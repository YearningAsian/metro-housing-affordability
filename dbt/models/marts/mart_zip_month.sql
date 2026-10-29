-- One row per study ZIP (with residential addresses) and month, with its metro: the same columns as
-- mart_metro_month, where county data reaches ZIPs as res_ratio-weighted averages of county rates.
-- Incremental: a plain dbt build rewrites only the last 24 months. The monthly pipeline passes --full-refresh,
-- because Zillow and Redfin restate older months too (see docs/warehouse_design.md).
{{ config(materialized='incremental', unique_key=['zip', 'month'], incremental_strategy='delete+insert') }}

with place_month as (
    {{ place_month('zip', 'zip') }}
)

select * from place_month  -- noqa: AM04
{% if is_incremental() %}
    -- filtered after place_month so the yoy columns still see the 12 months before the window
    where month > (select max(t.month) from {{ this }} as t) - interval 24 month
{% endif %}
