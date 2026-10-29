-- One row per study metro, origin county outside it and tax year: IRS movers into the metro's counties from that
-- county, with both places' Zillow ZHVI averaged over the move year. IRS rows with other_state_fips above 56 are
-- totals, foreign and "other flows" (flows under 20 returns, which IRS pools), and moves within the metro are dropped.
-- A tax_year 2023 row (file 2223) compares addresses on returns filed in 2022 and 2023, so the moves fall mostly in
-- 2022: move_year = tax_year - 1.
with metro_counties as (
    select
        county_fips,
        cbsa_code
    from {{ ref('dim_county') }}
    where is_study_metro
),

inflows as (
    select
        m.cbsa_code,
        f.other_county_fips as origin_county_fips,
        f.tax_year,
        any_value(f.other_name) as irs_origin_name,
        sum(f.returns) as returns,
        sum(f.people) as people,
        sum(f.agi_usd) as agi_usd
    from {{ ref('stg_irs_migration__flows') }} as f
    inner join metro_counties as m on f.county_fips = m.county_fips
    left join metro_counties as same on f.other_county_fips = same.county_fips and m.cbsa_code = same.cbsa_code
    where f.direction = 'inflow' and f.other_state_fips <= '56' and same.county_fips is null
    group by m.cbsa_code, f.other_county_fips, f.tax_year
),

county_zhvi as (
    select
        county_fips,
        year(month) as year,
        avg(value) as zhvi_usd
    from {{ ref('stg_zillow__indexes') }}
    where geo_level = 'county' and measure = 'zhvi'
    group by county_fips, year(month)
),

metro_zhvi as (
    select
        cbsa_code,
        year(month) as year,
        avg(zhvi_usd) as zhvi_usd
    from {{ ref('fct_home_prices') }}
    where geo_level = 'metro'
    group by cbsa_code, year(month)
)

select
    i.cbsa_code,
    i.origin_county_fips,
    -- Connecticut's pre-2022 counties are not in the 2024 boundaries, so they keep the IRS name and no metro
    coalesce(c.county_name || ', ' || c.state_code, i.irs_origin_name) as origin_name,
    c.cbsa_code as origin_cbsa_code,
    c.cbsa_title as origin_cbsa_title,
    i.tax_year,
    i.tax_year - 1 as move_year,
    i.returns,
    i.people,
    i.agi_usd,
    i.agi_usd / nullif(i.returns, 0) as agi_per_return_usd,
    oz.zhvi_usd as origin_zhvi_usd,
    mz.zhvi_usd as metro_zhvi_usd,
    oz.zhvi_usd / mz.zhvi_usd as origin_to_metro_zhvi
from inflows as i
left join {{ ref('dim_county') }} as c on i.origin_county_fips = c.county_fips
left join county_zhvi as oz on i.origin_county_fips = oz.county_fips and i.tax_year - 1 = oz.year
left join metro_zhvi as mz on i.cbsa_code = mz.cbsa_code and i.tax_year - 1 = mz.year
