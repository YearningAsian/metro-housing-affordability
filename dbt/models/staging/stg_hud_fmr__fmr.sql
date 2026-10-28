-- HUD Fair Market Rents, one row per FMR area and fiscal year, plus one row per ZIP for Small Area FMR areas
-- (whose area-wide row says 'MSA level' in zip_code).
-- noqa: disable=RF05
-- HUD's bedroom column names contain hyphens
select
    fmr_area_code,
    -- METRO + CBSA code + area suffix
    substr(fmr_area_code, 6, 5) as cbsa_code,
    area_name,
    case when regexp_full_match(zip_code, '\d{5}') then zip_code end as zip,
    year::int as fiscal_year,
    coalesce(smallarea_status = '1', false) as is_small_area,
    efficiency::int as fmr_0br_usd,
    "One-Bedroom"::int as fmr_1br_usd,
    "Two-Bedroom"::int as fmr_2br_usd,
    "Three-Bedroom"::int as fmr_3br_usd,
    "Four-Bedroom"::int as fmr_4br_usd
from {{ source('bronze', 'hud_fmr__fmr') }}
{{ latest_load() }}
-- noqa: enable=RF05
