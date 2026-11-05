# Findings log (Phase 9)

One entry per question: the answer in one sentence, its number, the chart and the caveats. The numbers come from the
notebooks under `notebooks/09_*.ipynb`, which read only the gold marts, on data through September 2026. Rerun the
notebooks after a pipeline run to refresh them, then update this page.

Shared caveats:

- **ACS income lags.** Metro income is the ACS 1-year estimate, published each September for the year before. It is
  interpolated between vintages, and months after January 2025 carry the 2025 vintage forward
  (`income_is_carried_forward`). There is no 2020 1-year release, so 2019 to 2021 is one straight line.
- **QCEW carry-forward.** Wage growth is null in months after the latest published QCEW quarter, so wage comparisons
  end at 2026 Q1.
- **IRS years.** An IRS tax year *t* compares filing addresses in *t*−1 and *t*, so tax year 2023 is mostly moves made
  in 2022.
- **Small sample.** Eleven metros is too few for metro-level correlations to be more than descriptive.

## Q1. Price-to-income

**Finding:** price-to-income rose in all 11 metros from the 2015 average to the latest 12 months (Oct 2025–Sep 2026).
Seattle rose most, from 4.5 to 6.1 years of median income (+1.59), ahead of Nashville (3.6 to 4.9, +1.34).
Austin rose least (3.8 to 4.1, +0.29) after giving back most of its 2022 spike.

