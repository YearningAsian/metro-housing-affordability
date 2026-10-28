-- One row per (ZIP, county) pair with HUD's address shares. Also the bridge for weighted county-to-ZIP allocation.
select
    zip,
    geoid as county_fips,
    year::int as crosswalk_year,
    quarter::int as crosswalk_quarter,
    res_ratio::double as res_ratio,
    bus_ratio::double as bus_ratio,
    oth_ratio::double as oth_ratio,
    tot_ratio::double as tot_ratio
from {{ source('bronze', 'hud_crosswalk__zip_county') }}
{{ latest_load() }}
