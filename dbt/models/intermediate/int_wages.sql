-- Labor market per place and month: QCEW employment and average weekly wage, and the BLS unemployment rate.
-- QCEW lags about six months, so its latest quarter carries forward. A ZIP gets the average of its counties' weekly
-- wages weighted by res_ratio, no employment count, and its metro's unemployment rate.
with places as (
    select
        geo_level,
        geo_code,
        month,
        quarter,
        employment,
        avg_weekly_wage_usd
    from {{ ref('fct_wages') }}
    where geo_level = 'metro'
    union all by name
    select
        'zip' as geo_level,
        x.zip as geo_code,
        w.month,
        any_value(w.quarter) as quarter,
        {{ weighted_avg('w.avg_weekly_wage_usd', 'x.res_ratio') }} as avg_weekly_wage_usd
    from {{ ref('stg_hud_crosswalk__zip_county') }} as x
    inner join {{ ref('fct_wages') }} as w on w.geo_level = 'county' and x.county_fips = w.geo_code
    group by x.zip, w.month
)

select
    s.geo_level,
    s.geo_code,
    s.month,
    w.employment,
    w.avg_weekly_wage_usd,
    w.quarter as wages_quarter,
    w.month < s.month as wages_is_carried_forward,
    e.value as unemployment_rate_pct
from {{ ref('int_spine') }} as s
asof left join places as w
    on s.geo_level = w.geo_level and s.geo_code = w.geo_code and s.month >= w.month
left join {{ ref('fct_economy') }} as e
    on s.cbsa_code = e.cbsa_code and s.month = e.month
