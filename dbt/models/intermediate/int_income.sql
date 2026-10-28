-- ACS income, population and rent per place and month. A 5-year vintage applies from January of its year; the latest
-- carries forward. ZIPs use the ZCTA with the same code (null when there is none).
with vintages as (
    select
        *,
        make_date(acs_vintage, 1, 1) as vintage_start
    from {{ ref('fct_income') }}
    where geo_level in ('metro', 'zip')
)

select
    s.geo_level,
    s.geo_code,
    s.month,
    v.median_household_income_usd,
    v.population,
    v.median_gross_rent_usd,
    v.rent_pct_income,
    v.acs_vintage as income_acs_vintage,
    year(s.month) > v.acs_vintage as income_is_carried_forward
from {{ ref('int_spine') }} as s
asof left join vintages as v
    on s.geo_level = v.geo_level and s.geo_code = v.geo_code and s.month >= v.vintage_start
