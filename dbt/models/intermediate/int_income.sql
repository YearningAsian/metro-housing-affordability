-- ACS income, population and rent per place and month. A vintage is pinned to January of its year, and months between
-- two vintages move in a straight line from one to the next, so the yearly release does not step every January; a
-- missing vintage (the 1-year 2020) is bridged the same way. After the latest vintage the value carries forward.
-- ZIPs use the ZCTA with the same code (null when there is none).
with vintages as (
    select
        geo_level,
        geo_code,
        acs_survey,
        acs_vintage,
        make_date(acs_vintage, 1, 1) as vintage_start,
        lead(make_date(acs_vintage, 1, 1)) over w as next_start,
        median_household_income_usd,
        population,
        median_gross_rent_usd,
        rent_pct_income,
        median_real_estate_taxes_usd / median_home_value_usd as property_tax_rate,
        lead(median_real_estate_taxes_usd / median_home_value_usd) over w as next_tax_rate,
        lead(median_household_income_usd) over w as next_income,
        lead(population) over w as next_population,
        lead(median_gross_rent_usd) over w as next_rent,
        lead(rent_pct_income) over w as next_rent_pct
    from {{ ref('fct_income') }}
    where geo_level in ('metro', 'zip')
    window w as (partition by geo_level, geo_code order by acs_vintage)
),

placed as (
    select
        s.geo_level,
        s.geo_code,
        s.month,
        v.* exclude (geo_level, geo_code),  -- noqa: RF02
        datediff('month', v.vintage_start, s.month) / datediff('month', v.vintage_start, v.next_start) as frac
    from {{ ref('int_spine') }} as s
    asof left join vintages as v
        on s.geo_level = v.geo_level and s.geo_code = v.geo_code and s.month >= v.vintage_start
)

select
    geo_level,
    geo_code,
    month,
    -- a null next value (latest vintage, or a suppressed estimate) keeps the vintage's own value
    coalesce(
        median_household_income_usd + (next_income - median_household_income_usd) * frac, median_household_income_usd
    ) as median_household_income_usd,
    coalesce(population + (next_population - population) * frac, population) as population,
    coalesce(median_gross_rent_usd + (next_rent - median_gross_rent_usd) * frac, median_gross_rent_usd)
        as median_gross_rent_usd,
    coalesce(rent_pct_income + (next_rent_pct - rent_pct_income) * frac, rent_pct_income) as rent_pct_income,
    coalesce(property_tax_rate + (next_tax_rate - property_tax_rate) * frac, property_tax_rate) as property_tax_rate,
    acs_survey as income_acs_survey,
    acs_vintage as income_acs_vintage,
    next_start is null and year(month) > acs_vintage as income_is_carried_forward
from placed
