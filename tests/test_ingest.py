import hashlib
import shutil
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import duckdb
import pytest
import requests

from ingest import EXTRACTORS, base

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 10, 27)

# source, fixture file (named as the real download), expected bronze rows
CASES = [
    ("zillow", "Metro_zori_uc_sfrcondomfr_sm_sa_month.csv", 2),
    ("redfin", "all_metros.csv", 2),
    ("bps", "co2608c.txt", 2),
    ("acs", "acs5_2024_county.json", 2),
    ("qcew", "2026_q1_industry_10.csv", 2),
    ("fred", "CPIAUCSL.json", 3),
    ("irs_migration", "countyinflow2223.csv", 2),
    ("hud_fmr", "METRO34980M34980_2027.json", 3),
    ("hud_fmr", "METRO12060N13035_2027.json", 1),
    ("hud_crosswalk", "zip_county.json", 3),
    ("census_geo", "list1_2023.xlsx", 2),
    ("census_geo", "cb_2024_us_county_500k.zip", 2),
]


@pytest.fixture(autouse=True)
def keys(monkeypatch):
    for k in ("CENSUS_API_KEY", "FRED_API_KEY", "HUD_API_TOKEN"):
        monkeypatch.setenv(k, "secret123")


@pytest.fixture
def served(monkeypatch):
    """Replace HTTP with copies of fixture files; record each URL requested."""
    state = SimpleNamespace(
        files={}, calls=[]
    )  # files: download filename -> fixture path or exception to raise

    def fake_download(session, url, dest, headers=None):
        state.calls.append(url)
        src = state.files[dest.name]
        if isinstance(src, Exception):
            raise src
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dest)
        return hashlib.sha256(dest.read_bytes()).hexdigest(), dest.stat().st_size

    monkeypatch.setattr(base, "download", fake_download)
    monkeypatch.setattr(base.time, "sleep", lambda s: None)
    return state


def one_file(source, filename):
    ex = EXTRACTORS[source]()
    f = next(f for f in ex.files() if f.filename == filename)
    ex.files = lambda: [f]
    return ex, f


def log_rows(data):
    with duckdb.connect(str(data / "warehouse.duckdb")) as con:
        return con.execute(
            "select status, url, row_count from _load_log order by loaded_at"
        ).fetchall()


@pytest.mark.parametrize(("source", "filename", "rows"), CASES)
def test_extractor_lands_bronze(tmp_path, served, source, filename, rows):
    ex, f = one_file(source, filename)
    served.files[filename] = FIXTURES / source / filename

    assert base.run([ex], data=tmp_path, today=TODAY) == 0

    assert (tmp_path / "raw" / source / TODAY.isoformat() / filename).exists()
    with duckdb.connect(str(tmp_path / "warehouse.duckdb")) as wh:
        view = f"bronze.{source}__{f.entity}"
        assert wh.execute(f"select count(*) from {view}").fetchall() == [(rows,)]
    out = (
        tmp_path
        / "bronze"
        / source
        / f.entity
        / f"{Path(filename).stem}__{TODAY.isoformat()}.parquet"
    )
    con = duckdb.connect()
    types = dict(
        con.execute(
            f"select column_name, column_type from (describe '{out.as_posix()}')"
        ).fetchall()
    )
    assert (
        con.execute(f"select count(*) from '{out.as_posix()}'").fetchall()[0][0] == rows
    )
    assert {"_source_file", "_load_id", "_loaded_at", "_file_hash"} <= types.keys()
    source_cols = {
        c: t for c, t in types.items() if not c.startswith("_") and c != "geom"
    }
    assert source_cols and set(source_cols.values()) == {"VARCHAR"}
    status, url, row_count = log_rows(tmp_path)[0]
    assert (status, row_count) == ("loaded", rows)
    assert "secret123" not in url


def test_second_run_same_month_downloads_nothing(tmp_path, served):
    period, pf = one_file("bps", "co2608c.txt")
    rolling, rf = one_file("redfin", "all_metros.csv")
    served.files = {
        pf.filename: FIXTURES / "bps" / pf.filename,
        rf.filename: FIXTURES / "redfin" / rf.filename,
    }

    base.run([period, rolling], data=tmp_path, today=TODAY)
    base.run([period, rolling], data=tmp_path, today=TODAY)
    assert len(served.calls) == 2

    # next month: the rolling file is fetched again but is identical, so nothing new lands in bronze
    base.run([period, rolling], data=tmp_path, today=date(2026, 11, 2))
    assert served.calls[2:] == [rf.url]
    assert [r[0] for r in log_rows(tmp_path)] == ["loaded", "loaded", "unchanged"]
    assert not (tmp_path / "raw" / "redfin" / "2026-11-02" / rf.filename).exists()
    assert len(list((tmp_path / "bronze" / "redfin").rglob("*.parquet"))) == 1


def test_unreleased_period_is_retried_next_month(tmp_path, served):
    ex, f = one_file("qcew", "2026_q1_industry_10.csv")
    served.files[f.filename] = base.NotPublished("HTTP 404")

    assert base.run([ex], data=tmp_path, today=TODAY) == 0
    assert base.run([ex], data=tmp_path, today=TODAY) == 0
    base.run([ex], data=tmp_path, today=date(2026, 11, 2))
    assert len(served.calls) == 2
    assert [r[0] for r in log_rows(tmp_path)] == ["missing", "missing"]


def test_failures_are_counted_and_redacted(tmp_path, served, caplog):
    ex, f = one_file("fred", "CPIAUCSL.json")
    served.files[f.filename] = requests.ConnectionError(f"cannot reach {f.url}")

    assert base.run([ex], data=tmp_path, today=TODAY) == 1
    assert "secret123" not in caplog.text and "api_key=REDACTED" in caplog.text
    assert log_rows(tmp_path)[0][0] == "failed"


class FakeResponse:
    def __init__(self, status, body=b""):
        self.status_code, self.body = status, body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def iter_content(self, size):
        yield self.body


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)

    def get(self, url, **kwargs):
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def test_download_retries_then_streams(tmp_path, monkeypatch):
    monkeypatch.setattr(base.time, "sleep", lambda s: None)
    session = FakeSession(
        requests.ConnectionError(), FakeResponse(503), FakeResponse(200, b"abc")
    )
    dest = tmp_path / "x" / "f.csv"

    assert base.download(session, "u", dest) == (hashlib.sha256(b"abc").hexdigest(), 3)
    assert dest.read_bytes() == b"abc" and not dest.with_name("f.csv.part").exists()


def test_download_gives_up_and_flags_unpublished(tmp_path, monkeypatch):
    monkeypatch.setattr(base.time, "sleep", lambda s: None)
    with pytest.raises(requests.HTTPError):
        base.download(FakeSession(*[FakeResponse(503)] * 4), "u", tmp_path / "f")
    with pytest.raises(base.NotPublished):
        base.download(FakeSession(FakeResponse(404)), "u", tmp_path / "f")
    with pytest.raises(
        requests.HTTPError
    ):  # a 403 is a real error, not a missing period
        base.download(FakeSession(FakeResponse(403)), "u", tmp_path / "f")


def test_redact():
    assert (
        base.redact("a?series_id=X&api_key=abc&key=def")
        == "a?series_id=X&api_key=REDACTED&key=REDACTED"
    )
