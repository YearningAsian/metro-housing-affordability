# Hot-ZIP classifier (Phase 14)

Can we tell ahead of time which ZIPs will land in their metro's top 20% of home value growth over the next 12 months?
This page compares a momentum baseline, logistic regression and LightGBM on held-out months, explains the LightGBM
scores with SHAP, and lists the ZIPs flagged as of September 2026. The code is [`ml/hot_zips.py`](../ml/hot_zips.py);
rerun it with `uv run --group ml --group dev python -m ml.hot_zips` after a pipeline run, then update the numbers
here. The monthly pipeline refits the classifier and writes each month's scores and flags to `ml.predictions`
(`hot_score`, `hot_rank_pct`, `hot_flag`); see the [model card](model_card.md).

> **Read this first.** The model describes market signals in public aggregate data. It is not investment advice, and
> a flag is a ranking, not a promise: on the test months fewer than half of the flagged ZIPs actually landed in the
> top 20%. Fast price growth is not good news for everyone. In a neighborhood where prices climb fastest, renters and
> long-time owners on fixed incomes often face rising rents and property taxes, and many are displaced. A "hot" ZIP
> is as much a warning about affordability as a signal about demand.

**Answer:** yes, clearly better than chance, but not by much more than momentum. On the 2024–2025 test months,
41–51% of flagged ZIPs landed in the top 20%, against a 20% base rate. Simply ranking ZIPs by last year's growth
gets 44–46%. LightGBM has the best PR-AUC (0.342), logistic regression the best precision among the top 20 ZIPs a
month (0.514), and the momentum baseline the best precision within metros (0.443).

## Setup

- **Target:** `target_top20` in [`ml.features_zip_month`](warehouse_design.md#features-ml), true when a ZIP's ZHVI
  growth from month t to t + 12 is in the top 20% of its metro's ZIPs that month.
- **Features:** the same 26 point-in-time features as the [forecast](forecast_report.md), each as published by the
  row's prediction date.
- **Time split:** each model is trained once per period on rows whose outcome was published before the period
  began: rows known by January 2023 (months up to January 2022) for the 2023 validation months, and rows known by
  January 2024 for the 21 test months, January 2024 to September 2025 (30,156 ZIP-months). The test model is not
  refit as the test period goes on.
- **Models:**
  - *Momentum baseline:* rank by last year's ZHVI growth (`zhvi_growth_12m`); ZIPs with under a year of history get
    their metro's median.
  - *Logistic regression:* median imputation, standardization, no class weights (`scikit-learn`).
  - *LightGBM:* the forecast's fixed parameters with a binary objective and the positive class weighted 4:1
    (`scale_pos_weight`), with `cbsa_code` as a category. No tuning.
- **Flags:** a ZIP is flagged when its score is in the top 20% of its metro's ZIPs that month, so every metro has the
  same share flagged as the base rate.

## Results

| Period | Model | Precision, top 20 ZIPs a month | Precision, top 20% per metro | PR-AUC |
| --- | --- | --- | --- | --- |
| Validate (2023) | Momentum | 0.217 | 0.300 | 0.225 |
| | Logistic regression | 0.358 | **0.322** | 0.273 |
| | LightGBM | **0.442** | 0.304 | **0.291** |
| Test (2024–2025) | Momentum | 0.455 | **0.443** | 0.301 |
| | Logistic regression | **0.514** | 0.412 | 0.338 |
| | LightGBM | 0.438 | 0.405 | **0.342** |
| Both | Base rate | 0.200 | 0.200 | 0.200 |

"Top 20 ZIPs a month" takes the 20 highest scores across all metros each month and averages the share that landed
in their metro's top 20%. "Top 20% per metro" flags each metro's top fifth, the rule used for publishing.

Every model beats the 20% base rate on every measure in both periods; the models gain little over momentum.
Momentum was weak in 2023 (0.217), when the 2022 price turn made last year's leaders a poor guide, and strong in
2024–2025, so its usefulness swings with the market. The models are steadier across both periods.

LightGBM precision within metros on the test months ranges from 0.23 (Tampa) and 0.29 (Charlotte) to 0.49 (Atlanta
and Phoenix):

| Metro | Precision | Metro | Precision |
| --- | --- | --- | --- |
| Atlanta | 0.494 | Nashville | 0.467 |
| Austin | 0.482 | Orlando | 0.434 |
| Charlotte | 0.290 | Phoenix | 0.487 |
| Dallas-Fort Worth | 0.398 | Raleigh | 0.376 |
| Denver | 0.417 | Seattle | 0.344 |
| | | Tampa | 0.227 |

**Calibration:** neither model's scores are probabilities. Class weighting pushes LightGBM's scores up, and both
models are overconfident at the top: of the test ZIP-months LightGBM scored around 0.7, about 40% landed in the top
20%. Read a score as a rank within the metro.

![Calibration on the test months](figures/hot_zips_calibration.png)

## What drives the score (SHAP)

SHAP values are LightGBM's own TreeSHAP contributions (`pred_contrib=True`), in log-odds. Over the test months, a
ZIP's own recent growth matters most (12-month and 1-month ZHVI growth), then its price relative to the metro median,
for-sale inventory, and the metro's growth. Metro-wide features (`metro_zhvi_growth_12m`, `mortgage_rate_pct`,
`cbsa_code`) take the same value for every ZIP in a metro that month, so they mostly lift or lower a metro's scores
together; the ranking within a metro rests mainly on the ZIP's own features.

