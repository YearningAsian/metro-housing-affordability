# Data dictionary

What each source looks like, how it is keyed, what its numbers mean and how late it arrives. Every fact here was checked against one downloaded sample, profiled in [`notebooks/02_source_profiling.ipynb`](../notebooks/02_source_profiling.ipynb). Samples come from [`notebooks/download_samples.py`](../notebooks/download_samples.py) and land in `data/samples/` (git-ignored).

Snapshot date: **2026-10-27**. Lags and latest periods are as observed on that day.

## Conventions

- **Geography codes are text.** ZIP, ZCTA, county FIPS and CBSA codes keep their leading zeros (`01001`, `00601`). Read them as `VARCHAR`, never as numbers.
- **County FIPS** is 5 characters: 2-digit state + 3-digit county. Some sources split it into two columns; join them before use.
- **Months** are stored as the first day of the month (`DATE`) in the warehouse. Zillow uses month-end dates and BPS uses `YYYYMM`; both get converted in staging.
- **Nulls.** Each source has its own missing-value marker (`NA`, `.`, `-1`, `-666666666`). Staging turns every one of them into `NULL`. They are listed per source below.
- **Money** is nominal US dollars unless a row says otherwise. Inflation adjustment uses CPI-U from FRED.
- **Dropped columns.** Source-computed changes (Redfin `*_MOM`, `*_YOY`; QCEW `oty_*`; QCEW location quotients `lq_*`) are not used. The warehouse computes its own growth rates so every metric uses one method.

## Summary

| Source | Grain (primary key) | Date column | Geography | Units | Seasonal adjustment | Latest period on 2026-10-27 | Typical release lag |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Zillow ZHVI | (`RegionID`, month) | month-end column headers | ZIP, Zillow metro | USD | SA, smoothed | 2026-09 | About 2–3 weeks after month end (mid-month) |
| Zillow ZORI | (`RegionID`, month) | month-end column headers | ZIP, Zillow metro | USD per month | NSA, smoothed (SA files exist) | 2026-09 | About 2–3 weeks after month end |
| Redfin metro | (`TABLE_ID`, `PERIOD_BEGIN`, `PROPERTY_TYPE_ID`, `IS_SEASONALLY_ADJUSTED`) | `PERIOD_BEGIN` | CBSA or metro division | mixed, see below | both SA and NSA rows | 2026-05 | Normally about 3 weeks; **feed stale** since 2026-06-02 |
| Redfin ZIP | same as metro | `PERIOD_BEGIN` (90-day window) | ZIP | mixed | NSA only | window starting 2026-03 | Normally about 3 weeks; **feed stale** |
| Census BPS | (`survey_date`, `cbsa_code`) or (`survey_date`, `state_fips`, `county_fips`) | `survey_date` (`YYYYMM`) | CBSA, county | units, buildings, value | NSA | 2026-08 | About 6–8 weeks after month end |
| ACS 5-year | (`geo_id`) per vintage | vintage (end year) | ZCTA, county, CBSA | USD, persons, percent | n/a (5-year pooled) | 2020–2024 | About 11–12 months after the last year (December release) |
| BLS QCEW | (`area_fips`, `own_code`, `industry_code`, `agglvl_code`, `size_code`, `year`, `qtr`) | `year`, `qtr` | county, MSA, state | jobs, USD | NSA | 2026 Q1 | About 5–7 months after quarter end |
| FRED | (`series_id`, `date`) | `date` | national, metro (LAUS) | percent, index | per series | 2026-10-22 (weekly) | Mortgage: same week; CPI: about 2 weeks; metro unemployment: about 8 weeks |
| IRS SOI migration | (`y2` state+county, `y1` state+county) | filing-year pair | county pairs | returns, exemptions, USD thousands | n/a (annual) | 2022–2023 | About 2 years after the second tax year |
| HUD FMR | (`zip_code`) per area, or (`fips_code`) | fiscal year | ZIP (Small Area), county, FMR area | USD per month | n/a (annual) | FY2027 | Published before the fiscal year starts on 1 October |
| HUD-USPS crosswalk | (`zip`, `geoid`) per quarter | `year`, `quarter` | ZIP to county, ZIP to CBSA | share 0–1 | n/a | 2026 Q2 | About 1–2 quarters |
| CBSA delineation | (`FIPS State Code`, `FIPS County Code`) | vintage | county to CBSA | n/a | n/a | July 2023 | Irregular (OMB revisions) |
| Cartographic boundaries | (`GEOID`) | vintage | CBSA, county, ZCTA | square metres | n/a | 2024 (ZCTA 2020) | Annual; ZCTA shapes only after each decennial census |

