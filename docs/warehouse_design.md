# Warehouse design

How the DuckDB warehouse (`data/warehouse.duckdb`) is laid out, what every planned model is called, and which grain and month rules the dbt models in Phase 6 follow. Source facts (keys, units, quirks) live in the [data dictionary](data_dictionary.md).

## Layers

| Schema | Holds | Built by | Materialized |
| --- | --- | --- | --- |
| `bronze` | One view per bronze entity, `bronze.<source>__<entity>`, over every Parquet load in `data/bronze/<source>/<entity>/`. All columns are text plus `_source_file`, `_load_id`, `_loaded_at`, `_file_hash`. | `python -m ingest` (`register_views` runs at the end of every run) | view |
| `silver` | Staging (`stg_`) and intermediate (`int_`) models: typed, cleaned, conformed to month and geography. | dbt | table (staging may be views) |
| `gold` | Dimensions (`dim_`), facts (`fct_`) and marts (`mart_`). The dashboard, models and exports read only from here. | dbt | table |
| `ml` | Feature tables built by dbt and predictions written by the training code. | dbt and Python | table |

`main` keeps `_load_log` (written by ingestion) and, until Phase 6 moves them, the Phase 3 geography models.

The bronze views read absolute paths, so they work from any working directory. After moving the repo, rerun `.\tasks.ps1 ingest` to rebuild them. A bronze view returns every monthly copy of a rolling source (Zillow, Redfin, FRED, HUD crosswalk); staging keeps only the newest `_loaded_at` per entity.

## Naming

| Prefix | Schema | Rule | Example |
| --- | --- | --- | --- |
| `stg_<source>__<entity>` | silver | One per bronze view, same `<source>__<entity>` name. Renames to snake_case, casts types, keeps ZIP and FIPS codes as zero-padded text, dedups to the newest load. No joins. | `stg_redfin__metros` |
| `int_<topic>` | silver | One per topic. Takes facts to the two target grains: applies the month rule, rolls counties up to metros, allocates counties to ZIPs. | `int_supply` |
| `dim_<entity>` | gold | One row per member. | `dim_zip` |
| `fct_<topic>` | gold | One row per geography per native period. Keeps the source's own grain; no carry-forward. | `fct_permits` |
| `mart_<grain>` | gold | Wide, one row per place per month. | `mart_metro_month` |

Columns are snake_case with the unit in the name when it is not obvious (`value_usd`, `sale_to_list_pct`). Booleans start with `is_`. Every month column is called `month`.

## Target grains

- **`metro_month`**: one row per (`cbsa_code`, `month`) for the 11 study metros in `dim_metro`.
- **`zip_month`**: one row per (`zip`, `month`) for every `dim_zip` ZIP with `is_po_box_only = false`.

Both marts run from 2015-01 (the first month every source covers) through the latest month with a Zillow ZHVI value. Facts keep each source's full history.

## Month rule

- `month` is a DATE on the first day of the month. Zillow month-end headers, Redfin `PERIOD BEGIN`, BPS `survey_date` and FRED dates all convert to it.
- Redfin ZIP rows are trailing three-month windows; each window is keyed on its `PERIOD END` month.
- Weekly FRED series (`MORTGAGE30US`) become the mean of the weeks that start in the month.
- A quarterly or annual value applies to every month it covers: QCEW Q1 to January through March, an ACS 5-year vintage ending *Y* to the 12 months of *Y*, an IRS pair (*Y*-1, *Y*) to the 12 months of *Y*, HUD FMR fiscal year *Y* to October *Y*-1 through September *Y*.
- Months after the latest published period repeat the latest value and set `<topic>_is_carried_forward = true` (for example `income_is_carried_forward`). The flag is false wherever the value comes from the month's own period. Each mart also carries the source period (`income_acs_vintage`, `wages_quarter`, `migration_tax_year`) so a reader can see how stale a value is.
- Marts align values to their reference period, not their release date. The Phase 11 features apply the release lags in the data dictionary's point-in-time rule.

## Geography rules

