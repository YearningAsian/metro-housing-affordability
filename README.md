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

The list lives in [`config/metros.yml`](config/metros.yml).

## Data sources

All free and public; no scraping.

| Source | Used for |
| --- | --- |
| [Zillow Research](https://www.zillow.com/research/data/) (ZHVI, ZORI) | Prices, rents |
| [Redfin Data Center](https://www.redfin.com/news/data-center/) | Inventory, days on market, price drops |
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

## Setup (Windows PowerShell)

Needs [uv](https://docs.astral.sh/uv/).

```powershell
.\tasks.ps1 setup   # Python 3.12 env, pre-commit hooks, .env from .env.example
```

Then put your Census, FRED and HUD keys in `.env`.
