-- Census building permits by county: monthly files, the two 2015 year-to-date files and the annual totals.
-- The county files report value in dollars.
with unioned as (
    select
        'monthly' as file_type,
        *
    from {{ source('bronze', 'bps__county_monthly') }}
    {{ latest_load() }}
    union all by name
    select
        'ytd' as file_type,
        *
    from {{ source('bronze', 'bps__county_ytd') }}
    {{ latest_load() }}
    union all by name
    select
        'annual' as file_type,
        *
    from {{ source('bronze', 'bps__county_annual') }}
    {{ latest_load() }}
)

select
    file_type,
    lpad(state_fips, 2, '0') || lpad(county_fips, 3, '0') as county_fips,
    -- YYYYMM, or YYYY for annual files
    survey_date,
    case
        when file_type = 'annual' then make_date(survey_date::int, 1, 1)
        else strptime(survey_date, '%Y%m')::date
    end as period_start,
    u1_units::int as units_1,
    u2_units::int as units_2,
    u34_units::int as units_3_4,
    u5p_units::int as units_5_plus,
    u1_bldgs::int + u2_bldgs::int + u34_bldgs::int + u5p_bldgs::int as buildings,
    u1_value::bigint + u2_value::bigint + u34_value::bigint + u5p_value::bigint as value_usd
from unioned
