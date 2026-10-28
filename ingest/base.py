"""Shared extractor machinery: HTTP with retries, the load log, raw landing and bronze Parquet.

Each source module defines a BaseExtractor subclass that lists its files and says how to read one.
run() does the rest: skip what is already loaded, download, hash, convert, log.
"""

import hashlib
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import duckdb
import pandas as pd
import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
log = logging.getLogger("ingest")

RETRY_STATUS = {429, 500, 502, 503, 504}
NOT_PUBLISHED_STATUS = {400, 404}  # HUD answers 400 "Invalid year"; the rest 404


class NotPublished(Exception):
    pass


@dataclass
class File:
    entity: str  # bronze table name
    url: str
    filename: str
    refresh: bool = False  # rolling URL (full history each time): re-fetch at most once per calendar month
    optional: bool = (
        False  # period that may not be released yet: 400/404 is expected, not an error
    )


def load_env(name):
    """os.environ first (CI secrets), then the repo's .env."""
    if name in os.environ:
        return os.environ[name]
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            k, _, v = line.partition("=")
            if k.strip() == name and not line.lstrip().startswith("#"):
                return v.strip().strip("'\"")
    raise KeyError(f"{name} not set in the environment or .env")


def metros():
    with open(ROOT / "config" / "metros.yml", encoding="utf-8") as f:
        return yaml.safe_load(f)["metros"]


def redact(text):
    """Strip API keys from URLs before they reach logs or the load log (the warehouse may be published)."""
    return re.sub(r"\b(api_key|key|token)=[^&\s'\"]+", r"\1=REDACTED", str(text))


def months(start, end):
    """(year, month) pairs from start to end inclusive."""
    y, m = start
    while (y, m) <= end:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def download(session, url, dest, headers=None, attempts=4, timeout=(10, 120)):
    """Stream url to dest via a .part file; return (sha256, bytes). Retries connection errors, 429 and 5xx."""
    for attempt in range(1, attempts + 1):
        try:
            with session.get(url, headers=headers, stream=True, timeout=timeout) as r:
                if r.status_code in NOT_PUBLISHED_STATUS:
                    raise NotPublished(f"HTTP {r.status_code}")
                if r.status_code in RETRY_STATUS:
                    raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
                r.raise_for_status()
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_name(dest.name + ".part")
                h, size = hashlib.sha256(), 0
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                        h.update(chunk)
                        size += len(chunk)
                tmp.replace(dest)
                return h.hexdigest(), size
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            retryable = (
                not isinstance(e, requests.HTTPError)
                or e.response.status_code in RETRY_STATUS
            )
            if not retryable or attempt == attempts:
                raise
            wait = 2**attempt
            log.warning(
                "retry %d/%d in %ds: %s", attempt, attempts - 1, wait, redact(e)
            )
            time.sleep(wait)


def lit(value):
    return "'" + str(value).replace("'", "''") + "'"


class BaseExtractor:
    source = ""
    headers = None
    throttle = 0.0  # seconds between requests, for rate-limited APIs

    def files(self):
        raise NotImplementedError

    def read(self, con, path, file):
        """Return the file as a DuckDB relation or DataFrame; every column text."""
        return con.sql(
            f"select * from read_csv({lit(path.as_posix())}, all_varchar = true)"
        )


LOG_DDL = """
create table if not exists _load_log (
    load_id varchar, source varchar, entity varchar, url varchar, raw_path varchar,
    file_hash varchar, bytes bigint, row_count bigint, status varchar, loaded_at timestamp
)"""


def should_skip(last, file, today):
    """last = (status, loaded_at) of the newest log row for this URL, or None."""
    if last is None:
        return False
    status, loaded_at = last
    same_month = (loaded_at.year, loaded_at.month) == (today.year, today.month)
    if status in ("loaded", "unchanged"):
        return same_month or not file.refresh
    return (
        status == "missing" and same_month
    )  # unreleased period: ask again next month; failures always retry


