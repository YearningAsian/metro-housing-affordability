"""Phase 12: rolling-origin backtest of 12-month-ahead home value (ZHVI) growth.

Each quarter from 2022 is an origin t. Every model sees only what was published by t's prediction date:
LightGBM trains on the feature rows whose 12-month target was already known (month <= t - 12), and AutoETS on the
metro series up to t. All models then forecast growth from t to t + 12 for every ZIP with a known outcome.

Writes data/ml/backtest_zip.parquet, data/ml/backtest_metro.parquet, the final model data/ml/lgbm_growth_12m.txt
and docs/figures/forecast_vs_actual.png, and prints the MAE tables for docs/forecast_report.md.
Run: uv run --group ml --group dev python -m ml.forecast [--report]   (--report: skip the backtest, reuse its output)
"""

import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "ml"
SEED = 42
FIRST_ORIGIN = "2022-01-01"
COVERAGE = 0.8  # nominal coverage of the prediction intervals
NOT_FEATURES = {
    "zip",
    "month",
    "prediction_date",
    "split",
    "target_growth_12m",
    "target_top20",
    "redfin_month",
    "permits_month",
    "wages_quarter_start",
    "income_acs_vintage",
}
ROUNDS = 600
PARAMS = {
    "learning_rate": 0.03,
    "num_leaves": 31,
    "min_data_in_leaf": 50,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "feature_fraction": 0.8,
    "seed": SEED,
    "deterministic": True,
    "verbose": -1,
}


def load():
    con = duckdb.connect(str(ROOT / "data" / "warehouse.duckdb"), read_only=True)
    zips = con.sql("select * from ml.features_zip_month").df()
    metro = con.sql(
        "select cbsa_code, month, zhvi_usd, zori_usd from gold.mart_metro_month order by all"
    ).df()
    names = con.sql(
        "select cbsa_code, split_part(metro_name, ',', 1) metro from gold.dim_metro"
    ).df()
    zips["cbsa_code"] = zips.cbsa_code.astype("category")
    return zips, metro, names.set_index("cbsa_code").metro


def features(zips):
    return [
        c
        for c in zips.columns
        if c not in NOT_FEATURES and not c.endswith("_available_on")
    ]


def known_by(zips, origin):
    """Rows whose target (ZHVI 12 months later) was published by origin's prediction date."""
    return zips[
        (zips.month <= origin - pd.DateOffset(months=12))
        & zips.target_growth_12m.notna()
    ]


def conformal_margin(scores):
    """Split-conformal quantile of conformity scores for COVERAGE (CQR, Romano et al. 2019)."""
    n = len(scores)
    return np.quantile(scores, min(1.0, np.ceil((n + 1) * COVERAGE) / n)) if n else 0.0


def fit_lgbm(train, cols, objective="regression", **params):
    import lightgbm as lgb

    data = lgb.Dataset(train[cols], train.target_growth_12m)
    return lgb.train(
        {**PARAMS, "objective": objective, **params}, data, num_boost_round=ROUNDS
    )


def ets_growth(metro, origin):
    """AutoETS per metro on the monthly ZHVI and ZORI series to origin: growth to origin + 12 with an 80% interval."""
    from statsforecast import StatsForecast
    from statsforecast.models import AutoETS

    out = []
    for series in ["zhvi_usd", "zori_usd"]:
        df = metro.loc[metro.month <= origin, ["cbsa_code", "month", series]].dropna()
        df.columns = ["unique_id", "ds", "y"]
        fc = StatsForecast(models=[AutoETS(season_length=12)], freq="MS").forecast(
            df=df, h=12, level=[int(COVERAGE * 100)]
        )
        fc = fc[fc.ds == origin + pd.DateOffset(months=12)].set_index("unique_id")
        last = df[df.ds == origin].set_index("unique_id").y
        band = f"{int(COVERAGE * 100)}"
        out.append(
            pd.DataFrame(
                {
                    "series": series,
                    "ets": fc.AutoETS / last - 1,
                    "ets_lo": fc[f"AutoETS-lo-{band}"] / last - 1,
                    "ets_hi": fc[f"AutoETS-hi-{band}"] / last - 1,
                }
            )
        )
    return pd.concat(out).rename_axis("cbsa_code").reset_index()


def backtest(zips, metro):
    cols = features(zips)
    last = zips.loc[zips.target_growth_12m.notna(), "month"].max()
    zip_rows, metro_rows = [], []
    for origin in pd.date_range(FIRST_ORIGIN, last, freq="QS"):
        train = known_by(zips, origin)
        test = zips[(zips.month == origin) & zips.target_growth_12m.notna()].copy()
        test["lgbm"] = fit_lgbm(train, cols).predict(test[cols])
        for name, alpha in [("lo", (1 - COVERAGE) / 2), ("hi", (1 + COVERAGE) / 2)]:
            test[name] = fit_lgbm(
                train, cols, objective="quantile", alpha=alpha
            ).predict(test[cols])
        ets = ets_growth(metro, origin)
        test["ets"] = test.cbsa_code.astype(str).map(
            ets[ets.series == "zhvi_usd"].set_index("cbsa_code").ets
        )
        zip_rows.append(test)
        print(
            f"{origin:%Y-%m}: trained on {len(train):,} rows, scored {len(test):,} ZIPs"
        )

        actual = metro.set_index(["cbsa_code", "month"])
        for series in ["zhvi_usd", "zori_usd"]:
            now = actual.xs(origin, level="month")[series]
            ago = actual.xs(origin - pd.DateOffset(months=12), level="month")[series]
            ahead = actual[series].unstack().get(origin + pd.DateOffset(months=12))
            if ahead is None:
                continue
            m = ets[ets.series == series].set_index("cbsa_code")
            m["y"] = ahead / now - 1
            m["naive"] = now / ago - 1
            m["month"] = origin
            metro_rows.append(m.reset_index())

    out = pd.concat(zip_rows, ignore_index=True)
    out = out[
        ["zip", "cbsa_code", "month", "split", "target_growth_12m", "zhvi_growth_12m"]
        + ["lgbm", "lo", "hi", "ets"]
    ].rename(columns={"target_growth_12m": "y", "zhvi_growth_12m": "naive"})
    out["no_change"] = 0.0
    return conformalize(out), pd.concat(metro_rows, ignore_index=True)


