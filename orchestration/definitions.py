"""The monthly pipeline as Dagster assets: ingest -> dbt build -> export. GitHub Actions runs the same steps through
tasks.ps1; this is the same flow with lineage and a UI. Run from the repo root:

    uv run --group orchestrate dagster dev -f orchestration/definitions.py
"""

import json
import os
from pathlib import Path

from dagster import (
    AssetExecutionContext,
    AssetSpec,
    Definitions,
    Failure,
    ScheduleDefinition,
    asset,
    define_asset_job,
    in_process_executor,
    multi_asset,
)
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets, get_asset_key_for_model

from ingest import EXTRACTORS
from ingest.base import DATA, ROOT, run

# dagster-dbt runs dbt from dbt/, so hand it the repo-root paths the project would otherwise resolve itself
os.environ.setdefault("DUCKDB_PATH", str(DATA / "warehouse.duckdb"))
os.environ.setdefault("METROS_PATH", str(ROOT / "config" / "metros.yml"))

project = DbtProject(project_dir=ROOT / "dbt", profiles_dir=ROOT / "dbt")
project.prepare_if_dev()

# one asset per bronze table, keyed as dagster-dbt keys the sources, so the dbt models hang off ingest
sources = json.loads(Path(project.manifest_path).read_text(encoding="utf-8"))[
    "sources"
].values()


@multi_asset(
    specs=[AssetSpec([s["source_name"], s["name"]]) for s in sources],
    group_name="ingest",
)
def bronze():
    """python -m ingest: download new source files into data/raw and data/bronze."""
    failed = run([e() for e in EXTRACTORS.values()])
    if failed:
        raise Failure(f"ingest: {failed} file(s) failed")


@dbt_assets(manifest=project.manifest_path, project=project)
def dbt_models(context: AssetExecutionContext, dbt: DbtCliResource):
    # --full-refresh like tasks.ps1 pipeline: sources restate past months
    yield from dbt.cli(["build", "--full-refresh"], context=context).stream()


MARTS = ["mart_metro_month", "mart_zip_month"]


@asset(
    deps=[get_asset_key_for_model([dbt_models], m) for m in MARTS], group_name="export"
)
def mart_exports(dbt: DbtCliResource):
    """The gold marts as data/export/*.parquet, for the dashboard."""
    out = DATA / "export"
    out.mkdir(parents=True, exist_ok=True)
    dbt.cli(
        [
            "run-operation",
            "export_marts",
            "--args",
            json.dumps({"path": out.as_posix()}),
        ]
    ).wait()


pipeline = define_asset_job("pipeline")

defs = Definitions(
    assets=[bronze, dbt_models, mart_exports],
    jobs=[pipeline],
    schedules=[ScheduleDefinition(job=pipeline, cron_schedule="0 12 20 * *")],
    resources={"dbt": DbtCliResource(project_dir=project)},
    # DuckDB takes one writer: run steps one at a time
    executor=in_process_executor,
)