**Point-in-time rule for features (Phase 11).** A row for month *m* may only use a value whose release date is on or before *m*. Use these availability rules: Zillow month *m* at *m*+1 (around the 16th); Redfin month *m* at *m*+1; BPS month *m* at *m*+2; QCEW quarter *q* at the end of the second quarter after *q*; ACS 5-year ending year *Y* from December of *Y*+1; IRS pair (*Y*-1, *Y*) from about the end of *Y*+2.

## Study metros across sources

Each source names the 11 metros differently. The Zillow and Redfin keys live in `config/metros.yml`, and `dim_metro` carries all of them (see [Geography backbone](#geography-backbone)).

| Metro | CBSA (2023) | Zillow metro `RegionID` | Redfin `TABLE_ID` | QCEW `area_fips` | Metro divisions (2023) |
| --- | --- | --- | --- | --- | --- |
| Atlanta | 12060 | 394347 | 12060 | C1206 | 12054, 31924 |
| Austin | 12420 | 394355 | 12420 | C1242 | none |
| Charlotte | 16740 | 394458 | 16740 | C1674 | none |
| Dallas-Fort Worth | 19100 | 394514 | 19124 + 23104 | C1910 | 19124, 23104 |
| Denver | 19740 | 394530 | 19740 | C1974 | none |
| Nashville | 34980 | 394902 | 34980 | C3498 | none |
| Orlando | 36740 | 394943 | 36740 | C3674 | none |
| Phoenix | 38060 | 394976 | 38060 | C3806 | none |
| Raleigh | 39580 | 395012 | 39580 | C3958 | none |
| Seattle | 42660 | 395078 | 42644 + 45104 | C4266 | 21794, 42644, 45104 |
| Tampa | 45300 | 395148 | 45300 | C4530 | 41304, 45294 |

Notes:

- Zillow's metro file has no CBSA code. Match on `RegionID` (above), never on name: `Austin, TX` and `Austin, MN` both exist.
- Redfin splits Dallas-Fort Worth and Seattle into metro divisions, and Seattle uses pre-2023 divisions (no Everett, 21794). Redfin medians cannot be added up, so for these two metros use the largest division (19124 Dallas, 42644 Seattle) or build the metro from Redfin ZIP rows. Phase 5 decides.
- The ZIP-level Zillow `Metro` column holds pre-2023 CBSA titles (e.g. `Denver-Aurora-Lakewood, CO`) and is null for 12.4% of ZHVI ZIPs. Assign ZIPs to metros with the HUD crosswalk instead.
- FRED metro unemployment series follow `LAUMT` + state FIPS + CBSA + `000000` + `03` (rate). Only Nashville, `LAUMT473498000000003`, was pulled; the other ten IDs are confirmed in Phase 4.

---

## Zillow (ZHVI, ZORI)

Files from `https://files.zillowstatic.com/research/public_csvs/`:

- ZHVI: `{Zip,Metro}_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv`
- ZORI: `{Zip,Metro}_zori_uc_sfrcondomfr_sm_month.csv`

**Shape.** Wide: one row per region, one column per month (`2000-01-31`, …). Staging unpivots to (`RegionID`, month, value). Rows after unpivot: ZIP ZHVI 6,508,601; ZIP ZORI 469,420; metro ZHVI 238,029; metro ZORI 53,977. No duplicate keys.

**Coverage.** ZHVI from 2000-01, ZORI from 2015-01, both to 2026-09. Share of ZHVI ZIPs with a ZORI value: 11% in 2015, 48% in 2022, 88% in 2026. ZIP-level rent models before about 2021 therefore cover a minority of ZIPs.

**Quirks.**

- `RegionName` is the ZIP for ZIP files. Read it as text: some ZIPs start with `0`.
- Metro files contain one `country` row (`RegionType = 'country'`, United States). Filter `RegionType = 'msa'`.
- ZORI is not seasonally adjusted in the current sample, while ZHVI is. Seasonally adjusted ZORI files (`…_zori_uc_sfrcondomfr_sm_sa_month.csv`) exist. **Decision for Phase 4:** download the SA ZORI file so prices and rents are both SA.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `RegionID` | BIGINT | id | Zillow region ID. Key for metros; stable across releases. |
| `RegionName` | VARCHAR | ZIP or name | ZIP code (5 chars) in ZIP files; metro name (`Nashville, TN`) in metro files. |
| `RegionType` | VARCHAR | category | `zip`, `msa` or `country`. |
| `State` | VARCHAR | state code | Two-letter state. |
| `CountyName` | VARCHAR | name | County of the ZIP (ZIP files only). Informational; not used for joins. |
| `month` | DATE | month | Unpivoted column header; month-end in the file, converted to month start. |
| `zhvi` | DOUBLE | USD | Typical home value: mid tier (33rd–67th percentile), single-family and condo, smoothed, seasonally adjusted. |
| `zori` | DOUBLE | USD per month | Typical observed market asking rent: single-family, condo and multifamily, smoothed. |

## Redfin market tracker

Files from `https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/`: `redfin_metro_market_tracker.tsv000.gz` (metro, 579,544 rows) and `zip_code_market_tracker.tsv000.gz` (ZIP, 9,725,026 rows, 1.5 GB). Tab-separated, gzip. `NA` means null.

**Grain.** Metro rows are calendar months (`PERIOD_DURATION = 30`), in both SA and NSA versions. ZIP rows are rolling 90-day windows (`PERIOD_DURATION = 90`), NSA only; `PERIOD_BEGIN` is the window start and `PERIOD_END` the last day of the third month. For a monthly ZIP series, key each window on its `PERIOD_END` month.

**Staleness (risk).** Both files show `LAST_UPDATED` 2026-06-02. Metro data ends 2026-05 and ZIP data ends with the window 2026-03 to 2026-05. Redfin normally updates monthly. Phase 4 must check whether the feed moved or stopped before relying on it.

**Quirks.**

- `TABLE_ID` is the CBSA or metro-division code for metro rows, but a Redfin-internal ID for ZIP rows. Take the ZIP from `REGION` (`Zip Code: 37203`).
- ZIP rows have no `MONTHS_OF_SUPPLY` and no `PRICE_DROPS` (100% null). The Phase 11 "share of price drops" feature is only available at metro grain.
- Seasonally adjusted counts can be negative (5 negative `INVENTORY` values among 33,295 SA metro rows). Use NSA counts for levels and SA rows only for trend charts.
- Outliers: ZIP `MEDIAN_SALE_PRICE` and `MEDIAN_PPSF` reach 999,999,999, and `MEDIAN_LIST_PRICE` reaches 2,000,000,001. Phase 7 adds range tests; small ZIPs with few sales are noisy.
- `PARENT_METRO_REGION_METRO_CODE` gives each ZIP's metro (CBSA or division) as Redfin assigns it.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `PERIOD_BEGIN` | DATE | day | First day of the period. |
| `PERIOD_END` | DATE | day | Last day of the period. |
| `PERIOD_DURATION` | INTEGER | days | 30 (metro, monthly) or 90 (ZIP, rolling three months). |
| `REGION_TYPE` | VARCHAR | category | `metro` or `zip code`. |
| `TABLE_ID` | BIGINT | id | Metro: CBSA or metro-division code. ZIP: Redfin internal, do not use. |
| `REGION` | VARCHAR | text | Metro name, or `Zip Code: NNNNN` (parse the ZIP). |
| `IS_SEASONALLY_ADJUSTED` | BOOLEAN | flag | True for SA rows (metro only). |
| `PROPERTY_TYPE_ID` | INTEGER | category | -1 All Residential, 3 Condo/Co-op, 4 Multi-Family (2–4 Unit), 6 Single Family Residential, 13 Townhouse. Use -1 unless a model needs a split. |
| `MEDIAN_SALE_PRICE` | DOUBLE | USD | Median closing price of homes sold in the period. |
| `MEDIAN_LIST_PRICE` | DOUBLE | USD | Median asking price of listings added in the period. |
| `MEDIAN_PPSF` | DOUBLE | USD per sq ft | Median sale price per square foot. |
| `HOMES_SOLD` | DOUBLE | homes | Closed sales in the period. |
| `PENDING_SALES` | DOUBLE | homes | Listings that went under contract in the period. |
| `NEW_LISTINGS` | DOUBLE | homes | Listings added in the period. |
| `INVENTORY` | DOUBLE | homes | Active listings at the end of the period. |
| `MONTHS_OF_SUPPLY` | DOUBLE | months | Inventory divided by monthly sales. Metro only. |
| `MEDIAN_DOM` | DOUBLE | days | Median days on market in the period. |
| `AVG_SALE_TO_LIST` | DOUBLE | ratio | Mean of sale price divided by final list price (1.0 = at asking). |
| `SOLD_ABOVE_LIST` | DOUBLE | share 0–1 | Share of sales that closed above list price. |
| `PRICE_DROPS` | DOUBLE | share 0–1 | Share of active listings with a price cut. Metro only. |
| `OFF_MARKET_IN_TWO_WEEKS` | DOUBLE | share 0–1 | Share of new listings that went pending within two weeks. |
| `PARENT_METRO_REGION_METRO_CODE` | BIGINT | CBSA or division code | Metro the ZIP belongs to, per Redfin. |
| `LAST_UPDATED` | VARCHAR | timestamp | When Redfin last refreshed the file. Used for freshness checks. |

## Census Building Permits Survey (BPS)

Files from `https://www2.census.gov/econ/bps/`:

- CBSA: `CBSA%20(beginning%20Jan%202024)/cbsaYYMMc.txt` (921 rows for 2026-08)
- County: `County/coYYMMc.txt` (3,018 rows)

`c` is the current-month file; `y` is year to date and includes late corrections. Phase 4 should load monthly `c` files and replace each year with its final `y` file when it appears. Layout reference: [cbsaasc.pdf](https://www2.census.gov/econ/bps/Documentation/cbsaasc.pdf); the county layout is in the same [Documentation](https://www2.census.gov/econ/bps/Documentation/) folder.

**Format.** Comma-separated, latin-1, two header rows plus a blank line (skip 3 lines and name the columns). Names are space-padded, with a double space before the state (`Raleigh-Cary  NC`).

**Units differ between files.** `*_value` is in **thousands of dollars** in the CBSA file and in **dollars** in the county file. Checked: one-unit value per unit is 340 in the CBSA file and 339,102 in the county file.

**Quirks.**

- `header_code`: 2 = metro in a CSA, 4 = metro not in a CSA, 5 = micropolitan. The file has no CSA summary rows.
- CBSA titles follow the 2023 delineation, and all 11 study CBSAs are present. Dallas-Fort Worth is a single 19100 row.
- Data are reported plus imputed. The `_rep` columns hold the reported-only part; use the totals.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `survey_date` | VARCHAR | `YYYYMM` | Month the permits were issued. |
| `cbsa_code` | VARCHAR(5) | CBSA | CBSA code (CBSA file). |
| `state_fips`, `county_fips` | VARCHAR(2), VARCHAR(3) | FIPS | County key (county file). |
| `header_code` | VARCHAR | category | Metro/micro type (CBSA file). |
| `u1_units` | BIGINT | housing units | Units authorized in single-family (1-unit) buildings. |
| `u2_units` | BIGINT | housing units | Units in 2-unit buildings. |
| `u34_units` | BIGINT | housing units | Units in 3–4 unit buildings. |
| `u5p_units` | BIGINT | housing units | Units in buildings with 5 or more units. |
| `u*_bldgs` | BIGINT | buildings | Buildings authorized, by the same size classes. |
| `u*_value` | BIGINT | USD thousands (CBSA) / USD (county) | Construction value of the authorized units. |
| `total_units` (derived) | BIGINT | housing units | `u1_units + u2_units + u34_units + u5p_units`. |

## Census ACS 5-year

API `https://api.census.gov/data/2024/acs/acs5` (vintage 2020–2024). The 2025 vintage (2021–2025) returns 404 and is expected in December 2026.

**Rows.** 33,772 ZCTAs, 3,222 counties (includes Puerto Rico), 935 CBSAs. All 11 study CBSAs are present.

**Quirks.**

- `-666666666` means "not available" (sample too small). Counts in the ZCTA file: income 3,225, rent 8,021, rent share 7,440. Staging sets them to `NULL`.
- Top-coded values: income `250001` means 250,000 or more; rent `3501` means 3,500 or more; rent share `51.0` is the top code for 50% or more. Keep the value and add a `*_topcoded` flag.
- Dollar values are in inflation-adjusted dollars of the vintage's last year (2024 dollars for 2020–2024).
- Each vintage is a five-year pooled estimate. Assign it to its end year and do not read single-year changes into overlapping vintages.
- ACS publishes ZCTAs, not ZIPs. Phase 3 maps ZIPs to ZCTAs.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `geo_id` | VARCHAR | ZCTA, county FIPS or CBSA | Geography code built from the API's geography columns. |
| `vintage_end_year` | INTEGER | year | Last year of the five-year period (2024). |
| `median_hh_income` (`B19013_001E`) | INTEGER | USD per year | Median household income in the past 12 months. |
| `population` (`B01003_001E`) | INTEGER | persons | Total population. |
| `median_gross_rent` (`B25064_001E`) | INTEGER | USD per month | Median gross rent (contract rent plus utilities) of renter-occupied units paying cash rent. |
| `rent_pct_income` (`B25071_001E`) | DOUBLE | percent | Median gross rent as a percentage of household income. |

## BLS QCEW

File `https://data.bls.gov/cew/data/api/{year}/{qtr}/industry/10.csv` (industry 10 = all industries). 17,729 rows for 2026 Q1.

**Quirks.**

- `area_fips` mixes levels: county (`47037`), state (`47000`), US (`US000`), CSA (`CS400`) and MSA (`C` + first four CBSA digits, e.g. `C3498`).
- Use `agglvl_code` 40 (MSA, all owners) for metros and 70/71 (county total / by ownership) for counties. `own_code` 0 = all owners, 5 = private.
- `disclosure_code = 'N'` means suppressed; the numbers are 0. No `own_code = 0` total is suppressed. Ownership splits are: at county level (agglvl 71), 145 state-government, 165 local-government and 28 private rows. Use `own_code = 0`; if private-only is needed, treat suppressed rows as `NULL`.
- Employment is reported per month of the quarter (`month1`–`month3`). For a monthly series use each column for its own month.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `area_fips` | VARCHAR | area code | County FIPS, state, MSA (`Cxxxx`) or CSA. |
| `own_code` | VARCHAR | category | Ownership: 0 all, 1 federal, 2 state, 3 local, 5 private. |
| `agglvl_code` | VARCHAR | category | Aggregation level (40 MSA, 70 county total, 71 county by ownership). |
| `year`, `qtr` | INTEGER | year, quarter | Reference quarter. |
| `disclosure_code` | VARCHAR | flag | `N` = suppressed. |
| `qtrly_estabs` | BIGINT | establishments | Establishments in the quarter. |
| `month1_emplvl`–`month3_emplvl` | BIGINT | jobs | Employment in each month of the quarter. |
| `total_qtrly_wages` | BIGINT | USD per quarter | Total wages paid in the quarter. |
| `avg_wkly_wage` | BIGINT | USD per week | Average weekly wage: total wages / average employment / 13. |

## FRED

API `https://api.stlouisfed.org/fred/series/observations?series_id=…&file_type=json`. The value `.` means missing (one observation each in CPI and Nashville unemployment).

| Series | Frequency | SA | Unit | Latest on 2026-10-27 | Definition |
| --- | --- | --- | --- | --- | --- |
| `MORTGAGE30US` | Weekly (Thursday) | NSA | percent | 2026-10-22 | Freddie Mac 30-year fixed mortgage average rate. |
| `CPIAUCSL` | Monthly | SA | index, 1982–84 = 100 | 2026-09 | CPI for all urban consumers, all items. Used to deflate dollar values. |
| `LAUMT473498000000003` | Monthly | NSA | percent | 2026-08 | Unemployment rate, Nashville MSA (BLS LAUS). One series per metro. |

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `series_id` | VARCHAR | id | FRED series ID. |
| `date` | DATE | day | Observation date (week ending Thursday for weekly series; month start for monthly). |
| `value` | DOUBLE | per series | Observation; `NULL` when FRED returns `.`. |

## IRS SOI county migration

Files `https://www.irs.gov/pub/irs-soi/countyinflow2223.csv` (90,048 rows) and `countyoutflow2223.csv` (90,358 rows). Latin-1. The 2023–2024 files return 404. The pair "2022–2023" compares addresses on tax returns filed for tax year 2022 with those filed for 2023.

**Quirks.**

- `y1` is the origin (earlier year), `y2` the destination. The inflow file is keyed by destination, the outflow file by origin.
- State codes 96–98 are summary rows (total, US, foreign, non-migrants). Codes 57–59 are rollups of "other" flows and foreign moves.
- `-1` means suppressed. All 5,818 suppressed rows are in the 57–59 rollups. Flows below the IRS disclosure threshold are folded into those rollups, so county-to-county rows are complete but not exhaustive.
- Country-level summary row names say what they are (`Total Migration-US and Foreign`, `Non-migrants`); filter by code, not name.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `y1_statefips`, `y1_countyfips` | VARCHAR(2), VARCHAR(3) | FIPS | Origin county (or summary code). |
| `y2_statefips`, `y2_countyfips` | VARCHAR(2), VARCHAR(3) | FIPS | Destination county (or summary code). |
| `n1` | BIGINT | returns | Number of returns that moved; a proxy for households. |
| `n2` | BIGINT | exemptions | Number of personal exemptions; a proxy for people. |
| `agi` | BIGINT | USD thousands | Adjusted gross income of the movers, in the second year. |

## HUD Fair Market Rents

API `https://www.huduser.gov/hudapi/public/fmr/data/{entityid}?year=YYYY` (one FMR area) and `fmr/statedata/{ST}?year=YYYY` (all counties in a state). Bearer token from `.env`. The HUD website blocks scripted downloads; use the API.

**Quirks.**

- Nashville is a Small Area FMR area (`smallarea_status = 1`): the area call returns 125 ZIPs plus one `MSA level` row. Non-SAFMR areas return one set of values.
- County `fips_code` is 10 characters: 5-digit county FIPS + `99999`. Take the first five.
- FMRs are set at the 40th percentile of gross rent (`FMR Percentile = 40`).
- Fiscal year *Y* starts 1 October of *Y*−1. FY2027 is current.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `zip_code` | VARCHAR | ZIP | ZIP for Small Area FMRs; `MSA level` for the area row. |
| `fips_code` | VARCHAR(10) | county FIPS + `99999` | County key in state data. |
| `year` | INTEGER | fiscal year | FMR fiscal year. |
| `smallarea_status` | VARCHAR | flag | 1 = the area uses ZIP-level FMRs. |
| `Efficiency`–`Four-Bedroom` | INTEGER | USD per month | Fair market gross rent for a 0–4 bedroom unit. |

## HUD-USPS ZIP crosswalk

API `https://www.huduser.gov/hudapi/public/usps?type={2|3}&query=All` (type 2 ZIP to county, 54,570 rows; type 3 ZIP to CBSA, 47,629 rows). 2026 Q2.

**Quirks.**

- 39,484 ZIPs; 11,379 are split across more than one county.
- `res_ratio` sums to 1 per ZIP, except 3,549 ZIPs with no residential addresses (sum 0). These are PO-box or business ZIPs; Phase 3 flags them.
- CBSA `geoid = 99999` means outside any CBSA.
- ZIPs per study CBSA: from 84 (Raleigh) to 388 (Dallas-Fort Worth).

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `zip` | VARCHAR(5) | ZIP | USPS ZIP code. |
| `geoid` | VARCHAR(5) | county FIPS or CBSA | Target geography. |
| `year`, `quarter` | INTEGER | year, quarter | Crosswalk vintage. |
| `res_ratio` | DOUBLE | share 0–1 | Share of the ZIP's residential addresses in this target. Used for allocation. |
| `bus_ratio`, `oth_ratio`, `tot_ratio` | DOUBLE | share 0–1 | Same for business, other and all addresses. |

## Census CBSA delineation (July 2023)

File `list1_2023.xlsx`. Read range `A3:L5000` and keep rows whose `CBSA Code` is five digits; the bottom rows are footnotes. 1,915 counties.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `CBSA Code` | VARCHAR(5) | CBSA | Metro or micro area. |
| `CBSA Title` | VARCHAR | name | Official 2023 title. |
| `Metropolitan/Micropolitan Statistical Area` | VARCHAR | category | Metro or micro. |
| `Metropolitan Division Code` | VARCHAR(5) | division | Set only for counties in metros split into divisions (38 divisions); null for 92.7% of rows. |
| `CSA Code` | VARCHAR(3) | CSA | Combined statistical area; null for 30% of rows. |
| `FIPS State Code`, `FIPS County Code` | VARCHAR(2), VARCHAR(3) | FIPS | County key. |
| `Central/Outlying County` | VARCHAR | category | Whether the county is central to the CBSA. |

## Census cartographic boundaries

Shapefiles from `https://www2.census.gov/geo/tiger/GENZ{year}/shp/`: `cb_2024_us_cbsa_500k` (935), `cb_2024_us_county_500k` (3,235) and `cb_2020_us_zcta520_500k` (33,791; ZCTA shapes are only published for 2020). Read with DuckDB spatial: `st_read('/vsizip/<zip>/<name>.shp')`.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `GEOID` / `GEOID20` | VARCHAR | CBSA, county FIPS or ZCTA | Geography code. |
| `NAME` | VARCHAR | name | Short name. |
| `ALAND`, `AWATER` | BIGINT | square metres | Land and water area. |
| `geom` | GEOMETRY | polygon | Shape (simplified, 1:500,000). |

## Geography backbone

dbt models in `dbt/models/geography/`, built with `.\tasks.ps1 build` into `data/warehouse.duckdb`. They read the Phase 2 samples for now; Phase 6 points them at bronze.

| Model | Grain | Rows | Built from |
| --- | --- | --- | --- |
| `dim_metro` | one row per study metro (`cbsa_code`) | 11 | `config/metros.yml` + delineation |
| `dim_county` | one row per US county (`county_fips`) | 3,235 (1,915 in a CBSA, 96 in study metros) | 2024 county boundaries + delineation |
| `dim_zip` | one row per ZIP in a study metro (`zip`) | 2,140 | HUD ZIP-to-county crosswalk + `dim_county` + 2020 ZCTAs |
| `stg_hud__zip_county` | one row per (ZIP, county) | 54,570 | HUD ZIP-to-county crosswalk |

**Rule for ZIPs split across counties.** Two rules, for two jobs:

- *Membership.* A ZIP belongs to the county with the largest share of its residential addresses (`res_ratio`); total addresses break ties and decide for ZIPs with no residential addresses. Its metro is that county's 2023 CBSA. This gives each ZIP exactly one county and one metro.
- *Allocation.* County-level values (wages, permits, migration) reach ZIPs weighted by `res_ratio` from `stg_hud__zip_county`, so a ZIP split 60/40 gets 60% and 40% of its two counties' values.

Membership goes through the county, not HUD's ZIP-to-CBSA file, so ZIPs, counties and metros form one hierarchy. The two routes disagree on 5 of 39,472 ZIPs, none in a study metro; the test `assert_dim_zip_matches_hud_cbsa` warns if that changes.

**Checks (2026 Q2 crosswalk).**

- Every Zillow ZIP in a study-metro county is in the crosswalk (`assert_zillow_zips_in_crosswalk`), and `dim_zip` is unique on `zip`, so each maps to exactly one metro. 1,438 Zillow ZIPs land in `dim_zip`.
- 21 Zillow ZIPs that Zillow's pre-2023 metro titles place in a study metro fall outside `dim_zip`. 9 are split ZIPs whose main county lies outside the metro (e.g. 30517 and 30548, filed by Zillow under Barrow County, GA, have most residents in Jackson County). The other 12 sit in counties outside the 2023 metro. The 2023 delineation wins.
- ZIP to ZCTA: a ZIP uses the ZCTA with the same code. 588 of the 2,140 `dim_zip` ZIPs have no 2020 ZCTA (122 of them have no residential addresses). Only 1 is a Zillow ZIP (98206), so the gap costs almost no price or rent data.
- `is_po_box_only` marks 178 ZIPs with no residential addresses. They stay in `dim_zip` but carry no prices or rents.

**How each source reaches the target grains (Gate A).**

| Source | Metro-month | ZIP-month |
| --- | --- | --- |
| Zillow ZHVI, ZORI | metro file, `RegionID` = `dim_metro.zillow_region_id` | ZIP file, `RegionName` = `dim_zip.zip` |
| Redfin | `TABLE_ID` in `dim_metro.redfin_table_ids`, monthly rows; split metros need the Phase 5 rule | ZIP parsed from `REGION`, 90-day window keyed on its `PERIOD_END` month (metro-only measures missing) |
| Census BPS | CBSA file, `cbsa_code` | county file, allocated by `res_ratio` |
| ACS 5-year | CBSA geography, carried forward to each month of the release year | ZCTA via `dim_zip.zcta`, carried forward |
| QCEW | `area_fips` = `dim_metro.qcew_area_fips`; monthly employment per month, wages per quarter carried forward | county rows, allocated by `res_ratio` |
| FRED | mortgage and CPI are national (weekly mortgage averaged to months); LAUS series per metro | metro value repeated for each ZIP in the metro |
| IRS SOI migration | counties summed by `dim_county.cbsa_code`, annual, carried forward | county flows allocated by `res_ratio` |
| HUD FMR | FMR area per metro (`MSA level` row), annual | Small Area FMR ZIPs where the area uses them, else the metro value |
| HUD crosswalk, delineation, boundaries | dimensions, not facts | dimensions, not facts |

## Open issues carried forward

| Issue | Phase |
| --- | --- |
| Redfin feed stuck at 2026-06-02; confirm the current location or drop Redfin features to metro grain from another source. | 4 |
| Switch ZORI downloads to the SA files. | 4 |
| Confirm the LAUS series IDs for the ten metros other than Nashville. | 4 |
| Redfin Dallas-Fort Worth and Seattle are split into divisions; pick the metro rule. | 5 |
| Redfin ZIP price outliers (999,999,999) need range tests. | 7 |
