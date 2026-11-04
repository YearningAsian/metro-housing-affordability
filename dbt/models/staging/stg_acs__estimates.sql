-- ACS 5-year estimates by ZCTA, county and CBSA, plus 1-year estimates by CBSA, one row per survey, place and
-- vintage. The Census API writes negative sentinels (e.g. -666666666) for estimates it cannot publish; those become
-- null.
with unioned as (
    select
        'acs5' as acs_survey,
        'zcta' as geo_level,
        "zip code tabulation area" as geo_code,  -- noqa: RF05
        *
    from {{ source('bronze', 'acs__zcta') }}
    {{ latest_load() }}
    union all by name
    select
        'acs5' as acs_survey,
        'county' as geo_level,
        state || county as geo_code,
        *
    from {{ source('bronze', 'acs__county') }}
    {{ latest_load() }}
    union all by name
    select
        'acs5' as acs_survey,
        'metro' as geo_level,
        "metropolitan statistical area/micropolitan statistical area" as geo_code,  -- noqa: RF05
        *
    from {{ source('bronze', 'acs__cbsa') }}
    {{ latest_load() }}
    union all by name
    select
        'acs1' as acs_survey,
        'metro' as geo_level,
        "metropolitan statistical area/micropolitan statistical area" as geo_code,  -- noqa: RF05
        *
    from {{ source('bronze', 'acs__cbsa_1yr') }}
    {{ latest_load() }}
)

select
    acs_survey,
    geo_level,
    geo_code,
    vintage::int as acs_vintage,
    case when b19013_001e::double >= 0 then b19013_001e::double end as median_household_income_usd,
    case when b01003_001e::double >= 0 then b01003_001e::double end as population,
    case when b25064_001e::double >= 0 then b25064_001e::double end as median_gross_rent_usd,
    case when b25071_001e::double >= 0 then b25071_001e::double end as rent_pct_income,
    case when b25077_001e::double >= 0 then b25077_001e::double end as median_home_value_usd,
    case when b25103_001e::double >= 0 then b25103_001e::double end as median_real_estate_taxes_usd,
    -- B19001_002E to _017E: under $10k, $10k-15k, ... $150k-200k, $200k or more
    [
        {%- for i in range(2, 18) %}
            case when b19001_{{ '%03d' % i }}e::double >= 0 then b19001_{{ '%03d' % i }}e::double end
            {%- if not loop.last %},{% endif %}
        {%- endfor %}
    ] as households_by_income
from unioned
