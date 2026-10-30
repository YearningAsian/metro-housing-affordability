import pandas as pd

from ml.hot_zips import flag


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
