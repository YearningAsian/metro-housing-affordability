"""Phase 15: the monthly retrain and scoring, run by the pipeline after dbt build.

Refits the 12-month growth forecast (LightGBM point and quantile models, the band widened by a split-conformal margin
from the last 12 months with known outcomes) and the hot-ZIP classifier on every outcome known today. Scores the
latest month into ml.predictions, replacing an earlier run's scores for that month, and logs the run to MLflow in
data/mlflow. Then checks drift: the predictions whose 12-month outcome became known this month against the backtest
error. On drift it warns, and in GitHub Actions sets the step output drift=true, which fails the workflow's alert
job and emails.
Run: uv run --group ml python -m ml.train   (or .\tasks.ps1 train)
"""

import os
import subprocess
from datetime import date

import duckdb
import numpy as np
import pandas as pd

from ml.forecast import (
    COVERAGE,
    OUT,
    PARAMS,
    ROOT,
    ROUNDS,
    conformal_margin,
    features,
    fit_lgbm,
    known_by,
    load,
)
from ml.hot_zips import WEIGHT, fit_classifier, flag

LO, HI = (1 - COVERAGE) / 2, (1 + COVERAGE) / 2
# worst per-origin ZIP-level MAE of LightGBM on the 2024-2025 backtest test origins (docs/forecast_report.md)
MAE_LIMIT = 0.0532  # the October 2024 origin
MLFLOW = ROOT / "data" / "mlflow"


def fit_forecast(zips, cols):
    """Point and quantile models on every known outcome, plus the conformal margin from the last known year."""
    known = zips[zips.target_growth_12m.notna()]
    start = known.month.max() - pd.DateOffset(months=11)
    train, cal = known_by(zips, start), known[known.month >= start]
    lo = fit_lgbm(train, cols, objective="quantile", alpha=LO).predict(cal[cols])
    hi = fit_lgbm(train, cols, objective="quantile", alpha=HI).predict(cal[cols])
    margin = conformal_margin(
        np.maximum(lo - cal.target_growth_12m, cal.target_growth_12m - hi)
    )
    models = {
        "growth_12m": fit_lgbm(known, cols),
        "growth_12m_lo": fit_lgbm(known, cols, objective="quantile", alpha=LO),
        "growth_12m_hi": fit_lgbm(known, cols, objective="quantile", alpha=HI),
    }
    return models, margin, len(known), len(cal)


def score(zips, cols, models, margin, classifier):
    latest = zips[zips.month == zips.month.max()].copy()
    latest["growth_pred"] = models["growth_12m"].predict(latest[cols])
    latest["growth_lo"] = models["growth_12m_lo"].predict(latest[cols]) - margin
    latest["growth_hi"] = models["growth_12m_hi"].predict(latest[cols]) + margin
    latest["hot_score"] = classifier.predict(latest[cols])
    latest["hot_rank_pct"] = latest.groupby("cbsa_code", observed=True).hot_score.rank(
        pct=True
    )
    latest["hot_flag"] = flag(latest, "hot_score")
    latest["cbsa_code"] = latest.cbsa_code.astype(str)
    return latest[
        [
            "zip",
            "cbsa_code",
            "month",
            "prediction_date",
            "growth_pred",
            "growth_lo",
            "growth_hi",
        ]
        + ["hot_score", "hot_rank_pct", "hot_flag"]
    ]


def drift(matured, limit=MAE_LIMIT):
    """Error of the latest scored month whose outcomes are now known: (month, MAE, hot-flag precision, alert)."""
    if matured.empty:
        return None
    d = matured[matured.month == matured.month.max()]
    mae = (d.growth_pred - d.actual_growth_12m).abs().mean()
    precision = d.actual_top20[d.hot_flag].astype(float).mean()
    return d.month.iloc[0], mae, precision, bool(mae > limit)


def main():
    import mlflow

    zips, _, _ = load()
    cols = features(zips)
    version = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,  # outside a git checkout the version is "unknown"
    )
    version = version.stdout.strip() or "unknown"

    MLFLOW.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{(MLFLOW / 'mlflow.db').as_posix()}")
    # an experiment stores its artifact folder as an absolute path, so CI and local runs (which share the database
    # through push-state and pull-state) each log to an experiment created on their own machine
    experiment = "monthly" if os.environ.get("GITHUB_ACTIONS") else "local"
    if mlflow.get_experiment_by_name(experiment) is None:
        mlflow.create_experiment(
            experiment, artifact_location=(MLFLOW / "artifacts" / experiment).as_uri()
        )
    mlflow.set_experiment(experiment)
    with mlflow.start_run(run_name=f"{date.today():%Y-%m}") as run:
        models, margin, n_known, n_cal = fit_forecast(zips, cols)
        models["top20"] = fit_classifier(zips[zips.target_top20.notna()], cols)
        scored = score(zips, cols, models, margin, models["top20"])
        scored["run_date"] = date.today()
        scored["model_version"] = version
        scored["mlflow_run_id"] = run.info.run_id

        OUT.mkdir(parents=True, exist_ok=True)
        for name, model in models.items():
            model.save_model(OUT / f"lgbm_{name}.txt")
            mlflow.log_artifact(str(OUT / f"lgbm_{name}.txt"), "models")
        mlflow.log_params(
            {
                **PARAMS,
                "rounds": ROUNDS,
                "coverage": COVERAGE,
                "pos_weight": WEIGHT,
                "features": len(cols),
            }
            | {"model_version": version, "scored_month": f"{scored.month.max():%Y-%m}"}
        )
        mlflow.log_metrics(
            {
                "train_rows": n_known,
                "conformal_rows": n_cal,
                "conformal_margin_pp": margin * 100,
                "scored_zips": len(scored),
                "median_growth_pred_pct": scored.growth_pred.median() * 100,
            }
        )

        con = duckdb.connect(str(ROOT / "data" / "warehouse.duckdb"))
        con.execute("delete from ml.predictions where month = ?", [scored.month.max()])
        con.execute("insert into ml.predictions by name select * from scored")
        matured = con.sql(
            """
            select p.month, p.growth_pred, p.hot_flag, f.target_growth_12m actual_growth_12m,
                f.target_top20 actual_top20
            from ml.predictions p
            inner join ml.features_zip_month f using (zip, month)
            where f.target_growth_12m is not null
            """
        ).df()
        con.close()
        print(
            f"scored {len(scored):,} ZIPs for {scored.month.max():%b %Y} (model {version}, margin {margin:.4f})"
        )

        check = drift(matured)
        if check is None:
            print("drift: no scored month has known outcomes yet")
            return
        month, mae, precision, alert = check
        mlflow.log_metrics(
            {"matured_mae_pp": mae * 100, "matured_hot_precision": precision}
        )
        print(
            f"drift: {month:%b %Y} predictions, MAE {mae * 100:.2f} pp (limit {MAE_LIMIT * 100:.2f}), "
            f"hot-flag precision {precision:.2f}"
        )
        if alert:
            print(
                f"::warning::forecast MAE {mae * 100:.2f} pp for {month:%b %Y} is above the backtest's worst origin"
            )
            if os.environ.get("GITHUB_OUTPUT"):
                with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                    f.write("drift=true\n")


if __name__ == "__main__":
    main()
