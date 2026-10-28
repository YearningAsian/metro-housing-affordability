-- FRED series by month: the metro unemployment rates (cbsa_code set) and the national series (cbsa_code null).
-- Weekly series (MORTGAGE30US) become the month's average.
select
    o.series_id,
    m.cbsa_code,
    date_trunc('month', o.observation_date)::date as month,
    avg(o.value) as value
from {{ ref('stg_fred__observations') }} as o
left join {{ ref('dim_metro') }} as m on o.series_id = m.fred_unemployment_series
where o.value is not null
group by o.series_id, m.cbsa_code, date_trunc('month', o.observation_date)
