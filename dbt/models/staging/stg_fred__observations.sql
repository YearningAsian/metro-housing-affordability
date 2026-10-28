-- FRED observations, one row per series and date. FRED writes '.' for missing values.
select
    series_id,
    "date"::date as observation_date,  -- noqa: RF06
    nullif(value, '.')::double as value
from {{ source('bronze', 'fred__observations') }}
{{ latest_load() }}
