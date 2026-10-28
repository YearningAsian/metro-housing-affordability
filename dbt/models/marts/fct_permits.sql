-- Building permits per study county and month, filling two gaps in the monthly files:
-- April 2015 has no monthly file, so it is the April year-to-date file minus the March one.
-- Before 2022 the monthly files cover only a sample of counties (19 study counties are missing), so a county-year
-- without monthly rows gets its annual total spread evenly over the 12 months (is_estimated).
-- shortcut: a county with only some months in a year keeps its gaps; spread the rest of the annual total if it matters
{% set units = ['units_1', 'units_2', 'units_3_4', 'units_5_plus'] %}
with permits as (
    select
        p.*,
        c.cbsa_code
    from {{ ref('stg_bps__permits') }} as p
    inner join {{ ref('dim_county') }} as c on p.county_fips = c.county_fips and c.is_study_metro
),

monthly as (
    select
        county_fips,
        cbsa_code,
        period_start as month,
        {% for u in units %}
            {{ u }},
        {% endfor %}
        false as is_estimated
    from permits
    where file_type = 'monthly'
),

april_2015 as (
    select
        a.county_fips,
        a.cbsa_code,
        a.period_start as month,
        {% for u in units %}
            a.{{ u }} - m.{{ u }} as {{ u }},
        {% endfor %}
        false as is_estimated
    from permits as a
    inner join permits as m on a.county_fips = m.county_fips and m.file_type = 'ytd' and m.survey_date = '201503'
    where a.file_type = 'ytd' and a.survey_date = '201504'
),

spread as (
    select
        y.county_fips,
        y.cbsa_code,
        (y.period_start + to_months(r.i))::date as month,
        {% for u in units %}
            y.{{ u }} / 12 as {{ u }},
        {% endfor %}
        true as is_estimated
    from permits as y
    cross join range(12) as r (i)
    where
        y.file_type = 'annual'
        and not exists (
            select 1 from monthly as mo
            where mo.county_fips = y.county_fips and year(mo.month) = year(y.period_start)
        )
),

unioned as (
    select * from monthly
    union all by name
    select * from april_2015
    union all by name
    select * from spread
)

select
    *,
    units_1 + units_2 + units_3_4 + units_5_plus as total_units
from unioned
