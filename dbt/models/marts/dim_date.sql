-- One row per month from 2012 (the earliest data any mart uses) to the current month.
select
    t.month::date as month,
    year(t.month) as year,
    quarter(t.month) as quarter,
    month(t.month) as month_of_year,
    date_trunc('quarter', t.month)::date as quarter_start
from generate_series(date '2012-01-01', date_trunc('month', current_date), interval 1 month) as t (month)
