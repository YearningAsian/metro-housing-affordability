"""The quick demo: every dashboard page runs on the two-metro sample in sample/, with no
local exports and no network."""

import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP))
import common


def test_share_above_splits_a_bracket_evenly():
    # half of the $50k-60k households are at $55k or more
    assert abs(common.share_above(55_000, [0] * 9 + [1] + [0] * 6) - 0.5) < 1e-9


@pytest.mark.parametrize(
    "page", ["overview", "metro", "migration", "forecasts", "findings", "matchmaker"]
)
def test_page_runs_on_sample(page, monkeypatch, tmp_path):
    monkeypatch.setattr(common, "LOCAL", tmp_path)  # no data/export
    monkeypatch.setattr(common, "REMOTE", str(APP.parent / "sample"))
    common.load.clear()
    at = AppTest.from_file(str(APP / "views" / f"{page}.py"), default_timeout=60).run()
    assert not at.exception, at.exception


def test_metro_page_shows_neighborhood_types(monkeypatch, tmp_path):
    monkeypatch.setattr(common, "LOCAL", tmp_path)
    monkeypatch.setattr(common, "REMOTE", str(APP.parent / "sample"))
    common.load.clear()
    at = AppTest.from_file(str(APP / "views" / "metro.py"), default_timeout=60)
    at.session_state["zip_view"] = "Neighborhood type"
    at.run()
    assert not at.exception, at.exception
    table = at.dataframe[0].value
    assert len(table) == 6 and table["ZIPs"].sum() > 0


def test_payment_matches_a_known_mortgage():
    # $300k loan at 6% over 30 years is $1,798.65 a month; 1% tax on $400k adds $333.33
    assert abs(common.payment(400_000, 100_000, 6.0, 0.01) - 2131.98) < 0.01
    # savings above the price leave only the tax
    assert abs(common.payment(100_000, 150_000, 6.0, 0.012) - 100) < 1e-9
