# Metro Housing Affordability

> Work in progress. See the [project plan](docs/PROJECT_PLAN.md).

## The question

Where in fast-growing US metros is housing still affordable, and which signals show up before prices jump?

Everything is modeled at two grains, metro-month and ZIP-month, from January 2015 to the latest release.

1. How has the home-price-to-income ratio changed in each metro since 2015?
2. Did metros that permitted more housing see slower price and rent growth?
3. Where are movers coming from, and are those origin counties pricier?
4. In which metros did rents outpace local wages the most?
5. Which ZIPs are most likely to be next year's fastest risers?

## Metros

| Metro | CBSA | Role |
| --- | --- | --- |
| Nashville, TN | 34980 | Core |
| Atlanta, GA | 12060 | Core |
| Orlando, FL | 36740 | Core |
| Seattle, WA | 42660 | Core, high-cost contrast |
| Austin, TX | 12420 | Comparison |
| Phoenix, AZ | 38060 | Comparison |
| Raleigh, NC | 39580 | Comparison |
| Charlotte, NC-SC | 16740 | Comparison |
| Tampa, FL | 45300 | Comparison |
| Dallas-Fort Worth, TX | 19100 | Comparison |
| Denver, CO | 19740 | Comparison |

The list lives in [`config/metros.yml`](config/metros.yml). Build the geography tables with `.\tasks.ps1 build`.

## Data sources

All free and public; no scraping.

| Source | Used for |
| --- | --- |
| [Zillow Research](https://www.zillow.com/research/data/) (ZHVI, ZORI) | Prices, rents |
| [Redfin Data Center](https://www.redfin.com/news/data-center/) | Sale prices, inventory, days on market |
| [Census Building Permits Survey](https://www.census.gov/construction/bps/index.html) | Housing supply |
| [Census ACS 5-year](https://www.census.gov/data/developers/data-sets/acs-5year.html) | Income, population, rent burden |
| [BLS QCEW](https://www.bls.gov/cew/) | Jobs and wages |
| [FRED](https://fred.stlouisfed.org/) | Mortgage rates, CPI, unemployment |
| [IRS SOI migration](https://www.irs.gov/statistics/soi-tax-stats-migration-data) | County-to-county migration |
| [HUD Fair Market Rents](https://www.huduser.gov/portal/datasets/fmr.html) | Rent cross-check |
| [HUD-USPS ZIP crosswalk](https://www.huduser.gov/portal/datasets/usps_crosswalk.html) | ZIP to county and CBSA |
| [Census CBSA delineations](https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html) | County to metro |
| [Census cartographic boundaries](https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html) | Map shapes |

Keys, units, release lags and quirks for each source are in the [data dictionary](docs/data_dictionary.md), backed by the [profiling notebook](notebooks/02_source_profiling.ipynb).

The warehouse layers, naming, grains and planned models are in the [warehouse design](docs/warehouse_design.md).

Every dbt test and its reason are in [data quality](docs/data_quality.md).

The answers so far, each with its number, chart and caveats, are in the [findings log](docs/findings.md). The analysis notebooks (`notebooks/09_*.ipynb`) read only the gold marts; rerun them with `uv run jupyter nbconvert --to notebook --execute --inplace notebooks/09_*.ipynb`.

The [forecast backtest](docs/forecast_report.md) compares a LightGBM model of 12-month ZIP home value growth with simple baselines, on point-in-time features (`ml.features_zip_month`). Rerun it with `uv run --group ml --group dev python -m ml.forecast`.

The [neighborhood clusters](docs/clusters_report.md) group the study ZIPs into six named types by their last 12 months of prices, rents, permits, sales speed and migration (`ml.zip_clusters`), and track how ZIPs moved since 2019. Rerun them with `uv run --group ml --group dev python -m ml.clusters`.

The [hot-ZIP classifier](docs/hot_zips_report.md) flags the ZIPs most likely to land in their metro's top 20% of home value growth over the next 12 months, explained with SHAP. It describes market signals, is not investment advice, and fast price growth often means displacement. Rerun it with `uv run --group ml --group dev python -m ml.hot_zips`.

Each monthly pipeline run refits both models on every known outcome, scores the latest month into `ml.predictions` (exposed as `gold.mart_zip_forecast`), logs the run to MLflow in `data/mlflow`, and fails an alert job when matured forecasts drift past the backtest's error. Run it alone with `.\tasks.ps1 train`. What the models are, how they scored and where they fail: the [model card](docs/model_card.md).

## Dashboard

A Streamlit app in [`app/`](app/) with four pages: an overview of which metro got least affordable, a metro detail page (ZIP map of home value growth, home values against wages, permits), migration origins, and forecasts (each ZIP's 12-month forecast and hot-ZIP flag from the monthly model). It reads the exports from `data/export` when they exist locally, otherwise from GitHub Pages (override with `DATA_URL`).

```powershell
uv run --group app streamlit run app/streamlit_app.py
```

Streamlit Community Cloud deploys it from this repo with `app/streamlit_app.py` as the entry point; it installs `app/requirements.txt`.

## Setup (Windows PowerShell)

Needs [uv](https://docs.astral.sh/uv/).

```powershell
.\tasks.ps1 setup   # Python 3.12 env, pre-commit hooks, .env from .env.example
```

Then put your Census, FRED and HUD keys in `.env`, and run:

```powershell
.\tasks.ps1 ingest   # download every source to data/raw and data/bronze (first run: about 3 GB, 15 minutes)
.\tasks.ps1 test     # unit tests
.\tasks.ps1 build    # dbt models and tests
```

`.\tasks.ps1 ingest fred zillow` loads only the named sources. A second run in the same month downloads nothing.

## Monthly pipeline

```powershell
.\tasks.ps1 pipeline   # ingest, then dbt build --full-refresh (models and tests), then export the marts to data/export/*.parquet
```

[`.github/workflows/pipeline.yml`](.github/workflows/pipeline.yml) runs it on the 20th of each month, after Zillow's mid-month release, and on demand (Actions > pipeline > Run workflow). Each run:

1. pulls the state from a private Cloudflare R2 bucket: `warehouse.duckdb` (with the load log) and every bronze load in `data/bronze`. Raw downloads are not kept; bronze holds their content.
2. runs `.\tasks.ps1 pipeline`.
3. pushes the state and the exports back to the bucket, only if the build passed.
4. checks source freshness: a source with no new load past its limit fails the run.
5. publishes the dbt docs to GitHub Pages, and the exports under `data/` for the dashboard.

A failed scheduled run emails whoever last edited the workflow's `cron` line (GitHub's own notification; check Settings > Notifications > Actions). GitHub turns off scheduled workflows in a public repo after 60 days without repository activity.

One-time setup:

1. In Cloudflare, create an R2 bucket and an R2 API token with Object Read & Write on it. Put its access key ID, secret, S3 endpoint (`https://<account-id>.r2.cloudflarestorage.com`) and the bucket name in `.env` (see `.env.example`).
2. Seed the bucket from a local run: `.\tasks.ps1 push-state`. `.\tasks.ps1 pull-state` fetches it back, overwriting the local warehouse.
3. Add the same four values as repository secrets (`gh secret set R2_BUCKET`, and so on), next to the Census, FRED and HUD keys.
4. Set Settings > Pages > Source to GitHub Actions.

The same flow runs as Dagster assets (ingest, every dbt model with its tests, the export) with a lineage graph and a schedule:

```powershell
uv run --group orchestrate dagster dev -f orchestration/definitions.py   # http://localhost:3000
```