- Number: +1.59 (Seattle), +0.29 (Austin).
- Charts: [trend by metro](figures/q1_price_to_income_trend.png), [ranked change](figures/q1_price_to_income_change.png).
- Notebook: [`09_q1_price_to_income.ipynb`](../notebooks/09_q1_price_to_income.ipynb).
- Caveats: the leader depends on the start year. From 2017, Charlotte rises most (+0.97, against Seattle's +0.93);
  from 2019, Seattle leads again (Spearman rank agreement with the 2015 ranking is 0.89 and 0.85). Austin stays at the
  bottom from every start year. The carried-forward 2025 income vintage slightly overstates the latest ratios. A ratio
  needs no inflation adjustment.

## Q2. Permits against price growth

**Finding:** across the 11 metros, each extra housing unit permitted per 1,000 residents per year in 2016–2025 went
with 3.0 percentage points less home value growth over the decade (r = −0.54). Austin carries that line: it permitted
the most (15.6 per 1,000 a year) and grew the least (+57%). Without Austin the slope is −0.4 pp (r = −0.08).

- Number: −3.0 pp per permit per 1,000 (r = −0.54); −0.4 pp (r = −0.08) without Austin.
- Chart: [permits vs growth](figures/q2_permits_vs_growth.png).
- Notebook: [`09_q2_permits_vs_prices.ipynb`](../notebooks/09_q2_permits_vs_prices.ipynb).
- Caveats: this is a correlation across 11 points, not a supply effect, because fast-growing metros both build more and
  draw more demand. Other windows are weaker: r = −0.32 for 2018–2025, −0.23 for 2020–2025, and −0.25 for
  2016–2020 permits against 2020–2025 growth. Permits lead completions by one to two years. Each county-year's
  permits are scaled up to the BPS annual file, which adds offices that report only once a year.

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

## Q6. Mortgage payment as a share of income

**Finding:** the monthly mortgage and property tax on a typical home now take more than 30% of a median household
income in all 11 metros; in the 2015 average, none passed 30%. Seattle is highest at 46.1% (up from 27.3%), and
Nashville had the next largest rise (20.6% to 35.3%). Atlanta is lowest at 30.5% (up from 17.5%). The share rose faster
than price-to-income because mortgage rates roughly doubled. Principal and interest alone pass 30% in 5 of 11 metros
(Seattle 41.0%).

- Number: 11 of 11 over 30% (none in 2015); Seattle 46.1%, Atlanta 30.5%.
- Chart: [mortgage share by metro](figures/q6_mortgage_share.png).
- Notebook: [`09_q6_q7_mortgage_and_who_can_afford.ipynb`](../notebooks/09_q6_q7_mortgage_and_who_can_afford.ipynb);
  helper `mortgage_share_change()` in [`notebooks/common.py`](../notebooks/common.py). ZHVI with 10% down, 30-year
  fixed at that month's Freddie Mac rate, plus property tax at the metro's effective rate (ACS median real estate
  taxes over ACS median owner home value: 0.42% in Phoenix to 1.52% in Austin in 2025), over median household
  income / 12; the 2015 average against Oct 2025–Sep 2026.
- Caveats: the count depends on the down payment. With 3.5% down (FHA), all 11 metros pass 30%; with 20% down, 6 do.
  Insurance and HOA fees are still left out, so the real cost is higher. The tax rate is what current owners pay on
  what they say their home is worth; Florida's Save Our Homes cap and Texas's homestead cap hold down long-time owners'
  bills, so a new buyer in Tampa, Orlando, Austin or Dallas–Fort Worth likely pays more. The lagged ACS income
  overstates recent shares a little. From 2019 one metro, Seattle, already started above 30% (31.6%).

## Q7. Who can afford the typical home

**Finding:** in Oct 2025–Sep 2026 the households who could pay for a typical home at 30% of income or less ranged
from 31% in Seattle to 50% in Atlanta. In 2015 they ranged from 54% (Seattle) to 71% (Atlanta). The share fell in all
11 metros, by a median of 19 points. Seattle now takes an income of about $184,000.

- Number: 31% (Seattle) to 50% (Atlanta), down from 54% to 71%. The dashboard's Findings page shows each metro.
- Chart: [who can afford the typical home](figures/q7_who_can_afford.png).
- Notebook: [`09_q6_q7_mortgage_and_who_can_afford.ipynb`](../notebooks/09_q6_q7_mortgage_and_who_can_afford.ipynb);
  helper `affordable_share()` in [`notebooks/common.py`](../notebooks/common.py). The income needed is 12 times the
  Q6 payment (with taxes, 10% down) divided by 30%. The share of households at or above it comes from the ACS 1-year
  income brackets (B19001), linear within a bracket. 2015 uses the 2015 brackets and payments; the latest 12 months
  use the 2025 brackets.
- Caveats: it counts all households, renters and owners alike, and ignores savings for the down payment, debts and
  credit. Wealthier buyers with equity from a sale need less income, so this is a rough reach, not a count of buyers.
  The 2025 brackets are a year older than the latest payments, which understates the latest share a little while
  incomes rise. Above $200,000 (the open top bracket) the method would return an upper bound; no metro needs that
  much yet.

## Q8. What drove the rise in the mortgage share

**Finding:** prices did the damage first and rates second. From 2015 to 2021, home prices alone would have raised the
mortgage share by a median 0.53 log points (about 70%), but falling rates (−0.13) and rising incomes (−0.28) absorbed
most of it, for a net +0.14. From 2021 to Oct 2025–Sep 2026, rates and tax were the largest part in all 11 metros
(+0.35), ahead of prices (+0.20) and against income (−0.15). Over the whole span prices still lead: in Seattle the net
+0.52 is +0.75 from prices, +0.22 from financing and −0.45 from income.

- Number: 2021 to now, financing +0.35 against prices +0.20 (medians); 2015 to now, prices +0.73, financing +0.22,
  income −0.44.
- Chart: [the split by metro](figures/q8_mortgage_share_split.png); the dashboard's Findings page has it for each period.
- Notebook: [`09_q8_mortgage_share_split.ipynb`](../notebooks/09_q8_mortgage_share_split.ipynb); helper
  `mortgage_share_split()` in [`notebooks/common.py`](../notebooks/common.py). The log of the Q6 share is log price +
  log financing cost per dollar (rate and property tax) − log income, so the three parts add up exactly; each period is
  the mean of its monthly logs, which matches the Q6 change to within 0.001.
- Caveats: log points are relative, not percentage points of income (0.10 means a share about 10% higher). The
  financing part mixes rates and tax rates; tax rates fell a little in most metros, so the rate effect alone is a bit
  larger. Austin is the one metro where prices fell after 2021 (−0.05). Lagged ACS income makes the latest income part
  a little too small.

## Q9. Price pressure on lower-income ZIPs

**Finding:** fast price growth landed mostly on lower-income ZIPs. Of each metro's top fifth of ZIPs for home value
growth from 2015 to Oct 2025–Sep 2026, 88% had a 2015 income below the median of the metro's ZIPs, against 50% if
growth ignored income. That share ranges from 60% in Seattle to 100% in Atlanta, Dallas–Fort Worth, Orlando and
Raleigh. 248 of 1,403 ZIPs are lower-income ZIPs with top-fifth growth; Atlanta's 30314 (Westside) grew most, about
5.6 times its 2015 value. At the median, ACS income in these ZIPs rose about as fast as in other lower-income ZIPs
(+62% against +60%), with large gaps only in Phoenix (+22 points) and Orlando (+14).

- Number: 88% of top-fifth growth ZIPs were lower-income (60% Seattle to 100%); 248 pressure ZIPs.
- Chart: [maps by metro](figures/q9_price_pressure_maps.png); the top 3 per metro are in the notebook and on the
  dashboard's Findings page.
- Notebook: [`09_q9_gentrification_pressure.ipynb`](../notebooks/09_q9_gentrification_pressure.ipynb).
- Caveats: this is an association, not displacement; price growth says nothing about who moved out. Cheap homes grew
  faster everywhere in this period (Q5), so part of the pattern is a cheap-home effect, not a neighborhood one. ZIP
  income is the ACS 5-year estimate, so the 2015 value covers 2011–2015 and the latest covers 2020–2024, and changes in
  who lives there show up late. Some flagged ZIPs are large exurban or rural ones (for example, near Mount Rainier and
  in Park County, Colorado), which dominate the maps by area. ZIPs with no 2015 ZHVI or ACS income are left out.

## Q10. Does climate risk explain the Tampa and Orlando declines?

**Finding:** no, not as FEMA measures it. From the 2024 average to Oct 2025–Sep 2026, Austin fell more (−7.3% at the
median ZIP) than Tampa (−7.0%), and Orlando (−4.5%) fell as much as Dallas–Fort Worth, with almost no hurricane risk
in either Texas metro. Tampa and Orlando carry the highest expected hurricane losses (0.070% and 0.029% of building
value a year, against at most 0.005% elsewhere), but within them higher risk does not go with larger falls (r = +0.36
for hurricanes, +0.12 for all hazards, 0.00 for flooding). The +0.36 is mostly one county: Pinellas fell most (−9.4%
at the median ZIP, 33716 −23%) with the lowest modeled hurricane rate in Tampa, and without it r is −0.09. Pinellas
took Hurricane Helene's storm surge in September 2024, which a fixed risk index does not record; that is a candidate
explanation, not one tested here.

- Number: within Tampa and Orlando, r = +0.36 between the hurricane loss rate and the value change, −0.09 without
  Pinellas, −0.11 in Orlando alone; across all ZIPs within their metros, +0.05 to +0.12. None supports a risk discount.
- Chart: [metro medians and Florida ZIPs](figures/q10_climate_risk.png), also on the dashboard's Findings page.
- Notebook: [`09_q10_climate_risk.ipynb`](../notebooks/09_q10_climate_risk.ipynb). Risk: FEMA National Risk Index
  v1.20 (December 2025), expected annual building loss over building value, from `gold.dim_zip`.
- Caveats: the index is by county, so inside the two Florida metros it varies only between 8 counties. It measures
  physical risk, not insurance premiums, which rose statewide in Florida for reasons a county risk score does not
  capture (litigation, reinsurance costs); a null here does not rule out insurance. The release postdates the period,
  so it is not used as a forecast feature, where it would leak.

## Robustness

- **Start years:** see the Q1, Q2 and Q4 caveats. The Q1 leader changes with the start year. The Q2 slope weakens in
  every other window. The Q4 ranking holds.
- **Inflation:** CPI-U rose 39.5% from the 2015 average to Oct 2025–Sep 2026. In real terms, home values grew from
  +15% (Austin) to +57% (Charlotte), against +60% to +119% nominal
  ([chart](figures/robustness_real_vs_nominal.png)). Price-to-income, rent-to-wage and rent-minus-wage gaps do not
  change, because the same CPI divides both sides.
- Notebook: [`09_robustness.ipynb`](../notebooks/09_robustness.ipynb).
