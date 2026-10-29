{{ config(severity='warn') }}
-- Yearly permit units per metro in fct_permits against the BPS annual files, within 15%. Monthly files are never
-- revised and the annual files add late reports, so monthly sums run a little low. A warning, not an error: the gap
-- is in the source. Known: Nashville 2022 is 36% low because Davidson County's monthly reports sum to 5,525 units
-- against 15,285 in the annual file.
with monthly as (
    select
        cbsa_code,
        year(month) as permit_year,
        sum(total_units) as units
    from {{ ref('fct_permits') }}
    group by cbsa_code, year(month)
),

annual as (
    select
        c.cbsa_code,
        year(p.period_start) as permit_year,
        sum(p.units_1 + p.units_2 + p.units_3_4 + p.units_5_plus) as units
    from {{ ref('stg_bps__permits') }} as p
    inner join {{ ref('dim_county') }} as c on p.county_fips = c.county_fips and c.is_study_metro
    where p.file_type = 'annual'
    group by c.cbsa_code, year(p.period_start)
)

select
    a.cbsa_code,
    a.permit_year,
    m.units as monthly_units,
    a.units as annual_units,
    m.units / a.units - 1 as rel_diff
from annual as a
left join monthly as m on a.cbsa_code = m.cbsa_code and a.permit_year = m.permit_year
where m.units is null or abs(m.units / a.units - 1) > 0.15
