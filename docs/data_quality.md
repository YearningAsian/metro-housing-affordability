# Data quality

Every dbt test in the project and the reason it exists. `.\tasks.ps1 build` runs them all (`dbt build`), and `dbt source freshness` checks the load dates. Tests fail the build unless marked **warn**.

Generic tests live next to the model descriptions in `dbt/models/*/_*.yml`; singular tests are the SQL files in `dbt/tests/`. Range tests use [dbt-expectations](https://github.com/metaplane/dbt-expectations) (`expect_column_values_to_be_between`), pinned in `dbt/packages.yml`.

## Keys

| Model | Test | Reason |
| --- | --- | --- |
| `stg_config__metros`, `dim_metro` | `unique`, `not_null` on `cbsa_code` | One row per study metro; every join to a metro goes through this key. |
| `dim_metro` | `unique`, `not_null` on `zillow_region_id` and `fred_unemployment_series`; `not_null` on `cbsa_title` | Each metro maps to exactly one Zillow region and one FRED series, or its prices or unemployment would double or vanish. |
| `stg_census_geo__cbsa_delineation`, `dim_county` | `unique`, `not_null` on `county_fips` | A county belongs to one metro. |
| `stg_hud_crosswalk__zip_county` | `unique` on (`zip`, `county_fips`); `not_null` on both | The crosswalk is many-to-many, but each pair appears once. |
| `dim_zip` | `unique`, `not_null` on `zip`; `not_null` on `cbsa_code`, `county_fips` | Each ZIP has one main county and one metro. |
| `dim_date` | `unique`, `not_null` on `month` | The calendar spine. |
| Every fact (`fct_*`) | `unique` on its grain (see [warehouse design](warehouse_design.md)); `not_null` on each grain column and `cbsa_code` | Facts are joined one-to-one onto the spine; a duplicate key would double-count. |
| Every intermediate (`int_*`) | `unique` on (`geo_level`, `geo_code`, `month`) or its own grain; `not_null` on the `int_spine` keys | Same, one level up. |
| `mart_metro_month` | `unique` on (`cbsa_code`, `month`); `not_null` on both | Phase 6 done-when: one row per key. |
| `mart_zip_month` | `unique` on (`zip`, `month`); `not_null` on `zip`, `month`, `cbsa_code` | Same. |
| `features_zip_month` | `unique` on (`zip`, `month`); `not_null` on `zip`, `month`, `cbsa_code`, `prediction_date`, `split`; `accepted_values` on `split` | One training row per key, and every row in exactly one split. |

## Relationships and accepted values

| Model | Test | Reason |
| --- | --- | --- |
| `dim_zip`, every fact with a `cbsa_code`, both marts | `relationships` from `cbsa_code` to `dim_metro` | No row belongs to a metro outside the study set. |
| `dim_zip`, `fct_permits`, `fct_migration` | `relationships` from `county_fips` to `dim_county` | County data only enters for study counties. |
| `fct_home_prices`, `fct_rents`, `fct_market_activity`, `fct_wages`, `fct_income` | `relationships` from `geo_code` to `dim_zip.zip` where `geo_level = 'zip'`, and to `dim_county.county_fips` where `geo_level = 'county'` | The polymorphic `geo_code` points at a real ZIP or county for its level. |
| `mart_zip_month` | `relationships` from `zip` to `dim_zip` | Every mart ZIP is a known study ZIP. |
| The same five facts | `accepted_values` on `geo_level`: `metro`, `county`, `zip` | A new level would silently skip the relationship tests above. |
| `dim_metro` | `accepted_values` on `cbsa_code`: the 11 codes in `config/metros.yml` | Catches a metro added to or dropped from the config by mistake. The list duplicates the config on purpose, so update both together. |
| `dim_metro` | `accepted_values` on `is_metropolitan`: `true` | The study covers metropolitan, not micropolitan, areas. |

## Ranges

Bounds are wide on purpose: they catch unit mistakes, sign errors and broken joins, not unusual markets. Each applies to the fact column and to the same column in both marts. Observed values are through September 2026.

| Column | Bounds | Reason |
| --- | --- | --- |
| `zhvi_usd`, `zori_usd`, `median_sale_price_usd`, `median_list_price_usd`, `fmr_2br_usd` | > 0 | A price of zero or below is a parsing or join error. No upper bound: some small ZIPs have real medians above 10 million USD (see the [data dictionary](data_dictionary.md)). |
| `sale_to_list_pct` | 50 to 200 | Homes rarely sell below half or above double the asking price; outside that, the value is a ratio stored as a fraction or a bad record. Observed: 96 to 108 for metros, 50 to 165 for ZIPs (the ZIP minimum sits on the bound). |
| `sold_above_list_pct`, `off_market_in_two_weeks_pct` | 0 to 100 | Shares of homes. |
| `zhvi_yoy_growth`, `zori_yoy_growth`, `avg_weekly_wage_yoy_growth`, `employment_yoy_growth` | −0.5 to 1 | A metro or ZIP losing half or doubling in a year points to a broken series, not a market. Stored as fractions. |
| `unemployment_rate_pct` | 0 to 30 | A rate, in percent. The highest observed is 21.7%. |
| `permits_per_1000` | 0 to 100 | Trailing 12-month units per 1,000 residents. Observed: up to 22.5 for metros, 33.3 for ZIPs. |
| `net_migration_rate` | −100 to 100 | Net migrants per 1,000 residents; a tenth of the population moving in a year is already extreme. Observed: −18 to 15 for metros, −50 to 75 for ZIPs. |
| `price_to_income` | 0.5 to 50 | ZHVI over median household income. Observed: 3.0 to 7.1 for metros, 0.8 to 23.2 for ZIPs. |
| `rent_to_wage` | 0.05 to 2 | Monthly ZORI over monthly average wage. Observed: 0.19 to 0.38 for metros, 0.09 to 0.89 for ZIPs. |

**Cleaning found by these tests.** Redfin reports negative `off_market_in_two_weeks_pct` in 333 metro rows (2012 to April 2020; 8 in study metros, all before 2015) and negative `sold_above_list_pct` in 6. A share cannot be negative, so `stg_redfin__market_tracker` sets negative values in both columns to null.

## Coverage and reconciliation (singular tests)

| Test | Rule | Reason and observed values |
| --- | --- | --- |
| `assert_metro_month_coverage` | Fails for a month in `mart_metro_month` where fewer metros have ZHVI or ZORI than `dim_metro` has rows. | The mart is a spine, so rows always exist; a gap means a Zillow file came in short or a region id stopped matching. |
| `assert_zip_count_stable` | Fails when the number of ZIPs with ZHVI or ZORI drops more than 5% from the previous month. | Catches a truncated ZIP file or a broken ZIP join. The worst drop through September 2026 is 0.4%. |
| `assert_zillow_metro_matches_zip_rollup` | Fails when the population-weighted mean of a metro's ZIP ZHVIs differs from Zillow's metro ZHVI by more than 20%. | The two are not the same measure (Zillow weights every home; a population-weighted mean of ZIP values runs high), so the tolerance is loose. Through September 2026 the roll-up is 0.2% to 12.9% above the metro value, never below. A gap past 20% means the metro file, the ZIP file or the ZIP-to-metro mapping went wrong. |
| `assert_permits_match_annual` (**warn**) | Warns when a metro-year sum of `fct_permits` differs from the BPS annual files by more than 15%. | Monthly files are never revised and the annual files add late reports, so monthly sums run a little low (−12.8% to +10.3%). One known source gap: Nashville (34980) 2022 is 36% low, because Davidson County's monthly reports sum to 5,525 units against 15,285 in the annual file. A warning, because the gap is in the source. |
| `assert_no_growth_on_carried_wages` | Fails for a mart row where `wages_is_carried_forward` is true and wage or employment growth is not null. | QCEW lags about six months, so its latest quarter repeats into later months; dividing that by a real value a year earlier made Seattle's April–June 2026 wage growth read 8.4% against a true 2.6%. |
| `assert_features_point_in_time` | Fails for a `features_zip_month` row where any `*_available_on` date is after `prediction_date`. | Phase 11 done-when. A feature built from data published after the prediction leaks the future, and the backtests would look better than the live model. Shifting every prediction date back one month makes all 184,077 rows fail, so the test bites. |
| `assert_zillow_zips_in_crosswalk` | Fails for a Zillow ZIP in a study-metro county that the HUD ZIP-to-county crosswalk lacks. | Phase 3 done-when: every Zillow ZIP maps to exactly one metro. |
| `assert_dim_zip_matches_hud_cbsa` (**warn**) | Warns where the metro `dim_zip` derives from the ZIP's main county differs from HUD's ZIP-to-CBSA file. | The two crosswalks or the delineation drifted apart. |

## Source freshness

`dbt source freshness` compares each bronze table's latest `_loaded_at` with now. The monthly CI run checks it last, after saving the state, so a source that stopped updating fails the run and sends the failure email. An unchanged download adds no bronze copy, so `_loaded_at` only moves when the content changes.

| Sources | Warn after | Fail after | Reason |
| --- | --- | --- | --- |
| Zillow (4 tables) | 45 days | 75 days | Zillow publishes mid-month and ingest runs monthly, so a load older than 45 days means a missed run. |
| Redfin, BPS monthly, FRED | 35 days | 65 days | Monthly sources: one load is expected every month. |
| QCEW, HUD crosswalk | 100 days | 200 days | Quarterly. The crosswalk is fetched monthly, but HUD changes it once a quarter. |
| ACS, IRS migration, HUD FMR, BPS annual | 400 days | none | Yearly releases; a late release is a warning, never a failure. |
| BPS year-to-date, Census delineation and shapes | none | none | Loaded once; they do not change. |

## Proof that the tests bite

`tests/test_dbt_quality.py` (run by `uv run pytest`) builds a tiny DuckDB with `gold.dim_metro` and `gold.mart_metro_month`, points dbt at it through the `DUCKDB_PATH` variable in `dbt/profiles.yml`, and runs `assert_metro_month_coverage`. A complete fixture passes; the same fixture with one metro's ZHVI missing for one month fails.
