-- FRED series by month: each metro's unemployment rate and payrolls (cbsa_code and metro_measure set) and the
-- national series (both null). Weekly series (MORTGAGE30US) become the month's average.
select
    o.series_id,
    m.cbsa_code,
    case
        when o.series_id = m.fred_unemployment_series then 'unemployment_rate'
        when o.series_id = m.fred_jobs_series then 'payroll_jobs'
    end as metro_measure,
    date_trunc('month', o.observation_date)::date as month,
    avg(o.value) as value
from {{ ref('stg_fred__observations') }} as o
left join {{ ref('dim_metro') }} as m on o.series_id in (m.fred_unemployment_series, m.fred_jobs_series)
where o.value is not null
group by all
