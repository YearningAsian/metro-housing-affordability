-- One row per study metro and month t for the turning-point model: the features as of prediction_date and whether
-- home values were lower 12 months later. Each source joins on its release date, as in features_zip_month. Zillow and
-- Realtor.com restate past months, and the warehouse keeps only their latest release.
with metros as (
    select
        cbsa_code,
        month,
        zhvi_yoy_growth as zhvi_growth_12m,
        lead(zhvi_usd, 12) over (partition by cbsa_code order by month) / zhvi_usd - 1 as target_growth_12m,
        (month + interval 1 month + interval 19 day)::date as prediction_date,
        (month + interval 1 month + interval 14 day)::date as zillow_available_on
    from {{ ref('mart_metro_month') }}
),

mortgage as (
    select
        value - lag(value, 12) over (order by month) as mortgage_rate_change_12m,
        (month + interval 1 month)::date as mortgage_available_on
    from {{ ref('fct_economy') }}
    where series_id = 'MORTGAGE30US'
),

realtor as (
    select
        cbsa_code,
        month as realtor_month,
        -- no fixed schedule: September 2026 came out on 30 September, October not by 4 November
        (month + interval 2 month)::date as realtor_available_on,
        active_listing_count_yy,
        price_reduced_share_yy,
        median_days_on_market_yy
    from {{ ref('stg_realtor__metro_inventory') }}
)

select
    m.cbsa_code,
    m.month,
    m.prediction_date,
    m.zhvi_growth_12m,
    mo.mortgage_rate_change_12m,
    r.realtor_month,
    r.active_listing_count_yy,
    r.price_reduced_share_yy,
    r.median_days_on_market_yy,
    m.zillow_available_on,
    mo.mortgage_available_on,
    r.realtor_available_on,
    m.target_growth_12m,
    m.target_growth_12m < 0 as target_negative
from metros as m
asof left join mortgage as mo on m.prediction_date >= mo.mortgage_available_on
asof left join realtor as r on m.cbsa_code = r.cbsa_code and m.prediction_date >= r.realtor_available_on
where r.active_listing_count_yy is not null and m.zhvi_growth_12m is not null
