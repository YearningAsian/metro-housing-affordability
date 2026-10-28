-- Every US county (2024 boundaries), with its 2023 CBSA when it has one.
-- IRS migration needs counties outside metros too.
select
    c.county_fips,
    c.state_fips,
    c.state_code,
    c.county_name,
    d.cbsa_code,
    d.cbsa_title,
    d.is_metropolitan,
    d.metro_division_code,
    d.metro_division_title,
    d.csa_code,
    d.is_central_county,
    m.cbsa_code is not null as is_study_metro
from {{ ref('stg_census_geo__county_shapes') }} as c
left join {{ ref('stg_census_geo__cbsa_delineation') }} as d on c.county_fips = d.county_fips
left join {{ ref('stg_config__metros') }} as m on d.cbsa_code = m.cbsa_code
