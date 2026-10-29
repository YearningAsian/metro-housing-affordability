-- No wage or employment growth where QCEW's latest quarter is carried forward: that value against a real one a year
-- earlier is not growth (it made Seattle's April-June 2026 wage growth read 8.4% instead of 2.6%).
select
    'metro' as geo_level,
    m.cbsa_code as geo_code,
    m.month
from {{ ref('mart_metro_month') }} as m
where m.wages_is_carried_forward and (m.avg_weekly_wage_yoy_growth is not null or m.employment_yoy_growth is not null)
union all
select
    'zip' as geo_level,
    z.zip as geo_code,
    z.month
from {{ ref('mart_zip_month') }} as z
where z.wages_is_carried_forward and z.avg_weekly_wage_yoy_growth is not null
