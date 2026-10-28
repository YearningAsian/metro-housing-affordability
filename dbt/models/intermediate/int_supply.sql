-- Supply per place and month: Redfin listing counts, and building permits over the trailing 12 months per 1,000
-- residents (ACS population). Permits are county data: a metro sums its counties; a ZIP gets the average of its
-- counties' rates weighted by its residential addresses (res_ratio). Permit counts are not split across ZIPs.
with county_units as (
    select
        county_fips,
        cbsa_code,
        month,
        total_units,
        case
            when month >= min(month) over () + interval 11 month then
                sum(total_units) over (
                    partition by county_fips order by month
                    range between interval 11 month preceding and current row
                )
        end as units_12m
    from {{ ref('fct_permits') }}
),

county_population as (
    select
        geo_code as county_fips,
        make_date(acs_vintage, 1, 1) as vintage_start,
        population
    from {{ ref('fct_income') }}
    where geo_level = 'county'
),

county_rates as (
    select
        u.*,
        p.population,
        u.units_12m / p.population * 1000 as permits_per_1000
    from county_units as u
    asof left join county_population as p
        on u.county_fips = p.county_fips and u.month >= p.vintage_start
),

places as (
    select
        'metro' as geo_level,
        cbsa_code as geo_code,
        month,
        sum(total_units) as permit_units,
        sum(units_12m) / sum(population) * 1000 as permits_per_1000
    from county_rates
    group by cbsa_code, month
    union all by name
    select
        'zip' as geo_level,
        x.zip as geo_code,
        c.month,
        {{ weighted_avg('c.permits_per_1000', 'x.res_ratio') }} as permits_per_1000
    from {{ ref('stg_hud_crosswalk__zip_county') }} as x
    inner join county_rates as c on x.county_fips = c.county_fips
    group by x.zip, c.month
)

select
    s.geo_level,
    s.geo_code,
    s.month,
    a.homes_sold,
    a.pending_sales,
    a.new_listings,
    a.active_listings,
    a.inventory,
    a.months_of_supply,
    a.median_days_on_market,
    a.sale_to_list_pct,
    a.sold_above_list_pct,
    a.off_market_in_two_weeks_pct,
    p.permit_units,
    p.permits_per_1000
from {{ ref('int_spine') }} as s
left join {{ ref('fct_market_activity') }} as a
    on s.geo_level = a.geo_level and s.geo_code = a.geo_code and s.month = a.month
left join places as p
    on s.geo_level = p.geo_level and s.geo_code = p.geo_code and s.month = p.month
