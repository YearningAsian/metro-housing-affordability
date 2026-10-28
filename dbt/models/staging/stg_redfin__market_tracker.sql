-- Redfin housing market data (all residential, not seasonally adjusted), metros and ZIPs. Metro rows are calendar
-- months; ZIP rows are rolling three-month windows, dated by the window's last month. Redfin writes NA for gaps.
-- noqa: disable=RF05,RF06
-- Redfin quotes every column name (some contain spaces and symbols); keep them all quoted alike
with unioned as (
    select
        'metro' as geo_level,
        *
    from {{ source('bronze', 'redfin__metros') }}
    {{ latest_load() }}
    union all by name
    select
        'zip' as geo_level,
        *
    from {{ source('bronze', 'redfin__zips') }}
    {{ latest_load() }}
)

select
    geo_level,
    -- metro rows: CBSA or metro division code; ZIP rows: Redfin's internal region id
    "REGION ID" as region_id,
    case when geo_level = 'zip' then "REGION NAME" end as zip,
    "METRO" as zip_metro_name,
    "PERIOD BEGIN"::date as period_begin,
    "PERIOD END"::date as period_end,
    case
        when geo_level = 'metro' then "PERIOD BEGIN"::date
        else date_trunc('month', "PERIOD END"::date)::date
    end as month,
    nullif("HOMES SOLD", 'NA')::double as homes_sold,
    nullif("PENDING SALES", 'NA')::double as pending_sales,
    nullif("NEW LISTINGS", 'NA')::double as new_listings,
    nullif("ACTIVE LISTINGS", 'NA')::double as active_listings,
    nullif("INVENTORY", 'NA')::double as inventory,
    nullif("MONTHS OF SUPPLY", 'NA')::double as months_of_supply,
    nullif("MEDIAN DAYS ON MARKET (DAYS)", 'NA')::double as median_days_on_market,
    nullif("MEDIAN SALE PRICE NSA ($)", 'NA')::double as median_sale_price_usd,
    nullif("MEDIAN SALE PRICE PER SQ.FT. ($)", 'NA')::double as median_sale_ppsf_usd,
    nullif("MEDIAN NEW LISTING PRICE ($)", 'NA')::double as median_list_price_usd,
    nullif("MEDIAN NEW LISTING PRICE PER SQ.FT. ($)", 'NA')::double as median_list_ppsf_usd,
    nullif("AVERAGE SALE TO LIST RATIO (%)", 'NA')::double as sale_to_list_pct,
    nullif("SHARE SOLD ABOVE ORIGINAL LIST (%)", 'NA')::double as sold_above_list_pct,
    nullif("PERCENT OFF MARKET IN TWO WEEKS (%)", 'NA')::double as off_market_in_two_weeks_pct,
    "LAST UPDATED"::date as last_updated
from unioned
-- noqa: enable=RF05,RF06
