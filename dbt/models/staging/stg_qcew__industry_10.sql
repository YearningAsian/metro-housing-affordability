-- BLS QCEW all-industry totals, one row per area, ownership and quarter. disclosure_code N marks suppressed
-- cells, which BLS fills with zeros; those become null.
select
    area_fips,
    own_code,
    agglvl_code,
    year::int as year,
    qtr::int as quarter_of_year,
    make_date(year::int, qtr::int * 3 - 2, 1) as quarter_start,
    disclosure_code,
    case when coalesce(disclosure_code, '') != 'N' then qtrly_estabs::int end as establishments,
    case when coalesce(disclosure_code, '') != 'N' then month1_emplvl::int end as employment_month_1,
    case when coalesce(disclosure_code, '') != 'N' then month2_emplvl::int end as employment_month_2,
    case when coalesce(disclosure_code, '') != 'N' then month3_emplvl::int end as employment_month_3,
    case when coalesce(disclosure_code, '') != 'N' then total_qtrly_wages::double end as total_wages_usd,
    case when coalesce(disclosure_code, '') != 'N' then avg_wkly_wage::double end as avg_weekly_wage_usd
from {{ source('bronze', 'qcew__industry_10') }}
{{ latest_load() }}
