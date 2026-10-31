"""Cut the dashboard exports down to two metros for a quick demo: Seattle, which lost the
most affordability, and Austin, which lost the least. Reads data/export (run
.\\tasks.ps1 pipeline first) and writes sample/, which is small enough to keep in git.
Run: uv run python app/make_sample.py
Then: $env:DATA_URL = "sample"; uv run --group app streamlit run app/streamlit_app.py
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "data" / "export", ROOT / "sample"
METROS = {"42660", "12420"}  # Seattle, Austin

OUT.mkdir(exist_ok=True)
zips = set()
for name in [
    "dim_metro",
    "mart_metro_month",
    "mart_migration_origins",
    "mart_zip_forecast",
    "mart_zip_month",
]:
    d = pd.read_parquet(SRC / f"{name}.parquet")
    d = d[d.cbsa_code.isin(METROS)]
    if "zip" in d:
        zips |= set(d.zip)
    d.to_parquet(OUT / f"{name}.parquet", index=False, compression="zstd")

# centroids: the two metros and every county, since movers come from anywhere
c = pd.read_parquet(SRC / "centroids.parquet")
c[(c.kind == "county") | c.code.isin(METROS)].to_parquet(
    OUT / "centroids.parquet", index=False, compression="zstd"
)

g = json.loads((SRC / "zip_shapes.geojson").read_text())
g["features"] = [f for f in g["features"] if f["properties"]["zip"] in zips]
(OUT / "zip_shapes.geojson").write_text(json.dumps(g, separators=(",", ":")))

# some ZIPs have no shape (PO boxes), in the full exports too
assert zips and g["features"], "the sample came out empty"
print(f"wrote {OUT}: 2 metros, {len(zips)} ZIPs")
