-- One row per study place and month, the grain of both marts: every metro, and every ZIP with residential
-- addresses, from 2015 (the first year all sources cover) to the latest Zillow month. Every int_ model returns
-- exactly these rows.
with months as (
    select d.month from {{ ref('dim_date') }} as d
    where d.month between date '2015-01-01' and (select max(p.month) from {{ ref('fct_home_prices') }} as p)
)

select
    'metro' as geo_level,
    m.cbsa_code as geo_code,
    m.cbsa_code,
    mo.month
from {{ ref('dim_metro') }} as m
cross join months as mo
union all
select
    'zip' as geo_level,
    z.zip as geo_code,
    z.cbsa_code,
    mo.month
from {{ ref('dim_zip') }} as z
cross join months as mo
where not z.is_po_box_only
