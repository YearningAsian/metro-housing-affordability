-- Every US county (2024 boundaries), with its 2023 CBSA when it has one.
-- IRS migration needs counties outside metros too.
-- noqa: disable=RF05
-- the delineation file's column names contain spaces
with delineation as (
    select
        "CBSA Code" as cbsa_code,
        "CBSA Title" as cbsa_title,
        "Metropolitan Division Code" as metro_division_code,
        "Metropolitan Division Title" as metro_division_title,
        "CSA Code" as csa_code,
        "FIPS State Code" || "FIPS County Code" as county_fips,
        "Metropolitan/Micropolitan Statistical Area" = 'Metropolitan Statistical Area' as is_metropolitan,
        "Central/Outlying County" = 'Central' as is_central_county
    from {{ source('samples', 'cbsa_delineation') }}
    where regexp_full_match("CBSA Code", '\d{5}')
)
-- noqa: enable=RF05

select
    c.geoid as county_fips,
    c.statefp as state_fips,
    c.stusps as state_code,
    c.namelsad as county_name,
    d.cbsa_code,
    d.cbsa_title,
    d.is_metropolitan,
    d.metro_division_code,
    d.metro_division_title,
    d.csa_code,
    d.is_central_county,
    m.cbsa_code is not null as is_study_metro
from {{ source('samples', 'county_shapes') }} as c
left join delineation as d on c.geoid = d.county_fips
left join {{ ref('stg_config__metros') }} as m on d.cbsa_code = m.cbsa_code
