-- ACS 5-year estimates by ZCTA, county and CBSA, one row per place and vintage. The Census API writes negative
-- sentinels (e.g. -666666666) for estimates it cannot publish; those become null.
with unioned as (
    select
        'zcta' as geo_level,
        "zip code tabulation area" as geo_code,  -- noqa: RF05
        *
    from {{ source('bronze', 'acs__zcta') }}
    {{ latest_load() }}
    union all by name
    select
        'county' as geo_level,
        state || county as geo_code,
        *
    from {{ source('bronze', 'acs__county') }}
    {{ latest_load() }}
    union all by name
    select
        'metro' as geo_level,
        "metropolitan statistical area/micropolitan statistical area" as geo_code,  -- noqa: RF05
        *
    from {{ source('bronze', 'acs__cbsa') }}
    {{ latest_load() }}
)

select
    geo_level,
    geo_code,
    vintage::int as acs_vintage,
    case when b19013_001e::double >= 0 then b19013_001e::double end as median_household_income_usd,
    case when b01003_001e::double >= 0 then b01003_001e::double end as population,
    case when b25064_001e::double >= 0 then b25064_001e::double end as median_gross_rent_usd,
    case when b25071_001e::double >= 0 then b25071_001e::double end as rent_pct_income
from unioned