![Global SHAP importance](figures/hot_zips_shap_global.png)

The three highest-scored ZIPs, one each in the three metros with the top scores, as of September 2026, scored by the
model trained on all known outcomes:

![Single-ZIP SHAP explanations](figures/hot_zips_shap_zips.png)

- **85253 (Paradise Valley, Phoenix), score 0.99:** the price level dominates (a $3.3M ZHVI, +2.17), helped by
  metro-wide terms (Phoenix prices down 1.1% over the year) and recent ZIP growth (1.0% last month).
- **75225 (Dallas), score 0.98:** again the price level ($2.08M, +1.81) and metro-wide terms (+0.95 for the metro's falling
  prices, +0.69 for the mortgage rate); its rent level pulls it down slightly (−0.24).
- **32789 (Winter Park, Orlando), score 0.93:** the price level ($817K, +1.34) and metro-wide terms; its for-sale inventory
  pulls it down (−0.40).

In this model a falling metro raises the score of its ZIPs. The top current flags lean on the dollar price level
(`zhvi_usd`, +1.3 to +2.2) far more than the average test ZIP-month (mean |SHAP| 0.18). A likely reason: dollar prices drift up over time, so 2026 values sit at the top of the
training range, where trees give every expensive ZIP the same boost.
Dropping the three dollar-level features (`zhvi_usd`, `zori_usd`, `avg_weekly_wage_usd`) made two of the three test
measures worse (PR-AUC 0.320, within-metro precision 0.369; top-20 precision rose to 0.452), so they stay, but the
current flags favor expensive ZIPs.

## ZIPs flagged for the 12 months from September 2026

290 of 1,436 ZIPs are flagged (each metro's top 20%). The five highest scores per metro (the full list is in
`ml.predictions` and on the dashboard's Forecasts page):

| Metro | ZIPs (score) |
| --- | --- |
| Atlanta | 30663 (0.91), 31816 (0.91), 30641 (0.91), 30306 (0.90), 30222 (0.89) |
| Austin | 78703 (0.91), 78731 (0.91), 78746 (0.91), 78733 (0.90), 78730 (0.88) |
| Charlotte | 28207 (0.92), 28101 (0.81), 28211 (0.80), 28226 (0.80), 28209 (0.76) |
| Dallas-Fort Worth | 75225 (0.98), 75205 (0.98), 75230 (0.97), 76092 (0.97), 75214 (0.96) |
| Denver | 80135 (0.90), 80116 (0.86), 80118 (0.81), 80111 (0.80), 80117 (0.79) |
| Nashville | 37137 (0.87), 37046 (0.86), 37145 (0.84), 38560 (0.83), 37150 (0.81) |
| Orlando | 32789 (0.93), 32836 (0.92), 32709 (0.92), 34734 (0.90), 34756 (0.89) |
| Phoenix | 85253 (0.99), 85262 (0.98), 85259 (0.98), 85377 (0.97), 85255 (0.96) |
| Raleigh | 27608 (0.89), 27607 (0.79), 27518 (0.63), 27508 (0.63), 27542 (0.60) |
| Seattle | 98304 (0.80), 98333 (0.78), 98394 (0.77), 98020 (0.74), 98256 (0.70) |
| Tampa | 33629 (0.84), 33548 (0.82), 34688 (0.80), 33527 (0.77), 33618 (0.77) |

## Caveats and limits

- **Not advice:** this is a description of market signals, not a recommendation to buy, sell or invest. See the
  note at the top on displacement.
- **Modest skill:** about 4 in 10 flagged ZIPs land in the top 20% (a 2x lift), and a momentum rank does nearly as
  well. Precision is lowest in Tampa and Charlotte.
- **Scores are not probabilities:** they are overconfident and inflated by class weighting; use the within-metro rank
  (`hot_rank_pct` in `ml.predictions`).
- **Noisy single scores:** refitting on the same rows in a different order (LightGBM samples rows at random) moved
  single test scores by up to 0.25, so a ZIP near its metro's 80th-percentile cutoff can flip in or out of the flags.
  The code fixes the row order so reruns match, but the spread is real model uncertainty.
- **Price-level drift:** the current flags rely on the dollar price level, which is past most of the training range
  (see SHAP above).
- **One fit per period, no tuning:** the test model is fit once in January 2024 and not refreshed; the parameters are
  the forecast's, untuned.
- **Restated inputs:** Zillow and Redfin restate history and the warehouse keeps only their latest release, so past
  features are slightly cleaner than they were live (see the feature table's limits).
- **Overlapping outcomes:** consecutive months share most of their 12-month window, so the 21 test months are far
  from 21 independent tests.
