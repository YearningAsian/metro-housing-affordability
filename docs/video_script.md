# Presentation video script (Phase 17)

The run of show from the project plan, about 7 minutes. The narration is 902 words, about 6.4 minutes at 140 words a
minute; the dashboard demo and pauses fill the rest. Read it aloud with a timer, then cut about 20%, starting with
the segments that run long. Every number comes from the [findings log](findings.md), the
[model card](model_card.md) or the [cluster](clusters_report.md) and [hot-ZIP](hot_zips_report.md) reports, as of
September 2026; recheck them after the next pipeline run.

**The one thing a viewer should repeat:** since 2015 every one of the 11 metros got less affordable, and Austin,
which built the most, barely moved.

## Footage to prepare

| Clip | Source |
| --- | --- |
| Bar chart race, 1920×1080, 22 s | `uv run python notebooks/bar_race.py` writes `data/video/affordability_race.mp4` |
| Bar chart race, 1080×1920, for the short cut | `uv run python notebooks/bar_race.py --vertical` |
| Deck charts | `docs/figures/deck/*.png` (rebuild with `uv run python notebooks/deck_charts.py`) |
| Other charts | `docs/figures/q3_origin_home_values.png`, `forecast_vs_actual.png`, `cluster_maps.png`, `hot_zips_shap_global.png` |
| Architecture | the Mermaid diagram at the top of the README, then a pipeline run under Actions, then the dbt lineage graph on GitHub Pages |
| Dashboard | `uv run --group app streamlit run app/streamlit_app.py`, or the Streamlit Community Cloud URL once deployed |

Recording: OBS Studio or Loom at 1920×1080 and 30 fps, a USB microphone, browser zoom at 125%, notifications off.
Record each segment as its own take; it is easier to cut.

## 1. Hook (0:00–0:30)

**On screen:** the bar chart race, ending on September 2026.

In 2015, the typical home in Seattle cost about four point nine years of the median household's income. Today it
costs six point three. That's the biggest jump among eleven of the fastest-growing metros in the country. And Seattle
isn't alone: every one of the eleven got less affordable. Here's how I measured it, and what I found.

## 2. The question and the metros (0:30–1:00)

**On screen:** the README's "The question" section, then the list of metros.

The question: in fast-growing US metros, where is housing still affordable, and which signals show up before prices
jump? I picked eleven metros: Atlanta, Austin, Charlotte, Dallas–Fort Worth, Denver, Nashville, Orlando, Phoenix,
Raleigh, Seattle and Tampa. That's fourteen hundred and thirty-six ZIP codes, every month from January 2015 to
September 2026.

## 3. The pipeline (1:00–2:00)

**On screen:** the README architecture diagram; a pipeline run under Actions; the dbt lineage graph.

Everything comes from free public data: eleven sources, including Zillow, Redfin, the Census Bureau, the Bureau of
Labor Statistics, the Federal Reserve, the IRS and HUD. Python loaders save each download as Parquet, the bronze
layer. dbt on DuckDB cleans and tests it into silver tables, then joins those into gold tables at two levels: metro
by month and ZIP by month. Two LightGBM models read the gold layer, and MLflow logs every run. On the twentieth of
each month, GitHub Actions reruns all of it. It pulls the warehouse from Cloudflare R2, rebuilds, retrains, and
publishes the results to GitHub Pages. If the forecasts drift or a source goes stale, a job fails and I get an email.
There's no server to keep running.

## 4. Findings (2:00–4:30)

**On screen:** `deck/price_to_income_change.png`.

First, the affordability race. Price-to-income is the typical home value divided by median household income: how
many years of income a home costs. It rose in all eleven metros. Seattle rose most, by one point four four years,
with Nashville close behind. Austin barely moved, up zero point zero four, because it gave back its whole 2022 spike.

**On screen:** `deck/permits_vs_growth.png`.

Why Austin? It built. Austin permitted fifteen homes per thousand residents a year, the most of any metro, and its
home values grew the least: fifty-seven percent over the decade. Across all eleven metros, more permits went with
slower price growth, a correlation of minus point five five. But take Austin out and it nearly vanishes, to minus
point one. With eleven metros, that's a story about Austin, not proof of a law.

