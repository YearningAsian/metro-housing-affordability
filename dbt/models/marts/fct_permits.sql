-- Building permits per study county and month, filling two gaps in the monthly files:
-- April 2015 has no monthly file, so it is the April year-to-date file minus the March one.
-- Before 2022 the monthly files cover only a sample of counties (19 study counties are missing), so a county-year
-- without monthly rows gets its annual total spread evenly over the 12 months (is_estimated).
-- Monthly files are never revised, and the annual files add late reports (Davidson County's 2022 monthly reports sum
-- to 5,525 units against 15,285), so in a year with an annual file each county's months are scaled to sum to its
-- annual total, unit type by unit type (annual_scale). The current year, with no annual file yet, stays as reported;
-- reported_total_units keeps the pre-scaling sum for point-in-time use.
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
),

annual as (
    select
        county_fips,
        year(period_start) as permit_year,
        {% for u in units %}
            {{ u }},
        {% endfor %}
        units_1 + units_2 + units_3_4 + units_5_plus as total_units
    from permits
    where file_type = 'annual'
),

scaled as (
    select
        u.county_fips,
        u.cbsa_code,
        u.month,
        u.is_estimated,
        u.units_1 + u.units_2 + u.units_3_4 + u.units_5_plus as reported_total_units,
        {% for x in units %}
            -- a unit type with no monthly units but an annual total keeps its zeros
            case
                when a.county_fips is not null and sum(u.{{ x }}) over cy > 0
                    then u.{{ x }} * a.{{ x }} / sum(u.{{ x }}) over cy
                else u.{{ x }}
            end as {{ x }},
        {% endfor %}
        a.total_units / nullif(sum(u.units_1 + u.units_2 + u.units_3_4 + u.units_5_plus) over cy, 0) as annual_scale
    from unioned as u
    left join annual as a on u.county_fips = a.county_fips and year(u.month) = a.permit_year
    window cy as (partition by u.county_fips, year(u.month))
)

select
    *,
    units_1 + units_2 + units_3_4 + units_5_plus as total_units
from scaled