def conformalize(out):
    """Widen each origin's quantile band by the CQR margin from earlier origins whose outcomes were known by then."""
    score = np.maximum(out.lo - out.y, out.y - out.hi)
    out["margin"] = np.nan
    for origin in pd.to_datetime(out.month.unique()):
        prior = out.month <= origin - pd.DateOffset(months=12)
        out.loc[out.month == origin, "margin"] = (
            conformal_margin(score[prior]) if prior.any() else np.nan
        )
    out["lo_cqr"] = out.lo - out.margin
    out["hi_cqr"] = out.hi + out.margin
    return out


def mae_table(out, names, models, split):
    d = out[out.split == split]
    err = d[models].sub(d.y, axis=0).abs()
    t = err.groupby(d.cbsa_code, observed=True).mean()
    t.loc["All"] = err.mean()
    t.index = [names.get(i, i) for i in t.index]
    return (t * 100).round(2)


def chart(out, names, metros):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(
        1, len(metros), figsize=(4 * len(metros), 3.2), sharey=True
    )
    for ax, code in zip(axes, metros, strict=True):
        d = out[(out.cbsa_code == code) & out.lo_cqr.notna()].groupby("month")
        med = d[["y", "lgbm", "naive", "lo_cqr", "hi_cqr"]].median() * 100
        ax.fill_between(
            med.index,
            med.lo_cqr,
            med.hi_cqr,
            color="#2a78d6",
            alpha=0.15,
            label="median ZIP 80% interval",
        )
        ax.plot(med.index, med.y, color="#0b0b0b", label="actual")
        ax.plot(med.index, med.lgbm, color="#2a78d6", label="LightGBM")
        ax.plot(med.index, med.naive, color="#c3c2b7", linestyle="--", label="naive")
        ax.axhline(0, color="#52514e", linewidth=0.6)
        ax.set_title(names[code])
        ax.tick_params(axis="x", rotation=45)
    axes[0].set_ylabel("12-month growth, median ZIP (%)")
    axes[0].legend(frameon=False, fontsize=7)
    fig.suptitle(
        "12-month ZHVI growth forecast at each quarterly origin vs. what followed",
        x=0.01,
        ha="left",
        fontsize=10,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(ROOT / "docs" / "figures" / "forecast_vs_actual.png", dpi=150)


def main():
    zips, metro, names = load()
    if "--report" in sys.argv:  # tables and chart from the saved backtest
        out = pd.read_parquet(OUT / "backtest_zip.parquet")
        metro_out = pd.read_parquet(OUT / "backtest_metro.parquet")
    else:
        out, metro_out = backtest(zips, metro)
        OUT.mkdir(parents=True, exist_ok=True)
        out.to_parquet(OUT / "backtest_zip.parquet")
        metro_out.to_parquet(OUT / "backtest_metro.parquet")
        # the model a run on today's data would use
        fit_lgbm(zips[zips.target_growth_12m.notna()], features(zips)).save_model(
            OUT / "lgbm_growth_12m.txt"
        )

    pd.set_option("display.width", 200)
    models = ["lgbm", "naive", "no_change", "ets"]
    for split in ["validate", "test"]:
        print(f"\nZIP-level MAE of 12-month growth (percentage points), {split}:")
        print(mae_table(out, names, models, split).to_string())
    test = out[out.split == "test"]
    for cols in [("lo", "hi"), ("lo_cqr", "hi_cqr")]:
        inside = test.y.between(test[cols[0]], test[cols[1]])
        print(
            f"\ncoverage {cols}: {inside.mean():.3f}, mean width {(test[cols[1]] - test[cols[0]]).mean() * 100:.2f} pp"
        )
    mt = metro_out[metro_out.month >= "2024-01-01"].copy()
    for m in ["ets", "naive"]:
        mt[m] = (mt[m] - mt.y).abs() * 100
    mt["metro"] = mt.cbsa_code.map(names)
    print("\nMetro-level MAE (pp), origins from 2024:")
    print(
        mt.pivot_table(index="metro", columns="series", values=["ets", "naive"])
        .round(2)
        .to_string()
    )
    inside = mt.y.between(mt.ets_lo, mt.ets_hi)
    print(
        f"ETS 80% interval coverage: {inside.mean():.3f} over {len(mt)} metro-origins"
    )
    chart(out, names, ["12420", "45300", "42660"])


if __name__ == "__main__":
    main()
