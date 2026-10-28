-- Redfin market activity for the study metros and their ZIPs, one row per place and month. Dallas-Fort Worth and
-- Seattle come as two metro divisions each: counts are summed, and medians and shares are averaged weighted by
-- homes sold (an approximation of the true metro median).
{% set counts = ['homes_sold', 'pending_sales', 'new_listings', 'active_listings', 'inventory'] %}
{% set rates = [
    'median_days_on_market', 'median_sale_price_usd', 'median_sale_ppsf_usd', 'median_list_price_usd',
    'median_list_ppsf_usd', 'sale_to_list_pct', 'sold_above_list_pct', 'off_market_in_two_weeks_pct',
] %}
with redfin as (
    select * from {{ ref('stg_redfin__market_tracker') }}
),

metro_regions as (
    select
        cbsa_code,
        unnest(redfin_table_ids) as region_id
    from {{ ref('dim_metro') }}
),

metros as (
    select
        'metro' as geo_level,
        m.cbsa_code as geo_code,
        m.cbsa_code,
        r.month,
        {% for c in counts %}
            sum(r.{{ c }}) as {{ c }},
        {% endfor %}
        {% for c in rates %}
            case
                when count(*) = 1 then any_value(r.{{ c }}) else {{ weighted_avg('r.' ~ c, 'r.homes_sold') }}
            end as {{ c }},
        {% endfor %}
        case
            when count(*) = 1 then any_value(r.months_of_supply) else sum(r.inventory) / nullif(sum(r.homes_sold), 0)
        end as months_of_supply,
        count(*) > 1 as is_division_blend
    from metro_regions as m
    inner join redfin as r on r.geo_level = 'metro' and m.region_id = r.region_id
    group by m.cbsa_code, r.month
),

zips as (
    select
        'zip' as geo_level,
        d.zip as geo_code,
        d.cbsa_code,
        r.month,
        {% for c in counts + rates %}
            r.{{ c }},
        {% endfor %}
        r.months_of_supply,
        false as is_division_blend
    from redfin as r
    inner join {{ ref('dim_zip') }} as d on r.geo_level = 'zip' and r.zip = d.zip
)

select * from metros
union all by name
select * from zips