def run(extractors, data=DATA, today=None):
    """Run each extractor; return the number of failed files."""
    today = today or date.today()
    data.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(data / "warehouse.duckdb"))
    con.execute(LOG_DDL)
    session = requests.Session()
    # some government hosts reject the requests default User-Agent
    session.headers["User-Agent"] = "Mozilla/5.0"
    failed = 0
    for ex in extractors:
        try:
            files = ex.files()
        except Exception as e:  # noqa: BLE001 - one source's setup error must not stop the others
            log.error("%s: %s", ex.source, redact(e))
            failed += 1
            continue
        counts = {}
        for f in files:
            status = load_file(con, session, ex, f, data, today)
            counts[status] = counts.get(status, 0) + 1
            failed += status == "failed"
        log.info(
            "%s: %s",
            ex.source,
            ", ".join(f"{n} {s}" for s, n in sorted(counts.items())),
        )
    con.close()
    return failed


def load_file(con, session, ex, f, data, today):
    url = redact(f.url)
    last = con.execute(
        "select status, loaded_at from _load_log where url = ? order by loaded_at desc limit 1",
        [url],
    ).fetchall()
    if should_skip(last[0] if last else None, f, today):
        return "skipped"

    load_id, loaded_at = uuid.uuid4().hex, datetime.now(UTC).replace(tzinfo=None)
    raw = data / "raw" / ex.source / today.isoformat() / f.filename
    row = {
        "load_id": load_id,
        "source": ex.source,
        "entity": f.entity,
        "url": url,
        "raw_path": None,
        "file_hash": None,
        "bytes": None,
        "row_count": None,
        "loaded_at": loaded_at,
    }
    try:
        time.sleep(ex.throttle)
        file_hash, size = download(session, f.url, raw, ex.headers)
        row.update(file_hash=file_hash, bytes=size)
        prev = con.execute(
            "select file_hash from _load_log where url = ? and status = 'loaded' order by loaded_at desc limit 1",
            [url],
        ).fetchall()
        if prev and prev[0][0] == file_hash:
            raw.unlink()
            status = "unchanged"
        else:
            row.update(
                raw_path=raw.relative_to(data).as_posix(),
                row_count=to_bronze(con, ex, f, raw, row, data, today),
            )
            status = "loaded"
            log.info("loaded %s/%s: %s rows", ex.source, f.filename, row["row_count"])
    except NotPublished:
        if not f.optional:
            log.error("%s/%s: not found at %s", ex.source, f.filename, url)
            status = "failed"
        else:
            status = "missing"
    except Exception as e:  # noqa: BLE001 - log and keep going; the run exits non-zero at the end
        log.error("%s/%s: %s", ex.source, f.filename, redact(e))
        status = "failed"
    con.execute(
        "insert into _load_log values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            row["load_id"],
            row["source"],
            row["entity"],
            row["url"],
            row["raw_path"],
            row["file_hash"],
            row["bytes"],
            row["row_count"],
            status,
            row["loaded_at"],
        ],
    )
    return status


def to_bronze(con, ex, f, raw, row, data, today):
    """Write data/bronze/<source>/<entity>/<stem>__<load_date>.parquet: source columns as text plus load metadata."""
    rel = ex.read(con, raw, f)
    if isinstance(rel, pd.DataFrame):
        rel = con.from_df(rel.astype("string"))
    rel = rel.project(
        f"*, {lit(raw.name)} as _source_file, {lit(row['load_id'])} as _load_id, "
        f"{lit(row['loaded_at'])}::timestamp as _loaded_at, {lit(row['file_hash'])} as _file_hash"
    )
    out = (
        data
        / "bronze"
        / ex.source
        / f.entity
        / f"{Path(f.filename).stem}__{today.isoformat()}.parquet"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    rel.write_parquet(out.as_posix())
    return con.execute(
        "select count(*) from read_parquet(?)", [out.as_posix()]
    ).fetchall()[0][0]
