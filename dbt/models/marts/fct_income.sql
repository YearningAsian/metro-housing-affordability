-- ACS estimates for the study metros, their counties and their ZIPs (through the ZCTA with the same code), one row
-- per place and vintage. Metros use the 1-year survey (single year, about a year fresher); counties and ZIPs, which
-- the 1-year survey mostly does not cover, use the 5-year survey.
with acs as (
    select * from {{ ref('stg_acs__estimates') }}
),

places as (
    select
        'metro' as place_level,
        m.cbsa_code as place_code,
        m.cbsa_code,
        a.*
    from acs as a
    inner join {{ ref('dim_metro') }} as m
        on a.geo_level = 'metro' and a.geo_code = m.cbsa_code and a.acs_survey = 'acs1'
    union all
    select
        'county' as place_level,
        c.county_fips as place_code,
        c.cbsa_code,
        a.*
    from acs as a
    inner join {{ ref('dim_county') }} as c
        on a.geo_level = 'county' and a.geo_code = c.county_fips and c.is_study_metro
    union all
    select
        'zip' as place_level,
        d.zip as place_code,
        d.cbsa_code,
        a.*
    from acs as a
    inner join {{ ref('dim_zip') }} as d on a.geo_level = 'zcta' and a.geo_code = d.zcta
)

select
    place_level as geo_level,
    place_code as geo_code,
    cbsa_code,
    acs_survey,
    acs_vintage,
    median_household_income_usd,
    population,
    median_gross_rent_usd,
    rent_pct_income,
    median_home_value_usd,
    median_real_estate_taxes_usd,
    households_by_income
from places
