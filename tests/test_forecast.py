import numpy as np
import pandas as pd

from ml.forecast import conformal_margin, conformalize, known_by


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
