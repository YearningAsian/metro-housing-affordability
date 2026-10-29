-- One row per study ZIP and month t from 2016 where the ZIP has a ZHVI: the features as of prediction_date (the
-- pipeline run on the 20th of the next month), the 12-month-ahead targets and a time split.
-- Point in time: each source joins on its release date (its *_available_on column), taking the latest release on or
-- before prediction_date. Release lags are conservative estimates of each publisher's schedule.
-- Not point in time: Zillow and Redfin restate past months, and the warehouse keeps only their latest release.
{% set growth_months = [1, 3, 6, 12] %}
with zips as (
    select
        zip,
        cbsa_code,
        month,
        zhvi_usd,
        zori_usd,
        {% for k in growth_months %}
            zhvi_usd / lag(zhvi_usd, {{ k }}) over w - 1 as zhvi_growth_{{ k }}m,
            zori_usd / lag(zori_usd, {{ k }}) over w - 1 as zori_growth_{{ k }}m,
        {% endfor %}
        zhvi_usd / median(zhvi_usd) over (partition by cbsa_code, month) as zhvi_to_metro_median,
        lead(zhvi_usd, 12) over w / zhvi_usd - 1 as target_growth_12m,
        (month + interval 1 month + interval 19 day)::date as prediction_date,
        -- Zillow publishes a month in the middle of the next one
        (month + interval 1 month + interval 14 day)::date as zillow_available_on
    from {{ ref('mart_zip_month') }}
    window w as (partition by zip order by month)
),

rolling as (
    select
        *,
        case
            when count(zhvi_growth_1m) over w12 = 12 then stddev_samp(zhvi_growth_1m) over w12
        end as zhvi_volatility_12m,
        -- the last 3 months annualized, minus the last 12
        power(1 + zhvi_growth_3m, 4) - 1 - zhvi_growth_12m as zhvi_momentum
    from zips
    window w12 as (partition by zip order by month rows between 11 preceding and current row)
),

redfin as (
    select
        zip,
        month as redfin_month,
        -- Redfin publishes a month in the middle of the next one; a full month later is the safe side
        (month + interval 2 month)::date as redfin_available_on,
        inventory,
        median_days_on_market,
        sale_to_list_pct,
        sold_above_list_pct,
        off_market_in_two_weeks_pct
    from {{ ref('mart_zip_month') }}
),

mortgage as (
    select
        value as mortgage_rate_pct,
        -- a monthly average of a weekly series is complete when the month ends
        (month + interval 1 month)::date as mortgage_available_on
    from {{ ref('fct_economy') }}
    where series_id = 'MORTGAGE30US'
),

income as (
    select
        geo_code as zip,
        acs_vintage as income_acs_vintage,
        median_household_income_usd,
        {{ acs_available_on('acs_vintage') }} as income_available_on
    from {{ ref('fct_income') }}
    where geo_level = 'zip'
),

-- the mart's ZIP wages (res_ratio-weighted county QCEW), one row per quarter
wage_quarters as (
    select
        zip,
        min(month) as wages_quarter_start,
        any_value(avg_weekly_wage_usd) as avg_weekly_wage_usd
    from {{ ref('mart_zip_month') }}
    where not wages_is_carried_forward
    group by zip, wages_quarter
),

wages as (
    select
        q.zip,
        q.wages_quarter_start,
        q.avg_weekly_wage_usd,
        q.avg_weekly_wage_usd / y.avg_weekly_wage_usd - 1 as avg_weekly_wage_yoy_growth,
        -- QCEW publishes a quarter about five months after it ends
        (q.wages_quarter_start + interval 9 month)::date as wages_available_on
    from wage_quarters as q
    left join wage_quarters as y
        on q.zip = y.zip and y.wages_quarter_start = q.wages_quarter_start - interval 12 month
),

