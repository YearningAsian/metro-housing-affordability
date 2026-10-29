-- Zillow's published metro ZHVI against our roll-up of its ZIP ZHVIs (weighted by ACS population), within 20%.
-- They are not the same measure: Zillow weights every home, and a population-weighted mean of ZIP values runs high.
-- Through September 2026 the roll-up is 0.2% to 12.9% above the metro value. A gap past 20% means the metro or ZIP
-- files, or the ZIP-to-metro mapping, went wrong.
with rollup as (
    select
        cbsa_code,
        month,
        sum(zhvi_usd * population) / sum(population) as zip_rollup_zhvi_usd
    from {{ ref('mart_zip_month') }}
    where zhvi_usd is not null and population > 0
    group by cbsa_code, month
)

select
    m.cbsa_code,
    m.month,
    m.zhvi_usd as metro_zhvi_usd,
    r.zip_rollup_zhvi_usd,
    r.zip_rollup_zhvi_usd / m.zhvi_usd - 1 as rel_diff
from {{ ref('mart_metro_month') }} as m
inner join rollup as r on m.cbsa_code = r.cbsa_code and m.month = r.month
where abs(r.zip_rollup_zhvi_usd / m.zhvi_usd - 1) > 0.20
