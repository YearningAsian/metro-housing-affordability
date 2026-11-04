import numpy as np
import pandas as pd

from ml.hot_zips import fit_ranker, flag


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
