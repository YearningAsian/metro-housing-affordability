-- Census cartographic boundary ZCTAs (2020), codes only; geometry stays in bronze for maps.
select geoid20 as zcta
from {{ source('bronze', 'census_geo__zcta_shapes') }}
{{ latest_load() }}
