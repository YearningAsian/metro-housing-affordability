-- Home prices per place and month: Zillow ZHVI and Redfin's sale and list prices.
select
    s.geo_level,
    s.geo_code,
    s.month,
    p.zhvi_usd,
    a.median_sale_price_usd,
    a.median_sale_ppsf_usd,
    a.median_list_price_usd,
    a.median_list_ppsf_usd,
    a.is_division_blend
from {{ ref('int_spine') }} as s
left join {{ ref('fct_home_prices') }} as p
    on s.geo_level = p.geo_level and s.geo_code = p.geo_code and s.month = p.month
left join {{ ref('fct_market_activity') }} as a
    on s.geo_level = a.geo_level and s.geo_code = a.geo_code and s.month = a.month
