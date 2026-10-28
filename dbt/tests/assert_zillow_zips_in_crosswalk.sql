-- Phase 3 done-when: every Zillow ZIP in a study metro maps to exactly one metro. dim_zip is unique on zip, so
-- the remaining failure is a Zillow ZIP in a study-metro county that the HUD crosswalk lacks entirely.
with zillow as (
    select
        regionname as zip,
        state as state_code,
        countyname as county_name
    from {{ source('bronze', 'zillow__zip_zhvi') }}
)

select z.*
from zillow as z
inner join {{ ref('dim_county') }} as c
    on z.state_code = c.state_code and z.county_name = c.county_name and c.is_study_metro
where z.zip not in (select x.zip from {{ ref('stg_hud_crosswalk__zip_county') }} as x)
