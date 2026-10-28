-- IRS SOI county-to-county migration, inflows and outflows in one shape: county_fips is the county the file is
-- about, other_* the origin (inflow) or destination (outflow). Rows with other_state_fips 96 hold the county's
-- total migration. -1 marks suppressed cells; AGI is reported in thousands of dollars.
with unioned as (
    select
        'inflow' as direction,
        y2_statefips as state_fips,
        y2_countyfips as county_code,
        y1_statefips as other_state_fips,
        y1_countyfips as other_county_code,
        y1_countyname as other_name,
        n1,
        n2,
        agi,
        _source_file
    from {{ source('bronze', 'irs_migration__inflow') }}
    {{ latest_load() }}
    union all
    select
        'outflow' as direction,
        y1_statefips as state_fips,
        y1_countyfips as county_code,
        y2_statefips as other_state_fips,
        y2_countyfips as other_county_code,
        y2_countyname as other_name,
        n1,
        n2,
        agi,
        _source_file
    from {{ source('bronze', 'irs_migration__outflow') }}
    {{ latest_load() }}
)

select
    direction,
    lpad(state_fips, 2, '0') || lpad(county_code, 3, '0') as county_fips,
    lpad(other_state_fips, 2, '0') as other_state_fips,
    lpad(other_state_fips, 2, '0') || lpad(other_county_code, 3, '0') as other_county_fips,
    other_name,
    -- countyinflow2223.csv covers moves between tax years 2022 and 2023
    2000 + regexp_extract(_source_file, '(\d{2})\.csv$', 1)::int as tax_year,
    nullif(n1::bigint, -1) as returns,
    nullif(n2::bigint, -1) as people,
    nullif(agi::bigint, -1) * 1000 as agi_usd
from unioned
