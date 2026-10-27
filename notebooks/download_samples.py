"""Phase 2: pull one sample of each source into data/samples/<source>/.

Run from the repo root:  uv run python notebooks/download_samples.py
Skips files that already exist. API keys come from .env. Phase 4 extractors replace this.
"""

import json
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "samples"

ZILLOW = "https://files.zillowstatic.com/research/public_csvs"
REDFIN = "https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker"
BPS = "https://www2.census.gov/econ/bps"
TIGER = "https://www2.census.gov/geo/tiger"
HUD = "https://www.huduser.gov/hudapi/public"

# ACS: median household income, population, median gross rent, median rent as % of income
ACS_VARS = "NAME,B19013_001E,B01003_001E,B25064_001E,B25071_001E"
ACS_GEOS = {
    "zcta": "zip code tabulation area:*",
    "county": "county:*",
    "cbsa": "metropolitan statistical area/micropolitan statistical area:*",
}
# 30-year mortgage rate (weekly), CPI-U (monthly, SA), Nashville MSA unemployment (LAUS, NSA)
FRED_SERIES = ["MORTGAGE30US", "CPIAUCSL", "LAUMT473498000000003"]


def load_env():
    env = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip("'\"")
    return env


def fetch(url, dest, headers=None):
    dest = OUT / dest
    if dest.exists():
        print(f"skip  {dest.relative_to(ROOT)}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", **(headers or {})}
    )
    tmp = dest.with_suffix(dest.suffix + ".part")
    # stream to a temp file so an interrupted download never leaves a truncated sample behind
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    tmp.replace(dest)
    print(f"saved {dest.relative_to(ROOT)} ({dest.stat().st_size / 1e6:.1f} MB)")


def main():
    env = load_env()
    files = {
        "zillow/zip_zhvi.csv": f"{ZILLOW}/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
        "zillow/metro_zhvi.csv": f"{ZILLOW}/zhvi/Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
        "zillow/zip_zori.csv": f"{ZILLOW}/zori/Zip_zori_uc_sfrcondomfr_sm_month.csv",
        "zillow/metro_zori.csv": f"{ZILLOW}/zori/Metro_zori_uc_sfrcondomfr_sm_month.csv",
        "redfin/metro_market_tracker.tsv.gz": f"{REDFIN}/redfin_metro_market_tracker.tsv000.gz",
        "redfin/zip_market_tracker.tsv.gz": f"{REDFIN}/zip_code_market_tracker.tsv000.gz",
        "bps/cbsa2608c.txt": f"{BPS}/CBSA%20(beginning%20Jan%202024)/cbsa2608c.txt",
        "bps/co2608c.txt": f"{BPS}/County/co2608c.txt",
        "qcew/2026_q1_industry_10.csv": "https://data.bls.gov/cew/data/api/2026/1/industry/10.csv",
        "irs/countyinflow2223.csv": "https://www.irs.gov/pub/irs-soi/countyinflow2223.csv",
        "irs/countyoutflow2223.csv": "https://www.irs.gov/pub/irs-soi/countyoutflow2223.csv",
        "cbsa_delineation/list1_2023.xlsx": "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx",
        "boundaries/cb_2024_us_cbsa_500k.zip": f"{TIGER}/GENZ2024/shp/cb_2024_us_cbsa_500k.zip",
        "boundaries/cb_2024_us_county_500k.zip": f"{TIGER}/GENZ2024/shp/cb_2024_us_county_500k.zip",
        "boundaries/cb_2020_us_zcta520_500k.zip": f"{TIGER}/GENZ2020/shp/cb_2020_us_zcta520_500k.zip",
    }
    for geo, clause in ACS_GEOS.items():
        q = urllib.parse.urlencode(
            {"get": ACS_VARS, "for": clause, "key": env["CENSUS_API_KEY"]}
        )
        files[f"acs/acs5_2024_{geo}.json"] = (
            f"https://api.census.gov/data/2024/acs/acs5?{q}"
        )
    for s in FRED_SERIES:
        q = urllib.parse.urlencode(
            {"series_id": s, "file_type": "json", "api_key": env["FRED_API_KEY"]}
        )
        files[f"fred/{s}.json"] = (
            f"https://api.stlouisfed.org/fred/series/observations?{q}"
        )

    failed = []
    for dest, url in files.items():
        try:
            fetch(url, dest)
        # keep going; report at the end without echoing URLs that hold keys
        except Exception as e:  # noqa: BLE001
            failed.append(dest)
            print(f"FAIL  {dest}: {type(e).__name__} {getattr(e, 'code', '')}")

    hud = {"Authorization": f"Bearer {env['HUD_API_TOKEN']}"}
    for dest, url in {
        "hud_fmr/fmr_2027_nashville.json": f"{HUD}/fmr/data/METRO34980M34980?year=2027",
        "hud_fmr/fmr_2027_state_tn.json": f"{HUD}/fmr/statedata/TN?year=2027",
        "hud_crosswalk/zip_county.json": f"{HUD}/usps?type=2&query=All",
        "hud_crosswalk/zip_cbsa.json": f"{HUD}/usps?type=3&query=All",
    }.items():
        try:
            fetch(url, dest, hud)
            # HUD returns HTML error pages with 200 sometimes
            json.loads((OUT / dest).read_text())
        except Exception as e:  # noqa: BLE001
            failed.append(dest)
            print(f"FAIL  {dest}: {type(e).__name__} {getattr(e, 'code', '')}")

    if failed:
        sys.exit(f"{len(failed)} downloads failed: {failed}")


if __name__ == "__main__":
    main()
