# Metro Housing Affordability Project Plan

Oct 26, 2026 · Colin Onevathana

This plan builds a multi-metro housing affordability pipeline, dashboard, three ML models and a presentation video in 18 phases over about 20 weeks at 8–10 hours a week. It compares Nashville, Atlanta, Orlando and Seattle against seven other fast-growing metros.

## Roadmap at a glance

| Part | Phase | Weeks | Gate |
| --- | --- | --- | --- |
| A: Foundations | 1 Setup and planning | 1 | |
| A: Foundations | 2 Source profiling | 2 | |
| A: Foundations | 3 Geography backbone | 3 | Gate A |
| B: Ingestion and storage | 4 Extractors and landing | 4–5 | |
| B: Ingestion and storage | 5 Warehouse layers | 6 | Gate B |
| C: Transform, quality, automation | 6 dbt models | 7–8 | |
| C: Transform, quality, automation | 7 Data quality | 8 | |
| C: Transform, quality, automation | 8 Orchestration | 9 | Gate C |
| D: Analysis and dashboard | 9 Exploratory analysis | 10–11 | |
| D: Analysis and dashboard | 10 Dashboard | 12 | Gate D (shippable) |
| E: Machine learning | 11 Feature engineering | 13 | |
| E: Machine learning | 12 Forecasting | 14–15 | |
| E: Machine learning | 13 Clustering | 15 | |
| E: Machine learning | 14 Hot-ZIP classifier | 16 | |
| E: Machine learning | 15 MLOps | 17 | Gate E |
| F: Story and ship | 16 Findings and deck | 18 | |
| F: Story and ship | 17 Presentation video | 19 | |
| F: Story and ship | 18 Portfolio launch | 20 | Gate F |

Gate D at week 12 already leaves a complete, shippable project: pipeline, tests, analysis and dashboard. Parts E and F add the models and the story; phases 6 and 7 share week 8, and 12 and 13 share week 15.

## Scope

The project answers one question: where in fast-growing US metros is housing still affordable, and which signals show up before prices jump? Everything is modeled at two grains, metro-month and ZIP-month, from January 2015 to the latest release.

**Supporting questions**

1. How has the home-price-to-income ratio changed in each metro since 2015?
2. Did metros that permitted more housing see slower price and rent growth?
3. Where are movers coming from, and are those origin counties pricier?
4. In which metros did rents outpace local wages the most?
5. Which ZIPs are most likely to be next year's fastest risers?

**Metros**

| Metro | CBSA code | Role |
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

Confirm each code against the Census CBSA delineation file in Phase 3; the list lives in one config file, so adding a metro is one line.

**Done means**

- The pipeline refreshes monthly with no manual steps.
- A public dashboard covers all 11 metros.
- The price forecast beats a naive baseline on a 2024–2025 backtest.
- A 6–8 minute video and a GitHub repo with a clear README are published.

Out of scope: scraping listing sites and property-level data. Use published aggregate files only.

## Data sources

Eleven free public datasets cover every metro the same way, so nothing needs scraping. Census, FRED and HUD need free API keys; request all three in Phase 1.

