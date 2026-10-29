# Findings log (Phase 9)

One entry per question: the answer in one sentence, its number, the chart and the caveats. The numbers come from the
notebooks under `notebooks/09_*.ipynb`, which read only the gold marts, on data through September 2026. Rerun the
notebooks after a pipeline run to refresh them, then update this page.

Shared caveats:

- **ACS income lags.** ACS 5-year income averages five survey years, so it trails current incomes by about two years.
  Months after 2024 reuse the 2020–2024 vintage (`income_is_carried_forward`).
- **QCEW carry-forward.** Wage growth is null in months after the latest published QCEW quarter, so wage comparisons
  end at 2026 Q1.
- **IRS years.** An IRS tax year *t* compares filing addresses in *t*−1 and *t*, so tax year 2023 is mostly moves made
  in 2022.
- **Small sample.** Eleven metros is too few for metro-level correlations to be more than descriptive.

## Q1. Price-to-income

**Finding:** price-to-income rose in all 11 metros from the 2015 average to the latest 12 months (Oct 2025–Sep 2026).
Seattle rose most, from 4.9 to 6.3 years of median income (+1.44), with Nashville close behind (3.9 to 5.3, +1.39).
Austin rose least (4.2 to 4.2, +0.04) after giving back its whole 2022 spike.

- Number: +1.44 (Seattle), +0.04 (Austin).
- Charts: [trend by metro](figures/q1_price_to_income_trend.png), [ranked change](figures/q1_price_to_income_change.png).
- Notebook: [`09_q1_price_to_income.ipynb`](../notebooks/09_q1_price_to_income.ipynb).
- Caveats: the leader depends on the start year. From 2017 or 2019, Charlotte rises most and Seattle drops to the
  middle (Spearman rank agreement with the 2015 ranking is 0.75 and 0.77). Austin and Denver stay at the bottom from
  every start year. The carried-forward 2024 income vintage slightly overstates the latest ratios. A ratio needs no
  inflation adjustment.

## Q2. Permits against price growth

**Finding:** across the 11 metros, each extra housing unit permitted per 1,000 residents per year in 2016–2025 went
with 3.1 percentage points less home value growth over the decade (r = −0.55). Austin carries that line: it permitted
the most (15.4 per 1,000 a year) and grew the least (+57%). Without Austin the slope is −0.6 pp (r = −0.10).

- Number: −3.1 pp per permit per 1,000 (r = −0.55); −0.6 pp (r = −0.10) without Austin.
- Chart: [permits vs growth](figures/q2_permits_vs_growth.png).
- Notebook: [`09_q2_permits_vs_prices.ipynb`](../notebooks/09_q2_permits_vs_prices.ipynb).
- Caveats: this is a correlation across 11 points, not a supply effect, because fast-growing metros both build more and
  draw more demand. Other windows are weaker: r = −0.33 for 2018–2025, −0.24 for 2020–2025, and −0.22 for
  2016–2020 permits against 2020–2025 growth. Permits lead completions by one to two years.

## Q3. Where newcomers come from

**Finding:** in 2022 moves, newcomers to 6 of 11 metros came from counties with pricier homes than the metro, on a
people-weighted average. Tampa led at +18%, with 61% of its newcomers from pricier counties. Seattle's newcomers came
from the cheapest counties (−22%), and Austin's were second (−14%). From 2014 to 2022 the ratio fell in all 11 metros,
because destination home values rose faster than the origins' values.

- Number: +18% (Tampa), −22% (Seattle); the ratio fell in 11 of 11 metros since 2014.
- Chart: [origin vs metro home values](figures/q3_origin_home_values.png); the top 3 origin counties per metro are in
  the notebook (for example, Nashville's top origin is Montgomery County, TN, with 2,817 people).
- Notebook: [`09_q3_migration_origins.ipynb`](../notebooks/09_q3_migration_origins.ipynb).
- Caveats: the IRS suppresses flows under 20 returns and counts only people who file, so small flows and non-filers
  are missing. About 0.3% of people come from counties with no Zillow ZHVI and are left out of the ratio. Moves within
  a metro are excluded.

## Q4. Rent growth against wage growth

**Finding:** from 2015 Q1 to 2026 Q1, rents outgrew wages in 6 of 11 metros. The gap was largest in Atlanta: rents
rose 81% and wages 53%, a gap of +28 pp. Wages led most in Austin: rents rose 34% and wages 78% (−44 pp).

- Number: +28 pp (Atlanta), −44 pp (Austin).
- Charts: [cumulative gap](figures/q4_rent_minus_wage.png), [year-over-year gap by quarter](figures/q4_gap_by_quarter.png).
- Notebook: [`09_q4_rent_vs_wages.ipynb`](../notebooks/09_q4_rent_vs_wages.ipynb).
- Caveats: ZORI is asking rent for new leases, which moves faster than what sitting tenants pay. The QCEW average weekly
  wage is total pay divided by jobs, so a shift toward high-paid jobs raises it; this likely inflates wage growth in
  Seattle and Austin. Both ends are Q1 because QCEW wages are seasonal. The ranking is stable from 2017 Q1 and 2019 Q1
  (Spearman 0.99 and 0.95), but the gaps shrink: from 2019 Q1, Atlanta's gap is +7 pp. CPI cancels out of the
  comparison.

## Q5. Fastest-rising ZIPs a year earlier

**Finding:** a year before a ZIP landed in its metro's top 20% for 12-month home value growth, it was already rising
faster than its metro. Its past-12-month growth sat +0.74 standard deviations above the other ZIPs in the metro.
ZIPs in the top fifth of their metro on that measure turned hot 44% of the time, against a 20% base rate. Hot ZIPs also
had lower incomes (−0.34 SD) and cheaper homes (−0.26 SD) than their metro.

- Number: +0.74 SD; a 44% hit rate against a 20% base rate.
- Chart: [hot ZIP profile](figures/q5_hot_zip_profile.png); hit rates by quintile are in the notebook.
- Notebook: [`09_q5_rising_zips.ipynb`](../notebooks/09_q5_rising_zips.ipynb).
- Caveats: momentum vanished or reversed in the January 2021 and 2022 snapshots (−0.04 and −0.27 SD), when the
  2021–2022 boom lifted lagging ZIPs. A Phase 14 model must not rely on momentum alone. The features are not yet
  shifted by their publication lags; ACS income and population appear a year or more late, and Phase 11 fixes this.
  ZORI-based features cover under half of ZIP-years (44–49%). Permits and migration are county rates spread to ZIPs.
  14,247 ZIP-years (1,436 ZIPs, January 2016–2025).

## Robustness

- **Start years:** see the Q1, Q2 and Q4 caveats. The Q1 leader changes with the start year. The Q2 slope weakens in
  every other window. The Q4 ranking holds.
- **Inflation:** CPI-U rose 39.5% from the 2015 average to Oct 2025–Sep 2026. In real terms, home values grew from
  +15% (Austin) to +57% (Charlotte), against +60% to +119% nominal
  ([chart](figures/robustness_real_vs_nominal.png)). Price-to-income, rent-to-wage and rent-minus-wage gaps do not
  change, because the same CPI divides both sides.
- Notebook: [`09_robustness.ipynb`](../notebooks/09_robustness.ipynb).
