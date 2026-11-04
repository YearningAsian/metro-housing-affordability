import numpy as np
import pandas as pd

from ml.turning_points import LABEL, MODELS, backtest, metrics


def frame():
    # two metros; values turn down in 2022, so 2022's outcomes are not known until 2023
    rng = np.random.default_rng(0)
    months = pd.date_range("2020-01-01", "2024-12-01", freq="MS")
    d = pd.concat(
        pd.DataFrame({"cbsa_code": c, "month": months}) for c in ["a", "b"]
    ).reset_index(drop=True)
    for col in {c for cols in MODELS.values() for c in cols}:
        d[col] = rng.normal(size=len(d))
    d["target_growth_12m"] = np.where(d.month.dt.year == 2022, -0.05, 0.05)
    d[LABEL] = d.target_growth_12m < 0
    latest = d.month > "2023-12-01"  # outcome not known yet
    d.loc[latest, "target_growth_12m"] = np.nan
    d[LABEL] = d[LABEL].astype(object).where(~latest)
    return d


def test_origins_wait_for_both_classes():
    # the first negative row is January 2022, known from January 2023
    months = backtest(frame()).month.unique()
    assert months.min() == pd.Timestamp("2023-01-01")
    assert months.max() == pd.Timestamp("2023-10-01")


def test_scores_ignore_outcomes_not_yet_published():
    d = frame()
    # flipping outcomes the January 2023 fit must not see: February 2022 is known only from February 2023
    later = d.copy()
    unseen = (d.month > "2022-01-01") & d.target_growth_12m.notna()
    later.loc[unseen, "target_growth_12m"] *= -1
    later.loc[unseen, LABEL] = later.loc[unseen, "target_growth_12m"] < 0

    first = pd.Timestamp("2023-01-01")
    a = backtest(d)
    b = backtest(later)
    cols = list(MODELS)
    a, b = a[a.month == first], b[b.month == first]
    assert np.allclose(a[cols].to_numpy(), b[cols].to_numpy())


def test_metrics_for_a_rule_that_never_fires():
    d = pd.DataFrame(
        {"month": [1, 1], LABEL: [True, False], "rule": [0.0, 0.0]},
    )
    m = metrics(d, "rule")
    assert m["recall at 0.5"] == 0
    assert np.isnan(m["precision at 0.5"])
    assert m["Brier"] == 0.5


def test_ranking_is_scored_within_each_origin():
    # perfect inside origin 1, backwards inside origin 2, and origin 3 has one outcome, so it is skipped
    d = pd.DataFrame(
        {
            "month": [1, 1, 2, 2, 3, 3],
            LABEL: [True, False, True, False, True, True],
            "score": [0.2, 0.1, 0.8, 0.9, 0.5, 0.6],
        }
    )
    assert metrics(d, "score")["AUC within origin"] == 0.5
