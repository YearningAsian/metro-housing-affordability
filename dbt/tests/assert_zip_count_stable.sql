-- The number of ZIPs with a Zillow value drops no more than 5% from one month to the next. A bigger drop means a
-- truncated ZIP file or a broken ZIP join. The worst drop through September 2026 is 0.4%.
with counts as (
    select
        month,
        count(zhvi_usd) as zhvi_zips,
        count(zori_usd) as zori_zips
    from {{ ref('mart_zip_month') }}
    group by month
)

select
    month,
    zhvi_zips,
    zori_zips,
    lag(zhvi_zips) over (order by month) as prev_zhvi_zips,
    lag(zori_zips) over (order by month) as prev_zori_zips
from counts
qualify zhvi_zips < 0.95 * prev_zhvi_zips or zori_zips < 0.95 * prev_zori_zips
