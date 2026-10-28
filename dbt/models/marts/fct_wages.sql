-- QCEW all-industry, all-ownership employment and wages for the study metros and counties, one row per place and
-- month. Employment is monthly; establishments and wages are quarterly and repeat in each month of the quarter.
with quarters as (
    select
        'county' as geo_level,
        c.county_fips as geo_code,
        c.cbsa_code,
        q.*
    from {{ ref('stg_qcew__industry_10') }} as q
    inner join {{ ref('dim_county') }} as c on q.area_fips = c.county_fips and c.is_study_metro
    where q.agglvl_code = '70' and q.own_code = '0'
    union all
    select
        'metro' as geo_level,
        m.cbsa_code as geo_code,
        m.cbsa_code,
        q.*
    from {{ ref('stg_qcew__industry_10') }} as q
    inner join {{ ref('dim_metro') }} as m on q.area_fips = m.qcew_area_fips
    where q.agglvl_code = '40' and q.own_code = '0'
)

select
    q.geo_level,
    q.geo_code,
    q.cbsa_code,
    (q.quarter_start + to_months(r.i))::date as month,
    q.year || 'Q' || q.quarter_of_year as quarter,
    [q.employment_month_1, q.employment_month_2, q.employment_month_3][r.i + 1] as employment,
    q.establishments,
    q.total_wages_usd,
    q.avg_weekly_wage_usd,
    q.disclosure_code
from quarters as q
cross join range(3) as r (i)