-- permits as in int_supply, but each trailing 12-month window is dated by its last release and divided by the
-- ACS population published by then
county_permits as (
    select
        county_fips,
        month,
        sum(total_units) over w as units_12m,
        count(*) over w as months_12m,
        -- BPS publishes a month's county permits within a month of its end; the annual totals behind the estimated
        -- months come out in May of the next year
        max(
            case when is_estimated then make_date(year(month) + 1, 6, 1) else (month + interval 2 month)::date end
        ) over w as permits_available_on
    from {{ ref('fct_permits') }}
    window w as (partition by county_fips order by month range between interval 11 month preceding and current row)
),

county_population as (
    select
        geo_code as county_fips,
        population,
        {{ acs_available_on('acs_vintage') }} as population_available_on
    from {{ ref('fct_income') }}
    where geo_level = 'county'
),

county_rates as (
    select
        c.county_fips,
        c.month,
        c.permits_available_on,
        c.units_12m / p.population * 1000 as permits_per_1000
    from county_permits as c
    asof inner join county_population as p
        on c.county_fips = p.county_fips and c.permits_available_on >= p.population_available_on
    where c.months_12m = 12
),

permits as (
    select
        x.zip,
        c.month as permits_month,
        max(c.permits_available_on) as permits_available_on,
        {{ weighted_avg('c.permits_per_1000', 'x.res_ratio') }} as permits_per_1000
    from {{ ref('stg_hud_crosswalk__zip_county') }} as x
    inner join county_rates as c on x.county_fips = c.county_fips
    group by x.zip, c.month
    -- several windows can share a release date (a year of estimated months); keep the latest
    qualify c.month = max(c.month) over (partition by x.zip, max(c.permits_available_on))
),

features as (
    select
        z.zip,
        z.cbsa_code,
        z.month,
        z.prediction_date,
        z.zhvi_usd,
        {% for k in growth_months %}
            z.zhvi_growth_{{ k }}m,
        {% endfor %}
        z.zori_usd,
        {% for k in growth_months %}
            z.zori_growth_{{ k }}m,
        {% endfor %}
        z.zhvi_volatility_12m,
        z.zhvi_momentum,
        mm.zhvi_yoy_growth as metro_zhvi_growth_12m,
        z.zhvi_to_metro_median,
        r.redfin_month,
        r.inventory,
        r.median_days_on_market,
        r.sale_to_list_pct,
        r.sold_above_list_pct,
        r.off_market_in_two_weeks_pct,
        p.permits_month,
        p.permits_per_1000,
        mo.mortgage_rate_pct,
        i.income_acs_vintage,
        z.zhvi_usd / i.median_household_income_usd as price_to_income,
        w.wages_quarter_start,
        w.avg_weekly_wage_usd,
        w.avg_weekly_wage_yoy_growth,
        -- monthly rent over a month of the average weekly wage, as in the marts
        z.zori_usd / (w.avg_weekly_wage_usd * 52 / 12) as rent_to_wage,
        z.zillow_available_on,
        r.redfin_available_on,
        p.permits_available_on,
        mo.mortgage_available_on,
        i.income_available_on,
        w.wages_available_on,
        z.target_growth_12m,
        case
            when z.target_growth_12m is not null
                then percent_rank() over (
                    partition by z.cbsa_code, z.month, z.target_growth_12m is null order by z.target_growth_12m
                ) >= 0.8
        end as target_top20
    from rolling as z
    left join {{ ref('mart_metro_month') }} as mm on z.cbsa_code = mm.cbsa_code and z.month = mm.month
    asof left join redfin as r on z.zip = r.zip and z.prediction_date >= r.redfin_available_on
    asof left join permits as p on z.zip = p.zip and z.prediction_date >= p.permits_available_on
    asof left join mortgage as mo on z.prediction_date >= mo.mortgage_available_on
    asof left join income as i on z.zip = i.zip and z.prediction_date >= i.income_available_on
    asof left join wages as w on z.zip = w.zip and z.prediction_date >= w.wages_available_on
    where z.month >= date '2016-01-01' and z.zhvi_usd is not null
)

select
    *,
    -- by the month of the prediction; 'score' rows are the last 12 months, whose outcome is not known yet
    case
        when month > (select max(f.month) from features as f) - interval 12 month then 'score'
        when month < date '2023-01-01' then 'train'
        when month < date '2024-01-01' then 'validate'
        else 'test'
    end as split
from features
