-- Census cartographic boundary counties (2024), attributes only; geometry stays in bronze for maps.
select
    geoid as county_fips,
    statefp as state_fips,
    stusps as state_code,
    namelsad as county_name
from {{ source('bronze', 'census_geo__county_shapes') }}
{{ latest_load() }}