| Source | What you get | Geography | Cadence | Access | Used for |
| --- | --- | --- | --- | --- | --- |
| [Zillow Research](https://www.zillow.com/research/data/) | ZHVI home values, ZORI rents | Metro, county, ZIP | Monthly, around the 16th | CSV, no key | Prices, rents, ML targets |
| [Redfin Data Center](https://www.redfin.com/news/data-center/) | Inventory, days on market, price drops, sale-to-list | National to ZIP | Weekly and monthly | Compressed CSV/TSV | Market heat features |
| [Census Building Permits Survey](https://www.census.gov/construction/bps/index.html) | New units authorized, single vs. multifamily | CBSA, county, place | Monthly and annual | Excel and text files | Housing supply |
| [Census ACS 5-year](https://www.census.gov/data/developers/data-sets/acs-5year.html) | Income, population, rent burden, commutes | ZCTA, county, CBSA | Annual | API, free key | Income denominator, demographics |
| [BLS QCEW](https://www.bls.gov/cew/) | Jobs and average wages | County | Quarterly | CSV files | Wage growth |
| [FRED](https://research.stlouisfed.org/docs/api/api_key.html) | Mortgage rates, CPI, metro unemployment | National, metro | Weekly to monthly | API, free key | Macro context |
| [IRS SOI migration](https://www.irs.gov/statistics/soi-tax-stats-migration-data) | County-to-county inflows and outflows | County | Annual, latest 2022–2023 | CSV and Excel | Migration flows |
| [HUD Fair Market Rents](https://www.huduser.gov/portal/datasets/fmr.html) | Rent benchmarks by bedroom count | Metro, county, ZIP (small-area) | Annual, by fiscal year | Excel, API | Rent cross-check |
| [HUD-USPS ZIP crosswalk](https://www.huduser.gov/portal/datasets/usps_crosswalk.html) | ZIP to county, CBSA and tract allocation ratios | ZIP | Quarterly | Files or API | Joining ZIP and county data |
| [Census CBSA delineations](https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html) | County to metro mapping | County | When OMB revises (latest 2023) | Excel | Geography backbone |
| [Census cartographic boundaries](https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html) | ZCTA, county and CBSA shapes | All | Annual | Shapefiles | Maps |

## Architecture

```
11 public sources (Zillow, Redfin, Census, BLS, FRED, IRS, HUD)
        │
        ▼
┌─ GitHub Actions: one scheduled run each month ─────────────────────┐
│  Ingest: one Python extractor per source                           │
│    (retries, file-hash checks, load log; raw files land as Parquet)│
│        │                                                           │
│        ▼                                                           │
│  DuckDB warehouse, built and tested with dbt                       │
│    Bronze (raw, as text) → Silver (cleaned, typed, joined)         │
│      → Gold (monthly metro + ZIP marts)                            │
│        │                              │                            │
│        ▼                              ▼                            │
│  Checks and alerts               Machine learning                  │
│  (dbt tests, freshness,          (forecast, clusters, hot-ZIP      │
│   failure email)                  classifier; MLflow; scores       │
│                                   saved back to Gold)              │
└────────────────────────────────────────────────────────────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
 Public dashboard      Deck and video       Repo and docs
 (Tableau Public       (4–5 findings,       (README, dbt docs,
  or Streamlit)         6–8 minutes)         model card)
```

Everything in the GitHub Actions box runs on one schedule. The gold marts are the single source for the dashboard, the models and the video, so every number you show traces back to a tested table.

## Part A: Foundations (Phases 1–3, weeks 1–3)

Part A leaves you with a working repo, API keys, a profile of every source and the geography tables every later join depends on.

### Phase 1: Setup and planning (week 1)

- [x] Create a GitHub repo with folders `ingest/`, `dbt/`, `notebooks/`, `ml/`, `dashboard/` and `docs/`
- [x] Set up Python 3.12 with `uv` or `venv`; install `duckdb`, `polars` or `pandas`, `requests`, `dbt-duckdb`, `pytest` and `ruff`
- [x] Request Census, FRED and HUD API keys; keep them in `.env` (git-ignored) and as GitHub Actions secrets
- [x] Write `config/metros.yml` with the 11 CBSA codes
- [x] Write a README stub: the question, the metros, the sources
- [x] Add pre-commit hooks for `ruff` and `sqlfluff`

**Deliverable:** a repo where `make setup` runs end to end. **Done when:** a fresh clone installs in under 5 minutes.

### Phase 2: Source discovery and profiling (week 2)

Know every file's columns, grain, gaps and quirks before writing any pipeline.

- [x] Download one sample of each source by hand
- [x] Profile each in a notebook: row counts, date range, nulls, duplicate keys, which geography codes it uses
- [x] Record per source: primary key, date column, geography type (ZIP, ZCTA, county FIPS or CBSA), units, seasonal adjustment
- [x] Note each release lag; ACS income, for example, arrives about a year after the period it measures
- [x] Write `docs/data_dictionary.md`

**Deliverable:** data dictionary and profiling notebook. **Done when:** every column you plan to use has a type, unit and definition.

### Phase 3: Geography backbone (week 3)

Build one set of tables that maps ZIP to county to metro, so every source can join.

- [x] Load the CBSA delineation file into `dim_county` (county FIPS, name, CBSA code, metro name)
- [x] Load the HUD-USPS ZIP-to-county and ZIP-to-CBSA crosswalks, keeping the residential ratio
- [x] Pick a rule for ZIPs split across counties: largest residential share, or weighted allocation
- [x] Build `dim_zip` and `dim_metro`, filtered to the 11 metros
- [x] Map ZIPs to ZCTAs for ACS joins and map shapes; flag PO-box-only ZIPs, which never appear in HUD files
- [x] Verify the CBSA codes in `metros.yml`

**Deliverable:** `dim_metro`, `dim_county`, `dim_zip`. **Done when:** every Zillow ZIP in the 11 metros maps to exactly one metro.

**Gate A:** for every source, you can say how it reaches ZIP-month or metro-month grain.

## Part B: Ingestion and storage (Phases 4–5, weeks 4–6)

Part B makes every source land automatically and gives the warehouse a written design before any transforms start.

### Phase 4: Extractors and raw landing (weeks 4–5)

One Python extractor per source downloads the data, records what it fetched and lands the files unchanged.

- [x] Write a shared `BaseExtractor` with retries, backoff, timeouts and logging
- [x] Write one extractor per source: `zillow.py`, `redfin.py`, `bps.py`, `acs.py`, `qcew.py`, `fred.py`, `irs_migration.py`, `hud_fmr.py`, `hud_crosswalk.py`
- [x] Land files as-is under `data/raw/<source>/<load_date>/`
- [x] Log URL, file hash, row count and load time to a `_load_log` table
- [x] Skip a download when the hash matches the last load, so reruns are safe
- [x] Convert each file to Parquet in `data/bronze/`, all columns as text plus load metadata
- [x] Unit-test each extractor against a small fixture file
- [x] Keep data out of git; add a `.\tasks.ps1 ingest` command

**Deliverable:** `.\tasks.ps1 ingest` fills bronze for every source. **Done when:** a second run in the same month downloads nothing and finishes in under a minute.

### Phase 5: Warehouse layers (week 6)

Set up a DuckDB warehouse whose layers make it obvious what is raw, cleaned and analysis-ready.

- [x] Create `warehouse.duckdb` with schemas `bronze`, `silver`, `gold` and `ml`
- [x] Register bronze Parquet files as views
- [x] Fix naming: `stg_<source>__<entity>`, `int_<topic>`, `dim_` and `fct_`, `mart_`
- [x] Fix the two target grains: `metro_month` (cbsa_code, month) and `zip_month` (zip, month)
- [x] Set the month rule: first-of-month dates; quarterly and annual values carried forward and flagged `is_carried_forward`
- [x] Sketch a star schema: facts for prices, rents, market activity, permits, wages and migration; dimensions for geography and date
- [x] Draw the entity diagram in Mermaid or dbdiagram.io and save it to `docs/`

**Deliverable:** the warehouse file and its diagram. **Done when:** bronze tables query in DuckDB and the diagram covers every planned model.

**Gate B:** all sources land on one command, and the model design is written down.

## Part C: Transform, quality and automation (Phases 6–8, weeks 7–9)

Part C turns raw files into two tested, analysis-ready tables that refresh themselves every month. This is the core data engineering showcase.

### Phase 6: dbt models (weeks 7–8)

- [x] Start a dbt project on `dbt-duckdb`; declare bronze tables as sources with freshness rules
- [x] Write one staging model per source: snake_case names, proper types, ZIP and county FIPS as zero-padded text
- [x] Unpivot Zillow's one-column-per-month files into long rows (region, month, value)
- [x] Roll Redfin weekly data up to months; use only seasonally adjusted series or only unadjusted ones, never a mix (done differently: Redfin's monthly not-seasonally-adjusted files replace the weekly data, so no roll-up is needed)
- [x] Allocate county-level data (wages, permits, migration) to ZIPs with the crosswalk ratios where ZIP grain needs it (ZIPs get `res_ratio`-weighted county rates; counts are not split)
- [x] Build intermediate models: `int_prices`, `int_rents`, `int_supply`, `int_wages`, `int_migration`
- [x] Build the marts `mart_metro_month` and `mart_zip_month`, one row per place per month
- [x] Add derived metrics: price-to-income, rent-to-wage, year-over-year growth, permits per 1,000 residents, net migration rate
- [x] Describe every model and column in `schema.yml` (`_staging.yml`, `_intermediate.yml`, `_marts.yml`); generate `dbt docs`

**Deliverable:** the two marts. **Done when:** `dbt build` passes and each mart has exactly one row per key.

### Phase 7: Data quality (week 8)

- [x] Add generic tests: `unique` and `not_null` on mart keys, `relationships` from facts to dimensions, `accepted_values` on metro codes
- [x] Add range tests with `dbt-expectations`: prices above 0, yearly growth between −50% and +100%, ratios in plausible bounds
- [x] Check coverage: every new month has all 11 metros, and ZIP count drops no more than 5% month over month
- [x] Set source freshness: warn when Zillow data is 45 days old, fail at 75
- [x] Reconcile Zillow's published metro values against your own ZIP roll-up, within a documented tolerance
- [x] List every test and its reason in `docs/data_quality.md`

**Deliverable:** the test suite. **Done when:** a deliberately broken fixture fails at least one test.

### Phase 8: Orchestration and automation (week 9)

- [ ] Add one entry point, `make pipeline`: ingest, then `dbt build`, then export
- [ ] Schedule a GitHub Actions workflow monthly on the 20th, after Zillow's mid-month release, plus a manual trigger
- [ ] Persist the DuckDB file between runs as a release asset or in object storage such as S3 or Cloudflare R2
- [ ] Make the large ZIP-month models incremental
- [ ] Send failure alerts by email or a Slack or Discord webhook
- [ ] Publish `dbt docs` to GitHub Pages on every successful run
- [ ] Optional: re-run the pipeline as a Dagster or Prefect job to show orchestrator skills

**Deliverable:** the scheduled workflow. **Done when:** two scheduled runs in a row succeed with no manual fixes.

**Gate C:** clean, tested marts refresh on their own.

## Part D: Analysis and visualization (Phases 9–10, weeks 10–12)

Part D answers the five questions with numbers and puts them in a public dashboard. After Gate D you have a shippable portfolio project even if the ML phases slip.

### Phase 9: Exploratory analysis (weeks 10–11)

- [ ] Write one notebook per question, reading only from the marts
- [ ] Question 1: chart price-to-income by metro from 2015 to now and rank the biggest changes
- [ ] Question 2: plot permits per 1,000 residents against price growth by metro, with a fitted line
- [ ] Question 3: find each metro's top origin counties in the IRS data and compare their home values
- [ ] Question 4: chart rent growth minus wage growth by metro
- [ ] Question 5: compare what the fastest-rising ZIPs looked like a year before they took off; this feeds Phase 14
- [ ] Test robustness: other start years, and inflation-adjusted values using CPI from FRED
- [ ] Log each finding in `docs/findings.md`: one sentence, its number, its chart, its caveats

**Deliverable:** notebooks and the findings log. **Done when:** each question has a one-sentence answer with a number.

### Phase 10: Dashboard (week 12)

- [ ] Pick a tool: Tableau Public (most recognized by recruiters), Power BI (common in corporate roles) or Streamlit (shows Python, hosts free)
- [ ] Export the gold marts to Parquet or CSV on every pipeline run
- [ ] Page 1, overview: an affordability ranking over time, a metro picker and headline numbers
- [ ] Page 2, metro detail: a ZIP map of price growth, price vs. wage lines and the permits trend
- [ ] Page 3, migration: a flow map of the top origins into each metro
- [ ] Page 4, forecasts: left as a placeholder until Phase 15
- [ ] Keep colors consistent: one color per metro on every chart, one sequential palette for maps
- [ ] Show a data-as-of date and source notes on every page
- [ ] Check the layout on a phone

**Deliverable:** a public dashboard link. **Done when:** someone new can answer "which metro got least affordable?" in 30 seconds without help.

**Gate D:** findings are written down and the dashboard is live.

## Part E: Machine learning (Phases 11–15, weeks 13–17)

Part E adds three models that each have to beat a simple baseline on data they never saw, then automates them. Leakage is the main risk, so features come first.

### Phase 11: Feature engineering (week 13)

- [ ] Build `ml.features_zip_month` in dbt from the ZIP mart
- [ ] Add lags: price and rent growth at 1, 3, 6 and 12 months; inventory, days on market and share of price drops; permits over the trailing 12 months
- [ ] Add rolling stats: 12-month volatility and momentum (3-month vs. 12-month growth)
- [ ] Add context: metro-wide growth, the ZIP's price relative to its metro median, the mortgage rate
- [ ] Enforce point-in-time data: shift ACS and QCEW by their release lags so each row only sees what was published then
- [ ] Define targets: 12-month-ahead price growth (regression) and a top-20%-in-its-metro flag (classification)
- [ ] Split by time: train 2016–2022, validate 2023, test on predictions from 2024 onward whose outcome is already known
- [ ] Write a test that fails if any feature date is later than its prediction date

**Deliverable:** the feature table and splits. **Done when:** the leakage test passes.

### Phase 12: Price and rent forecasting (weeks 14–15)

- [ ] Set baselines: naive (last year's growth continues) and seasonal naive
- [ ] Fit a statistical model per metro, ETS or ARIMA, with `statsforecast`
- [ ] Fit one global LightGBM model across all ZIPs on the feature table
- [ ] Backtest with a rolling origin: refit each quarter, forecast 12 months ahead
- [ ] Report MAE of growth by metro, always next to the baseline's
- [ ] Add prediction intervals with quantile regression or conformal prediction
- [ ] Chart forecast vs. actual with intervals for 2–3 metros, and point out the misses

**Deliverable:** the forecast model and a backtest report. **Done when:** LightGBM beats the naive baseline on the test period, or the report explains why it does not.

### Phase 13: Neighborhood clustering (week 15)

- [ ] Summarize each ZIP's last 12 months: price growth, price-to-income, permits per capita, days on market, rent growth, net migration
- [ ] Standardize the features; run k-means for k = 3 to 8 and choose by silhouette score and how readable the groups are
- [ ] Cross-check with a Gaussian mixture or HDBSCAN
- [ ] Name each cluster by its profile, such as "hot and supply-constrained" or "affordable and growing"
- [ ] Chart a cluster map per metro, plus the share of ZIPs in each cluster by metro
- [ ] Track how ZIPs moved between clusters from 2019 to now

**Deliverable:** a cluster label table. **Done when:** every cluster has a name and a one-line profile.

### Phase 14: Hot-ZIP classifier with SHAP (week 16)

- [ ] Predict whether a ZIP lands in its metro's top 20% of price growth over the next 12 months
- [ ] Start with logistic regression, then LightGBM with class weights
- [ ] Evaluate on the time-based test set: precision among the top 20 flagged ZIPs, PR-AUC, a calibration curve
- [ ] Explain with SHAP: one global importance chart and 2–3 single-ZIP explanations
- [ ] Publish the ZIPs flagged for the next 12 months, with caveats
- [ ] Add a note that the model describes market signals, is not investment advice, and that fast price growth often means displacement

**Deliverable:** the classifier and SHAP charts. **Done when:** precision among flagged ZIPs clearly beats the 20% base rate.

### Phase 15: MLOps (week 17)

- [ ] Track runs, parameters, metrics and artifacts in MLflow
- [ ] Package training as `make train` with pinned versions and fixed random seeds
- [ ] Add monthly retrain and scoring to the GitHub Actions workflow, after `dbt build`
- [ ] Write predictions to `ml.predictions` with model version and run date, exposed through a dbt model
- [ ] Compare last month's predictions with new actuals and alert when error drifts above the backtest level
- [ ] Fill the dashboard's forecast page
- [ ] Write `docs/model_card.md`: data, metrics, known limits

**Deliverable:** automated retraining and scoring. **Done when:** a scheduled run produces new predictions that show up in the dashboard.

**Gate E:** every model beats its baseline, is explained, and runs on schedule.

## Part F: Story and ship (Phases 16–18, weeks 18–20)

Part F turns the work into a deck, a 6–8 minute video and a public launch. Recruiters often see only this part, so it gets three full weeks.

### Phase 16: Findings and slide deck (week 18)

- [ ] Choose the 4–5 strongest findings from `docs/findings.md`
- [ ] Give each one slide: one chart and a headline that states the finding with its number
- [ ] Order about 12 slides: hook, question, metros and data, architecture, findings, ML results, limits and next steps, links
- [ ] Re-export charts at 1920×1080 with large labels, so they read on a phone
- [ ] Write a one-page summary for the README

**Deliverable:** the deck. **Done when:** each headline makes sense with the chart hidden.

### Phase 17: Presentation video (week 19)

Run of show, about 7 minutes:

1. 0:00–0:30 — Hook: the biggest affordability swing among the 11 metros
2. 0:30–1:00 — The question and the metros
3. 1:00–2:00 — The pipeline, walked through on the architecture diagram
4. 2:00–4:30 — Findings: the affordability race, supply vs. prices, migration, rent vs. wages
5. 4:30–6:00 — ML: the forecast backtest, the cluster map, SHAP drivers, flagged ZIPs
6. 6:00–7:00 — Limits, next steps and where to find everything

- [ ] Write the script at about 140 words a minute, read it aloud, then cut 20%
- [ ] Record screen and voice with OBS Studio or Loom and a USB microphone
- [ ] Show the live dashboard for 30–60 seconds
- [ ] Animate the affordability ranking as a bar chart race (Flourish or a matplotlib animation)
- [ ] Edit in DaVinci Resolve or CapCut and add captions
- [ ] Upload to YouTube with chapters; cut a 60-second vertical version for LinkedIn

**Deliverable:** the full video and the short cut. **Done when:** someone new to the project can repeat the main finding after watching.

### Phase 18: Portfolio launch (week 20)

- [ ] Finish the README: problem, architecture image, how to run, findings, links to dashboard, video and model card
- [ ] Clean the repo: license, passing-tests badge, no secrets in git history, a small sample dataset for a quick demo
- [ ] Publish a write-up on Medium, Substack or a personal site
- [ ] Post on LinkedIn with the short cut and the strongest chart
- [ ] Add 2–3 resume bullets with real numbers: sources, metros, refresh cadence, how much the forecast beat its baseline
- [ ] Practice a 2-minute walkthrough for interviews

**Deliverable:** the public launch. **Done when:** the repo, dashboard, video and write-up are public and link to each other.

**Gate F:** shipped.

## Stretch phases (optional, after week 20)

Each stretch phase is a self-contained add-on of 1–2 weeks; pick by the job you want.

### Stretch 1: 311 deep dive for one city

- [ ] Pick the core metro whose city publishes 311 service requests on an open data portal; confirm before committing
- [ ] Ingest requests through the portal's API, incrementally by request date
- [ ] Geocode requests to ZIP and build `fct_311_zip_month` by complaint type
- [ ] Compare the complaint mix with price growth by ZIP; report associations, not causes
- [ ] Add a city spotlight page to the dashboard

### Stretch 2: Bike-share and transit layer

- [ ] Check which of the 11 metros publish bike-share trip data or transit ridership
- [ ] Map stations to ZIPs and count trips per ZIP-month
- [ ] Test whether trip growth adds anything to the hot-ZIP classifier

### Stretch 3: Cloud warehouse

- [ ] Port the warehouse to BigQuery or Snowflake by swapping the dbt adapter
- [ ] Define the cloud setup in Terraform
- [ ] Compare run time and monthly cost with DuckDB in a short write-up

### Stretch 4: Public API or app

- [ ] Serve metro metrics and predictions with FastAPI, containerized with Docker
- [ ] Deploy to a free tier such as Render or Fly.io
- [ ] Or build a Streamlit "metro matchmaker": enter income and budget, get the metros and ZIPs that fit

## Risks and pitfalls

Most failures in projects like this come from geography joins, silent source changes and scope creep, not from the models.

| Risk | Why it happens | How to handle it |
| --- | --- | --- |
| Download links break | Zillow notes it occasionally changes its CSV download paths | Keep URLs in config; a failed download alerts instead of loading stale data |
| Redfin history shifts | Redfin rebuilt its Data Center in May 2026 and made seasonally adjusted data the default | Re-pull full history each run; never mix old and new files |
| ZIP and ZCTA mismatch | ZIPs are mail routes; ZCTAs are Census areas that approximate them | Use the HUD crosswalk and one documented rule; report ZIP coverage |
| Metro boundaries change | OMB revised CBSA delineations in 2023 | Use one delineation vintage for every year |
| Data leakage | Annual data used before it was published | Point-in-time shifts plus the Phase 11 leakage test |
| Stale migration data | The latest IRS release covers 2022–2023 | Label years clearly; treat migration as structural context |
| Noisy small ZIPs | Few sales make values jumpy | Drop ZIPs with missing months or too few sales; say how many |
| Overclaiming causes | Permits, prices and migration move together for many reasons | Say "associated with" and state confounders on screen |
| Scope creep | 18 phases plus stretch work is a lot | Gate D is already shippable; ML and stretch phases are optional |

## Sources

- [Zillow Research housing data](https://www.zillow.com/research/data/)
- [Redfin Data Center](https://www.redfin.com/news/data-center/) and [its download hub](https://www.redfin.com/news/data-center/downloads/)
- [Census Building Permits Survey](https://www.census.gov/construction/bps/index.html)
- [Census ACS 5-year API](https://www.census.gov/data/developers/data-sets/acs-5year.html)
- [BLS Quarterly Census of Employment and Wages](https://www.bls.gov/cew/)
- [FRED API key](https://research.stlouisfed.org/docs/api/api_key.html)
- [IRS SOI migration data](https://www.irs.gov/statistics/soi-tax-stats-migration-data)
- [HUD Fair Market Rents](https://www.huduser.gov/portal/datasets/fmr.html)
- [HUD-USPS ZIP crosswalk files](https://www.huduser.gov/portal/datasets/usps_crosswalk.html)
- [Census CBSA delineation files](https://www.census.gov/geographies/reference-files/time-series/demo/metro-micro/delineation-files.html)
- [Census cartographic boundary files](https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html)
