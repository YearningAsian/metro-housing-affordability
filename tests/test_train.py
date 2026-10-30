import pandas as pd

from ml.train import drift


def test_drift_waits_for_known_outcomes():
    assert (
        drift(
            pd.DataFrame(
                columns=["month", "growth_pred", "hot_flag", "actual_growth_12m"]
            )
        )
        is None
    )


def test_drift_checks_only_the_latest_matured_month():
    d = pd.DataFrame(
        {
            "month": pd.to_datetime(["2024-01-01"] * 2 + ["2024-02-01"] * 2),
            "growth_pred": [0.0, 0.0, 0.05, 0.05],
            "hot_flag": [True, False, True, False],
            # January missed by 50 pp; February by 3 and 5 pp, mean 4 pp
            "actual_growth_12m": [0.5, 0.5, 0.02, 0.10],
            "actual_top20": [True, False, False, True],
        }
    )
    month, mae, precision, alert = drift(d, limit=0.045)
    assert month == pd.Timestamp("2024-02-01")
    assert round(mae, 4) == 0.04 and precision == 0.0 and not alert
    assert drift(d, limit=0.035)[3]
