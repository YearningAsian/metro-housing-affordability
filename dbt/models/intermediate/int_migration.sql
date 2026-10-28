-- Net migration per place and month from the IRS county flows: net people moving in per 1,000 residents (ACS
-- population). A tax year's value applies to its calendar year; the latest carries forward. A metro sums its
-- counties; a ZIP gets the average of its counties' rates weighted by res_ratio.
with county_population as (
    select
        geo_code as county_fips,
        acs_vintage,
        population
    from {{ ref('fct_income') }}
    where geo_level = 'county'
),

county_rates as (
    select
        m.county_fips,
        m.cbsa_code,
        m.tax_year,
        m.net_people,
        p.population,
        m.net_people / p.population * 1000 as net_migration_rate
    from {{ ref('fct_migration') }} as m
    asof left join county_population as p
        on m.county_fips = p.county_fips and m.tax_year >= p.acs_vintage
),

places as (
    select
        'metro' as geo_level,
        cbsa_code as geo_code,
        tax_year,
        sum(net_people) as net_migration_people,
        sum(net_people) / sum(population) * 1000 as net_migration_rate
    from county_rates
    group by cbsa_code, tax_year
    union all by name
    select
        'zip' as geo_level,
        x.zip as geo_code,
        c.tax_year,
        {{ weighted_avg('c.net_migration_rate', 'x.res_ratio') }} as net_migration_rate
    from {{ ref('stg_hud_crosswalk__zip_county') }} as x
    inner join county_rates as c on x.county_fips = c.county_fips
    group by x.zip, c.tax_year
),

dated as (
    select
        *,
        make_date(tax_year, 1, 1) as year_start
    from places
)

select
    s.geo_level,
    s.geo_code,
    s.month,
    d.net_migration_people,
    d.net_migration_rate,
    d.tax_year as migration_tax_year,
    year(s.month) > d.tax_year as migration_is_carried_forward
from {{ ref('int_spine') }} as s
asof left join dated as d
    on s.geo_level = d.geo_level and s.geo_code = d.geo_code and s.month >= d.year_start
