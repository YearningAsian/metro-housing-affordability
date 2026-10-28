-- Zillow ZHVI and ZORI for metros and ZIPs, one row per region, measure and month (Zillow dates each month by its
-- last day).
with wide as (
    select
        'metro' as geo_level,
        'zhvi' as measure,
        *
    from {{ source('bronze', 'zillow__metro_zhvi') }}
    {{ latest_load() }}
    union all by name
    select
        'zip' as geo_level,
        'zhvi' as measure,
        *
    from {{ source('bronze', 'zillow__zip_zhvi') }}
    {{ latest_load() }}
    union all by name
    select
        'metro' as geo_level,
        'zori' as measure,
        *
    from {{ source('bronze', 'zillow__metro_zori') }}
    {{ latest_load() }}
    union all by name
    select
        'zip' as geo_level,
        'zori' as measure,
        *
    from {{ source('bronze', 'zillow__zip_zori') }}
    {{ latest_load() }}
),

-- one row per month column; unpivot drops the empty cells
long as (
    unpivot wide on columns('^\d{4}-\d{2}-\d{2}$') into name month_end value value_text
)

select
    geo_level,
    measure,
    regionid::bigint as region_id,
    case when geo_level = 'zip' then regionname end as zip,
    date_trunc('month', month_end::date)::date as month,
    value_text::double as value
from long
