-- Every month in mart_metro_month has Zillow values (ZHVI and ZORI) for every study metro. The mart is a spine,
-- so it always has the rows; a gap means a Zillow file came in short or a metro's region id stopped matching.
select
    m.month,
    count(m.zhvi_usd) as metros_with_zhvi,
    count(m.zori_usd) as metros_with_zori
from {{ ref('mart_metro_month') }} as m
group by m.month
having
    count(m.zhvi_usd) < (select count(*) from {{ ref('dim_metro') }})
    or count(m.zori_usd) < (select count(*) from {{ ref('dim_metro') }})
