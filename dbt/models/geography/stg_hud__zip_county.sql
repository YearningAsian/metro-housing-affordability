-- One row per (ZIP, county) pair with HUD's address shares. Also the bridge for weighted county-to-ZIP allocation.
with results as (
    select
        data.year::int as crosswalk_year,
        data.quarter::int as crosswalk_quarter,
        -- expands into one column per field, so it takes no alias
        unnest(data.results, recursive := true)  -- noqa: AL03
    from {{ source('samples', 'hud_zip_county') }}
)

select
    zip,
    geoid as county_fips,
    crosswalk_year,
    crosswalk_quarter,
    res_ratio,
    bus_ratio,
    oth_ratio,
    tot_ratio
from results
