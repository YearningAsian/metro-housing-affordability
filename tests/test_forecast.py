import numpy as np
import pandas as pd

from ml.forecast import (
    conformal_margin,
    conformalize,
    error_parts,
    known_by,
    reconcile,
)


def test_known_by_keeps_only_published_targets():
    months = pd.date_range("2022-01-01", "2024-01-01", freq="MS")
    zips = pd.DataFrame({"month": months, "target_growth_12m": 0.05})
    zips.loc[0, "target_growth_12m"] = np.nan
    train = known_by(zips, pd.Timestamp("2024-01-01"))
    # the target of month m is ZHVI at m + 12, published by the origin only when m + 12 <= origin
    assert train.month.min() == pd.Timestamp("2022-02-01")
    assert train.month.max() == pd.Timestamp("2023-01-01")


def test_conformal_margin_covers_the_nominal_share():
    scores = np.arange(1, 11, dtype=float)  # ceil(11 * 0.8) / 10 = 0.9 quantile
    assert conformal_margin(scores) == np.quantile(scores, 0.9)
    assert conformal_margin(np.array([])) == 0.0


def test_conformalize_uses_only_earlier_known_outcomes():
    origins = pd.to_datetime(["2022-01-01", "2023-01-01", "2023-04-01"])
    out = pd.DataFrame({"month": origins, "y": [0.5, 9.0, 9.0], "lo": 0.0, "hi": 0.1})
    out = conformalize(out)
    # 2022-01 has no earlier outcome; both 2023 origins see only 2022-01 (score 0.4), never each other
    assert np.isnan(out.margin[0])
    assert np.allclose(out.margin[1:], 0.4)


def test_reconcile_moves_the_metro_level_and_keeps_the_zip_spread():
    out = pd.DataFrame(
        {
            "cbsa_code": ["a", "a", "b"],
            "month": pd.Timestamp("2024-01-01"),
            "lgbm": [0.10, 0.04, 0.02],
            "ets": [-0.01, -0.01, 0.03],
        }
    )
    weights = np.array([1.0, 3.0, 5.0])
    rec = reconcile(out, weights)
    # metro a: weighted mean (0.10 + 3 * 0.04) / 4 = 0.055, so every ZIP shifts by -0.065
    assert np.allclose(rec, [0.035, -0.025, 0.03])
    assert np.isclose(np.average(rec[:2], weights=weights[:2]), -0.01)


def test_error_parts_split_a_level_miss_from_a_spread_miss():
    d = pd.DataFrame(
        {
            "cbsa_code": "a",
            "month": pd.Timestamp("2024-01-01"),
            "y": [0.0, 0.2],
            "level": [0.1, 0.3],  # right spread, 0.1 too high
            "spread": [0.05, 0.15],  # right level, spread 0.05 too narrow on each side
        }
    )
    parts = error_parts(d, ["level", "spread"])
    assert parts.loc["level"].tolist() == [10.0, 0.0]
    assert parts.loc["spread"].tolist() == [0.0, 5.0]
