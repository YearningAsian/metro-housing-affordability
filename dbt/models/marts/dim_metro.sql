-- The study metros, with the key each source uses for them.
with cbsa as (
    select
        cbsa_code,
        any_value(cbsa_title) as cbsa_title,
        bool_and(is_metropolitan) as is_metropolitan,
        count(*) as county_count,
        list(distinct metro_division_code order by metro_division_code)
        filter (where metro_division_code is not null) as metro_division_codes
    from {{ ref('dim_county') }}
    where cbsa_code is not null
    group by cbsa_code
)

select
    m.cbsa_code,
    m.name as metro_name,
    m.role,
    c.cbsa_title,
    c.is_metropolitan,
    c.county_count,
    c.metro_division_codes,
    m.zillow_region_id::bigint as zillow_region_id,
    m.redfin_table_ids,
    m.fred_unemployment_series,
    m.hud_fmr_areas,
    -- QCEW names MSAs with C + the first four CBSA digits
    'C' || left(m.cbsa_code, 4) as qcew_area_fips
from {{ ref('stg_config__metros') }} as m
left join cbsa as c on m.cbsa_code = c.cbsa_code
