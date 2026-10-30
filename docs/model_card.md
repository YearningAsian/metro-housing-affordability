# Model card: monthly ZIP forecast and hot-ZIP flags

The monthly pipeline refits two LightGBM models and publishes their scores for every study ZIP. This card covers what
they are, what they were tested on, how they run, and where they fail. The backtests behind the numbers are in the
[forecast report](forecast_report.md) and the [hot-ZIP report](hot_zips_report.md).

> Not investment advice. The models describe signals in public aggregate data. A ZIP flagged "hot" is where prices
> are likely to rise fastest in its metro, which for renters and owners on fixed incomes often means rising rents,
> rising property taxes and displacement.

## What is published

`ml.predictions` holds one row per ZIP and scored month, exposed through the dbt view `gold.mart_zip_forecast` and
the dashboard's Forecasts page:

| Column | Meaning |
| --- | --- |
| `growth_pred` | Forecast ZHVI growth from the scored month to 12 months later (LightGBM regression) |
| `growth_lo`, `growth_hi` | An 80% band: LightGBM 10% and 90% quantile models, each widened by a split-conformal margin |
| `hot_score` | The hot-ZIP classifier's score. A ranking, not a probability |
| `hot_rank_pct`, `hot_flag` | The score's percentile within the metro; flagged when in the metro's top 20% |
| `run_date`, `model_version`, `mlflow_run_id` | When it ran, the git commit, and the MLflow run with its parameters, metrics and model files |

Intended use: ranking ZIPs within one of the 11 study metros, as one input to research on affordability. Not for
pricing a single home, lending decisions or comparisons outside the study metros.

## Data

- **Rows:** about 1,436 ZIPs in 11 Sun Belt and Western metros, monthly from 2016, in
  [`ml.features_zip_month`](warehouse_design.md#features-ml).
- **Features:** 26, each as published by the row's prediction date (ACS and QCEW are shifted by their release lags):
  price and rent growth lags, volatility and momentum, Redfin sale-to-list and share sold above list, trailing
  permits, metro-wide growth, the ZIP's price relative to its metro, the dollar price level, the 30-year mortgage
  rate, and `cbsa_code` as a category.
- **Targets:** `target_growth_12m` (ZHVI growth from t to t + 12) and `target_top20` (that growth in the top 20% of the
  metro's ZIPs that month).
- **Sources:** Zillow ZHVI and ZORI, Redfin, Census ACS and building permits, BLS QCEW, FRED. Zillow and Redfin restate
  history and the warehouse keeps only the latest release, so past features are a little cleaner than they were live.

## Training and scoring (monthly)

[`ml/train.py`](../ml/train.py) runs in GitHub Actions after `dbt build` on the 20th of each month
(`.\tasks.ps1 train` locally):

1. Fit the point model and the 10% and 90% quantile models on every row whose outcome is known.
2. Compute the conformal margin: quantile models fit on rows known by the start of the last known year, scored on
   that year (about 17,000 rows); the margin is the 80% quantile of their misses.
3. Fit the hot-ZIP classifier (binary, positives weighted 4:1) on every row with a known `target_top20`.
4. Score the latest month, replace any earlier run's scores for that month in `ml.predictions`, and log the
   parameters, metrics and four model files to MLflow (`data/mlflow`, kept in R2 between runs).
5. Check drift (below).

Parameters are fixed and untuned: 600 rounds, learning rate 0.03, 31 leaves, seed 42. Rows are read in a fixed order,
so a rerun on the same data gives the same scores. Package versions are pinned in `uv.lock`.

## Backtest results

**12-month growth forecast** (rolling origin, one origin per quarter; ZIP-level MAE in percentage points):

| Model | Validation (2023) | Test (2024-2025) |
| --- | --- | --- |
| LightGBM | **3.16** | 3.63 |
| Naive (last year's growth) | 5.46 | 3.68 |
| No change | 3.39 | **2.84** |
| Metro AutoETS | 3.82 | 3.15 |

LightGBM beats the naive baseline in both periods but loses the test period to no change and to metro ETS. Its loss
is metro-wide: it kept forecasting gains through the 2024-2025 flattening, which no training year resembled. Within
metros it ranks ZIPs best (within-metro error 1.57 against 1.74-1.78 for the baselines). The conformal band covered
94% of test outcomes at a nominal 80% (mean width 15.6 pp): honest but too wide for a single ZIP. The monthly run
calibrates on the latest known year only; its first band is about 9 pp wide at the median ZIP.

**Hot-ZIP classifier** (test months January 2024 to September 2025, base rate 0.20):

| Model | Precision, top 20% per metro | PR-AUC |
| --- | --- | --- |
| Momentum (last year's growth) | **0.443** | 0.301 |
| Logistic regression | 0.412 | 0.338 |
| LightGBM | 0.405 | **0.342** |

Every model doubles the base rate. LightGBM has the best PR-AUC but does not beat momentum on the published rule's
precision in the test period; it did in 2023 (0.304 against 0.300), when momentum collapsed after the 2022 turn.
SHAP explanations are in the hot-ZIP report.

**Against Gate E** ("every model beats its baseline"): the forecast beats naive and the classifier beats chance and
momentum on PR-AUC, but neither beats the strongest simple baseline on every measure. The dashboard therefore
presents both as within-metro rankings, not price targets.

## Drift monitoring

Each run joins earlier scores with outcomes that have since become known. For the latest matured month it logs the
MAE and the hot-flag precision to MLflow; when the MAE exceeds `MAE_LIMIT` in `ml/train.py`, the worst single test
origin's LightGBM MAE in the backtest (5.32 pp, from October 2024), the run prints a warning and the workflow's `alert` job
fails. GitHub emails a failed scheduled run to whoever last edited its cron line. The first scores were made for September 2026, so the first check runs in
autumn 2027, once Zillow publishes September 2027.

## Known limits

- **Regime change:** the training years are mostly growth with one sharp dip. A slow, flat or falling market is
  under-represented, and the forecast's metro-wide level lags turns.
- **The mortgage rate dominates:** it carries most of the forecast's split gain and, as one national number a month,
  partly stands in for the period.
- **Price-level drift:** the hot-ZIP flags lean on the dollar price level, which today is past most of the training
  range.
- **Noisy single scores:** a different row order moved single test scores by up to 0.25, so ZIPs near a metro's
  80th-percentile cutoff can flip in or out of the flags between runs.
- **Missing drivers:** insurance costs, zoning and local employers are not in the data. The 2024-2025 Florida decline,
  often tied to insurance costs, was missed.
- **Overlapping outcomes:** consecutive months share most of a 12-month window, so the backtest's test months are
  far from independent; a further year could reorder the models.
- **Coverage:** 11 metros only; the models have not been tested anywhere else.
