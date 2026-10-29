import os
import subprocess
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).parent.parent
METROS = ["12060", "34980"]
MONTHS = ["2026-07-01", "2026-08-01"]


def run_coverage_test(tmp_path, drop_zhvi_for=None):
    # Named warehouse.duckdb so dbt's database name matches what the models compile to.
    db = tmp_path / "warehouse.duckdb"
    con = duckdb.connect(str(db))
    con.execute("create schema gold")
    con.execute("create table gold.dim_metro (cbsa_code varchar)")
    con.execute(
        "create table gold.mart_metro_month (cbsa_code varchar, month date, zhvi_usd double, zori_usd double)"
    )
    con.executemany("insert into gold.dim_metro values (?)", [[m] for m in METROS])
    for m in METROS:
        for month in MONTHS:
            zhvi = None if (m, month) == drop_zhvi_for else 350000.0
            con.execute(
                "insert into gold.mart_metro_month values (?, ?, ?, 1800.0)",
                [m, month, zhvi],
            )
    con.close()

    if not (ROOT / "dbt" / "dbt_packages").exists():
        subprocess.run(
            ["dbt", "deps", "--project-dir", "dbt", "--profiles-dir", "dbt"],
            cwd=ROOT,
            check=True,
        )
    return subprocess.run(
        [
            "dbt",
            "test",
            "--project-dir",
            "dbt",
            "--profiles-dir",
            "dbt",
            "--select",
            "assert_metro_month_coverage",
        ],
        cwd=ROOT,
        env={**os.environ, "DUCKDB_PATH": str(db)},
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("broken", [False, True])
def test_coverage_test_catches_missing_metro_month(tmp_path, broken):
    result = run_coverage_test(
        tmp_path, drop_zhvi_for=("34980", "2026-08-01") if broken else None
    )
    assert (result.returncode != 0) == broken, result.stdout
    if broken:
        assert "FAIL 1 assert_metro_month_coverage" in result.stdout
