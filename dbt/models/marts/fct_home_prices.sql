-- Zillow ZHVI (typical home value) for the study metros and their ZIPs, one row per place and month.
with zhvi as (
    select * from {{ ref('stg_zillow__indexes') }}
    where measure = 'zhvi'
)

select
    'metro' as geo_level,
    m.cbsa_code as geo_code,
    m.cbsa_code,
    z.month,
    z.value as zhvi_usd
from zhvi as z
inner join {{ ref('dim_metro') }} as m on z.geo_level = 'metro' and z.region_id = m.zillow_region_id
union all
select
    'zip' as geo_level,
    d.zip as geo_code,
    d.cbsa_code,
    z.month,
    z.value as zhvi_usd
from zhvi as z
inner join {{ ref('dim_zip') }} as d on z.geo_level = 'zip' and z.zip = d.zip