**On screen:** `q3_origin_home_values.png`.

Next, who's moving in. Using IRS address changes, I compared each metro's home values with the counties its
newcomers left. In 2022 moves, Tampa's newcomers came from counties with homes eighteen percent pricier than
Tampa's. Seattle's came from the cheapest, twenty-two percent cheaper. And in all eleven metros that ratio fell
after 2014: the destinations got expensive faster than the places people left.

**On screen:** `deck/rent_minus_wage.png`.

Last, renters. From 2015 to 2026, rents outgrew wages in six of the eleven metros. Atlanta was worst: rents up
eighty-one percent, wages up fifty-three, a twenty-eight point gap. In Austin, wages led by forty-four points.

**On screen, 30–60 seconds:** the dashboard. Overview, then pick Atlanta on the metro page and scroll its ZIP map.

All of this is live in the dashboard. The overview ranks the metros. Pick one, say Atlanta, and you get a map of
home value growth by ZIP, home values against wages, and permits. It refreshes every month on its own.

## 5. Machine learning (4:30–6:00)

**On screen:** `forecast_vs_actual.png`.

Then the machine learning. The first model forecasts each ZIP's home value growth over the next twelve months. In a
backtest, it ranked ZIPs within a metro better than every baseline. But here's the miss: in 2024 and 2025, simply
guessing no change beat it overall, with 2.84 points of error against 3.63. The market flattened in a way no
training year had.

**On screen:** `cluster_maps.png`.

I also grouped the ZIPs into six neighborhood types, from "pricey and still rising" to "building boom, prices
slipping". Only thirty-seven percent of ZIPs are in the same type as in late 2019. The pandemic reshuffled whole
suburbs.

**On screen:** `hot_zips_shap_global.png`.

The second model flags ZIPs likely to land in their metro's top fifth for growth next year. SHAP shows what drives
it: a ZIP's own recent growth first, then its price compared with the rest of the metro.

**On screen:** the dashboard's Forecasts page.

It flags two hundred and ninety ZIPs for the coming year. About four in ten flags come true, double the base rate,
but a plain momentum rule does nearly as well. So the dashboard shows these as rankings, not bets.

## 6. Limits and where to find everything (6:00–7:00)

**On screen:** the findings log's caveats, then an end card with the repo, dashboard, findings log and model card
links.

The limits. Census income lags about two years, so the latest ratios run a little high. Zillow's rents are asking
rents for new leases, not what current tenants pay. Eleven metros are too few for correlations to be more than
descriptive. And none of this is investment advice: a "hot" ZIP is often where people get priced out.

Next, I'd like a forecast that copes with a flat market, and a deep dive into one city's 311 calls.

So, the one thing to remember: since 2015, every one of these eleven metros got less affordable, and the one that
built the most, Austin, barely moved. The code, the dashboard, the findings and the model card are all linked
below.

## YouTube chapters

```text
0:00 The biggest affordability swing
0:30 The question and the 11 metros
1:00 The pipeline
2:00 The affordability race
2:40 Supply and prices
3:15 Who is moving in
3:40 Rents against wages
4:00 The dashboard
4:30 The forecast
5:05 Neighborhood types
5:25 Hot ZIPs and SHAP
6:00 Limits and links
```

Set the timestamps to the final edit before uploading; YouTube needs the first chapter at 0:00.

## 60-second vertical cut (LinkedIn)

**On screen:** `affordability_race_vertical.mp4` for the first 20 seconds, then the deck charts cropped to 1080×1920.

Eleven of America's fastest-growing metros. Every one got less affordable since 2015. In Seattle, the typical home
went from 4.9 years of median income to 6.3. Austin barely moved. Why? It built more housing than anywhere else,
fifteen homes per thousand residents a year, and its prices grew the least. Meanwhile in Atlanta, rents rose 81%
while wages rose 53%. I built a pipeline that pulls eleven public data sources every month, rebuilds the warehouse,
retrains two models and updates a live dashboard, with no server to run. The full video and the code are linked in
the comments.
