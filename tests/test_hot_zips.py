import numpy as np
import pandas as pd

from ml.hot_zips import fit_classifier, fit_ranker, flag, reasons


def test_reasons_add_up_to_the_averaged_score():
    rng = np.random.default_rng(1)
    n = 400
    d = pd.DataFrame(
        {
            "zip": [f"{i:05d}" for i in range(n)],
            "cbsa_code": pd.Categorical(rng.choice(["a", "b"], n)),
            "month": pd.Timestamp("2024-01-01"),
            "x": rng.normal(size=n),
            "noise": rng.normal(size=n),
        }
    )
    d["target_top20"] = flag(d, "x")
    cols = ["cbsa_code", "x", "noise"]
    model = fit_classifier(d, cols)
    why = reasons(d, cols, model)
    assert len(why) == 3 * n and why.value[why.feature == "cbsa_code"].isna().all()
    # contributions plus the base value give the averaged log-odds of each ZIP
    base = model.predict(d[cols], pred_contrib=True)[:, -1]
    logodds = why.groupby("zip", sort=False).contribution.sum().to_numpy() + base
    assert np.allclose(1 / (1 + np.exp(-logodds)), model.predict(d[cols]))
    assert np.allclose(why.value[why.feature == "x"], d.x)


def test_ranker_learns_the_order_within_each_group():
    # rows arrive out of group order, as the feature table's zip-then-month order does
    rng = np.random.default_rng(0)
    n = 400
    d = pd.DataFrame(
        {
            "zip": [f"{i:05d}" for i in range(n)],
            "cbsa_code": rng.choice(["a", "b"], n),
            "month": pd.Timestamp("2024-01-01")
            + pd.to_timedelta(rng.integers(0, 2, n) * 31, "D"),
            "x": rng.normal(size=n),
        }
    )
    d["target_top20"] = flag(d, "x")
    d["score"] = fit_ranker(d, ["x"]).predict(d[["x"]])
    assert d.target_top20[flag(d, "score")].mean() > 0.95


def test_flag_takes_the_top_fifth_of_each_metro_month():
    d = pd.DataFrame(
        {
            "cbsa_code": ["a"] * 10 + ["b"] * 5,
            "month": pd.Timestamp("2024-01-01"),
            "score": list(range(10)) + [0.9, 0.1, 0.5, 0.3, 0.7],
        }
    )
    # metro a: the 2 highest of 10; metro b: the 1 highest of 5, whatever the other metro's scale
    assert d.score[flag(d, "score")].tolist() == [8, 9, 0.9]
