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


@pytest.mark.parametrize("page", ["overview", "metro", "migration", "forecasts"])
def test_page_runs_on_sample(page, monkeypatch, tmp_path):
    monkeypatch.setattr(common, "LOCAL", tmp_path)  # no data/export
    monkeypatch.setattr(common, "REMOTE", str(APP.parent / "sample"))
    common.load.clear()
    at = AppTest.from_file(str(APP / "views" / f"{page}.py"), default_timeout=60).run()
    assert not at.exception, at.exception
