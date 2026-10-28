-- IRS county migration totals (US and foreign) for the study counties, one row per county and tax year.
with totals as (
    select
        f.county_fips,
        c.cbsa_code,
        f.tax_year,
        f.direction,
        f.returns,
        f.people,
        f.agi_usd
    from {{ ref('stg_irs_migration__flows') }} as f
    inner join {{ ref('dim_county') }} as c on f.county_fips = c.county_fips and c.is_study_metro
    where f.other_state_fips = '96'
)

select
    county_fips,
    cbsa_code,
    tax_year,
    {% for m in ['returns', 'people', 'agi_usd'] %}
        any_value({{ m }}) filter (where direction = 'inflow') as inflow_{{ m }},
        any_value({{ m }}) filter (where direction = 'outflow') as outflow_{{ m }},
    {% endfor %}
    inflow_people - outflow_people as net_people
from totals
group by county_fips, cbsa_code, tax_year
