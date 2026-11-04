"""Will a metro's home values be lower 12 months from now?

Classifies target_negative from ml.features_metro_month with logistic regressions, one row per metro and month. Each
quarter is an origin t: a model sees only rows whose outcome was published by t (known_by), then scores the 11 metros
at t. Origins start once training holds both classes. The baselines are today's growth alone, and persistence: what
is falling now stays falling. "Turns" keeps the rows still growing at t, where persistence says no by construction.

Ranking is scored within each origin, over origins with both outcomes. A pooled PR-AUC would reward a model whose
scores drift up with its growing share of negative training rows, because later origins are all negative.

Backtest only, not part of the monthly run. Prints the tables in docs/forecast_report.md.
Run: uv run --group ml --group dev python -m ml.turning_points
"""

import duckdb
import pandas as pd

from ml.forecast import ROOT, known_by
from ml.hot_zips import fit_logit

GROWTH = ["zhvi_growth_12m"]
RATES = [*GROWTH, "mortgage_rate_change_12m"]
REALTOR = [
    *RATES,
    "active_listing_count_yy",
    "price_reduced_share_yy",
    "median_days_on_market_yy",
]
MODELS = {
    "growth": GROWTH,
    "growth + rates": RATES,
    "growth + rates + Realtor": REALTOR,
}
LABEL = "target_negative"


def fit(train, cols):
    return fit_logit(train, cols, label=LABEL)


def backtest(metros):
    known = metros[metros[LABEL].notna()]
    scored = []
    for origin in pd.date_range(known.month.min(), known.month.max(), freq="QS"):
        train = known_by(metros, origin)
        if train[LABEL].nunique() < 2:
            continue
        d = known[known.month == origin].copy()
        d["persistence"] = (d.zhvi_growth_12m < 0).astype(float)
        for name, cols in MODELS.items():
            d[name] = fit(train, cols).predict_proba(d[cols])[:, 1]
        scored.append(d)
    return pd.concat(scored)


def metrics(d, col):
    from sklearn.metrics import brier_score_loss, roc_auc_score

    y = d[LABEL].astype(int)
    called = d[col] >= 0.5
    mixed = d.groupby("month").filter(lambda g: g[LABEL].nunique() == 2)
    return {
        "AUC within origin": mixed.groupby("month")
        .apply(
            lambda g: roc_auc_score(g[LABEL].astype(int), g[col]), include_groups=False
        )
        .mean(),
        "Brier": brier_score_loss(y, d[col]),
        "precision at 0.5": y[called].mean(),
        "recall at 0.5": y[called].sum() / y.sum(),
    }


def report(scored):
    rows = {}
    for subset, d in [
        ("all", scored),
        ("turns", scored[scored.zhvi_growth_12m >= 0]),
    ]:
        mixed = d.groupby("month")[LABEL].nunique().eq(2).sum()
        print(
            f"{subset}: {len(d)} metro-quarters, {int(d[LABEL].sum())} negative "
            f"({d[LABEL].astype(float).mean():.0%}), {mixed} origins with both outcomes"
        )
        for m in ["persistence", *MODELS]:
            rows[(subset, m)] = metrics(d, m)
    return pd.DataFrame(rows).T.round(3)


def main():
    con = duckdb.connect(str(ROOT / "data" / "warehouse.duckdb"), read_only=True)
    metros = con.sql("select * from ml.features_metro_month order by all").df()
    pd.set_option("display.width", 200)

    scored = backtest(metros)
    print(f"origins {scored.month.min():%b %Y} to {scored.month.max():%b %Y}\n")
    print(f"\n{report(scored).to_string()}\n")
    by_origin = scored.assign(growing=scored.zhvi_growth_12m >= 0).groupby("month")
    print(
        by_origin.agg(
            negative=(LABEL, "sum"),
            growing=("growing", "sum"),
            **{m.replace(" ", "_"): (m, "mean") for m in MODELS},
        )
        .round(2)
        .to_string()
    )


if __name__ == "__main__":
    main()
