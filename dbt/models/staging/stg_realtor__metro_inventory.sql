-- Realtor.com research inventory (MLS-listed homes for sale), one row per CBSA and month. The _yy columns are
-- Realtor.com's own: a fractional change for counts and days, a difference in points for shares.
select
    cbsa_code,
    cbsa_title,
    strptime(month_date_yyyymm, '%Y%m')::date as month,
    median_listing_price::double as median_listing_price_usd,
    active_listing_count::double as active_listing_count,
    active_listing_count_yy::double as active_listing_count_yy,
    new_listing_count::double as new_listing_count,
    median_days_on_market::double as median_days_on_market,
    median_days_on_market_yy::double as median_days_on_market_yy,
    price_reduced_share::double as price_reduced_share,
    price_reduced_share_yy::double as price_reduced_share_yy,
    quality_flag::double = 1 as is_quality_flagged
from {{ source('bronze', 'realtor__metro_inventory') }}
{{ latest_load() }}