- **Metro**: CBSA code from the July 2023 delineation. County data rolls up through `dim_county.cbsa_code`; additive measures (permits, migration counts) are summed.
- **Redfin Dallas-Fort Worth and Seattle**: Redfin reports these as metro divisions (19124 and 23104; 42644 and 45104). Each pair covers the whole CBSA (Seattle's pre-2023 42644 includes Everett). The metro row sums the counts (homes sold, pending sales, new and active listings, inventory) across both divisions and recomputes months of supply from those sums. Medians and percentages are averaged weighted by homes sold and flagged `is_division_blend = true`. They are an approximation; a true metro median would need transaction data.
- **ZIP**: county counts (permits, migration) are allocated to ZIPs by `stg_hud_crosswalk__zip_county.res_ratio`. County rates and averages (wages, unemployment) are not allocated; a ZIP takes its primary county's value (`dim_zip.county_fips`). ACS values join through `dim_zip.zcta`.

## Star schema

### Dimensions (gold)

| Model | Key | Contents |
| --- | --- | --- |
| `dim_date` | `month` | Every month from 2012-01 through the current month: `year`, `quarter`, `month_of_year`, `quarter_start`. |
| `dim_metro` | `cbsa_code` | The 11 study metros and each source's code for them (built in Phase 3). |
| `dim_county` | `county_fips` | Every US county with its CBSA, metro division and `is_study_metro` (Phase 3). |
| `dim_zip` | `zip` | Study-metro ZIPs with primary county, CBSA and ZCTA (Phase 3). |

### Facts (gold)

`geo_level` is `zip`, `county` or `metro`; `geo_code` is the ZIP, county FIPS or CBSA code; every fact row also carries `cbsa_code`.

| Model | Grain | Measures | Source |
| --- | --- | --- | --- |
| `fct_home_prices` | (`geo_level`, `geo_code`, `month`); zip and metro | `zhvi_usd`, `median_sale_price_usd`, `median_sale_ppsf_usd`, `median_list_price_usd`, `is_division_blend` | Zillow ZHVI, Redfin |
| `fct_rents` | (`geo_level`, `geo_code`, `month`); zip and metro | `zori_usd` | Zillow ZORI |
| `fct_fair_market_rents` | (`fmr_area_code`, `zip`, `fiscal_year`); `zip` null for area-wide FMRs | `fmr_0br_usd` to `fmr_4br_usd`, `is_small_area` | HUD FMR |
| `fct_market_activity` | (`geo_level`, `geo_code`, `month`); zip and metro | `homes_sold`, `pending_sales`, `new_listings`, `active_listings`, `inventory`, `months_of_supply`, `median_days_on_market`, `sale_to_list_pct`, `sold_above_list_pct`, `off_market_in_two_weeks_pct`, `is_division_blend` | Redfin |
| `fct_permits` | (`county_fips`, `month`) | `units_1`, `units_2`, `units_3_4`, `units_5_plus`, `total_units`, `buildings`, `value_usd` | BPS monthly; April 2015 from the year-to-date files |
| `fct_wages` | (`geo_level`, `geo_code`, `month`); county (QCEW `agglvl_code` 70) and metro (40) | `employment` (monthly), `avg_weekly_wage_usd`, `total_quarterly_wages_usd`, `establishments` (quarterly), `quarter` | QCEW, all industries, all ownerships |
| `fct_migration` | (`county_fips`, `tax_year`) | `inflow_returns`, `inflow_people`, `inflow_agi_usd`, `outflow_returns`, `outflow_people`, `outflow_agi_usd`, `net_people` | IRS SOI |
| `fct_income` | (`geo_level`, `geo_code`, `acs_vintage`); zcta, county and metro | `median_household_income_usd`, `population`, `median_gross_rent_usd`, `rent_pct_income` | ACS 5-year |
| `fct_economy` | (`series_id`, `month`); `cbsa_code` null for national series | `value` | FRED: mortgage rate, CPI, metro unemployment rate |

BPS annual files are not a fact; Phase 7 tests that yearly sums of `fct_permits` match them.

### Marts (gold)

`mart_metro_month` and `mart_zip_month` join every intermediate model at their grain and add the derived metrics:

- `price_to_income` = ZHVI / ACS median household income
- `rent_to_wage` = ZORI / (average weekly wage × 52 / 12)
- year-over-year growth for prices, rents, wages and employment
- `permits_per_1000` = trailing 12-month permitted units / population × 1,000
- `net_migration_rate` = net migrants / population × 1,000
- national mortgage rate and CPI on every row; metro unemployment rate

## Every planned model

| Layer | Models |
| --- | --- |
| Staging (silver) | `stg_config__metros`, `stg_zillow__metro_zhvi`, `stg_zillow__zip_zhvi`, `stg_zillow__metro_zori`, `stg_zillow__zip_zori`, `stg_redfin__metros`, `stg_redfin__zips`, `stg_bps__county_monthly`, `stg_bps__county_ytd`, `stg_bps__county_annual`, `stg_acs__zcta`, `stg_acs__county`, `stg_acs__cbsa`, `stg_qcew__industry_10`, `stg_fred__observations`, `stg_irs_migration__inflow`, `stg_irs_migration__outflow`, `stg_hud_fmr__fmr`, `stg_hud_crosswalk__zip_county`, `stg_hud_crosswalk__zip_cbsa`, `stg_census_geo__cbsa_delineation`, `stg_census_geo__county_shapes`, `stg_census_geo__zcta_shapes`, `stg_census_geo__cbsa_shapes` |
| Intermediate (silver) | `int_prices`, `int_rents`, `int_supply`, `int_wages`, `int_migration`, `int_income` |
| Dimensions (gold) | `dim_date`, `dim_metro`, `dim_county`, `dim_zip` |
| Facts (gold) | `fct_home_prices`, `fct_rents`, `fct_fair_market_rents`, `fct_market_activity`, `fct_permits`, `fct_wages`, `fct_migration`, `fct_income`, `fct_economy` |
| Marts (gold) | `mart_metro_month`, `mart_zip_month`, `mart_zip_forecast` (a view over `ml.predictions`, Phase 12) |
| ML | `ml.features_zip_month` (dbt, Phase 11), `ml.predictions` (written by the training code, Phase 12) |

`int_income` is not in the Phase 6 list; price-to-income needs ACS income at both grains, so it gets its own topic. National FRED series join the marts straight from `fct_economy`; the metro unemployment rate goes through `int_wages`.

### Star schema diagram

```mermaid
erDiagram
    dim_metro ||--o{ dim_county : "cbsa_code"
    dim_county ||--o{ dim_zip : "primary county"
    dim_metro ||--o{ fct_home_prices : "cbsa_code"
    dim_zip ||--o{ fct_home_prices : "zip rows"
    dim_date ||--o{ fct_home_prices : "month"
    dim_metro ||--o{ fct_rents : "cbsa_code"
    dim_zip ||--o{ fct_rents : "zip rows"
    dim_date ||--o{ fct_rents : "month"
    dim_metro ||--o{ fct_fair_market_rents : "cbsa_code"
    dim_zip ||--o{ fct_fair_market_rents : "small-area rows"
    dim_metro ||--o{ fct_market_activity : "cbsa_code"
    dim_zip ||--o{ fct_market_activity : "zip rows"
    dim_date ||--o{ fct_market_activity : "month"
    dim_county ||--o{ fct_permits : "county_fips"
    dim_date ||--o{ fct_permits : "month"
    dim_county ||--o{ fct_wages : "county rows"
    dim_metro ||--o{ fct_wages : "cbsa_code"
    dim_date ||--o{ fct_wages : "month"
    dim_county ||--o{ fct_migration : "county_fips"
    dim_metro ||--o{ fct_income : "cbsa_code"
    dim_county ||--o{ fct_income : "county rows"
    dim_zip ||--o{ fct_income : "zcta rows"
    dim_date ||--o{ fct_economy : "month"
    dim_metro ||--o{ fct_economy : "metro series"
    dim_metro ||--o{ mart_metro_month : "cbsa_code"
    dim_date ||--o{ mart_metro_month : "month"
    dim_zip ||--o{ mart_zip_month : "zip"
    dim_date ||--o{ mart_zip_month : "month"

    dim_date {
        date month PK
    }
    dim_metro {
        varchar cbsa_code PK
    }
    dim_county {
        varchar county_fips PK
    }
    dim_zip {
        varchar zip PK
    }
    fct_home_prices {
        varchar geo_level PK
        varchar geo_code PK
        date month PK
    }
    fct_rents {
        varchar geo_level PK
        varchar geo_code PK
        date month PK
    }
    fct_fair_market_rents {
        varchar fmr_area_code PK
        varchar zip PK
        int fiscal_year PK
    }
    fct_market_activity {
        varchar geo_level PK
        varchar geo_code PK
        date month PK
    }
    fct_permits {
        varchar county_fips PK
        date month PK
    }
    fct_wages {
        varchar geo_level PK
        varchar geo_code PK
        date month PK
    }
    fct_migration {
        varchar county_fips PK
        int tax_year PK
    }
    fct_income {
        varchar geo_level PK
        varchar geo_code PK
        int acs_vintage PK
    }
    fct_economy {
        varchar series_id PK
        date month PK
    }
    mart_metro_month {
        varchar cbsa_code PK
        date month PK
    }
    mart_zip_month {
        varchar zip PK
        date month PK
    }
```

### Lineage diagram

```mermaid
flowchart LR
    subgraph bronze
        b_zillow[zillow: metro/zip zhvi, zori]
        b_redfin[redfin: metros, zips]
        b_bps[bps: county monthly, ytd, annual]
        b_acs[acs: zcta, county, cbsa]
        b_qcew[qcew: industry_10]
        b_fred[fred: observations]
        b_irs[irs_migration: inflow, outflow]
        b_fmr[hud_fmr: fmr]
        b_xwalk[hud_crosswalk: zip_county, zip_cbsa]
        b_geo[census_geo: delineation, shapes]
        config[config/metros.yml]
    end
    subgraph staging [silver: staging]
        s_zillow[stg_zillow__*]
        s_redfin[stg_redfin__*]
        s_bps[stg_bps__*]
        s_acs[stg_acs__*]
        s_qcew[stg_qcew__industry_10]
        s_fred[stg_fred__observations]
        s_irs[stg_irs_migration__*]
        s_fmr[stg_hud_fmr__fmr]
        s_xwalk[stg_hud_crosswalk__*]
        s_geo[stg_census_geo__*]
        s_config[stg_config__metros]
    end
    subgraph dims [gold: dimensions]
        dim_date
        dim_metro
        dim_county
        dim_zip
    end
    subgraph facts [gold: facts]
        fct_home_prices
        fct_rents
        fct_fair_market_rents
        fct_market_activity
        fct_permits
        fct_wages
        fct_migration
        fct_income
        fct_economy
    end
    subgraph intermediate [silver: intermediate]
        int_prices
        int_rents
        int_supply
        int_wages
        int_migration
        int_income
    end
    subgraph marts [gold: marts]
        mart_metro_month
        mart_zip_month
        mart_zip_forecast
    end
    subgraph ml
        features[ml.features_zip_month]
        predictions[ml.predictions]
    end

    b_zillow --> s_zillow
    b_redfin --> s_redfin
    b_bps --> s_bps
    b_acs --> s_acs
    b_qcew --> s_qcew
    b_fred --> s_fred
    b_irs --> s_irs
    b_fmr --> s_fmr
    b_xwalk --> s_xwalk
    b_geo --> s_geo
    config --> s_config

    s_config --> dim_metro
    s_geo --> dim_county
    s_geo --> dim_metro
    s_xwalk --> dim_zip
    s_geo --> dim_zip

    s_zillow --> fct_home_prices
    s_redfin --> fct_home_prices
    s_zillow --> fct_rents
    s_fmr --> fct_fair_market_rents
    s_redfin --> fct_market_activity
    s_bps --> fct_permits
    s_qcew --> fct_wages
    s_irs --> fct_migration
    s_acs --> fct_income
    s_fred --> fct_economy

    fct_home_prices --> int_prices
    fct_rents --> int_rents
    fct_fair_market_rents --> int_rents
    fct_market_activity --> int_supply
    fct_permits --> int_supply
    fct_wages --> int_wages
    fct_economy --> int_wages
    fct_migration --> int_migration
    fct_income --> int_income
    s_xwalk --> int_supply
    s_xwalk --> int_migration

    int_prices --> mart_metro_month
    int_rents --> mart_metro_month
    int_supply --> mart_metro_month
    int_wages --> mart_metro_month
    int_migration --> mart_metro_month
    int_income --> mart_metro_month
    fct_economy --> mart_metro_month
    dim_date --> mart_metro_month
    int_prices --> mart_zip_month
    int_rents --> mart_zip_month
    int_supply --> mart_zip_month
    int_wages --> mart_zip_month
    int_migration --> mart_zip_month
    int_income --> mart_zip_month
    fct_economy --> mart_zip_month
    dim_date --> mart_zip_month
    dim_zip --> mart_zip_month

    mart_zip_month --> features
    features --> predictions
    predictions --> mart_zip_forecast
```

## Moving to this layout (Phase 6)

- Add a `generate_schema_name` macro that uses the configured schema as is (dbt's default would build `main_silver`), and set `+schema` per model folder: `models/staging` and `models/intermediate` to silver, `models/marts` (dims, facts, marts) to gold, `models/ml` to ml.
- Move the Phase 3 geography models into those folders, rename `stg_hud__zip_county` to `stg_hud_crosswalk__zip_county`, and point their sources at the bronze views instead of `data/samples/`. Then drop the old copies in `main`, and `notebooks/download_samples.py` can go.
- Redfin's monthly files replace the weekly roll-up planned in Phase 6. The feed is NSA only, so the "never mix SA and NSA" rule holds automatically.
