-- Rents per place and month: Zillow ZORI and HUD's two-bedroom Fair Market Rent. An FMR fiscal year starts on
-- 1 October of the year before; the latest one carries forward until the next is published. A metro takes its
-- core FMR area (the first in config/metros.yml); a ZIP takes its Small Area FMR when HUD publishes one for that
-- fiscal year, else the metro's.
-- shortcut: ZIPs in a metro's peripheral FMR areas (single-county splits) get the core area's FMR; join those
-- areas by county if ZIP-level FMRs matter
with fmr as (
    select
        f.*,
        m.cbsa_code as metro_cbsa_code,
        make_date(f.fiscal_year - 1, 10, 1) as fiscal_year_start
    from {{ ref('fct_fair_market_rents') }} as f
    inner join {{ ref('dim_metro') }} as m on f.fmr_area_code = m.hud_fmr_areas[1]
),

metro_fmr as (
    select
        metro_cbsa_code,
        fiscal_year,
        fiscal_year_start,
        fmr_2br_usd
    from fmr
    where zip is null
),

zip_fmr as (
    select
        'zip' as geo_level,
        zip,
        fiscal_year,
        fiscal_year_start,
        fmr_2br_usd
    from fmr
    where zip is not null
)

select
    s.geo_level,
    s.geo_code,
    s.month,
    r.zori_usd,
    case when zf.fiscal_year = mf.fiscal_year then zf.fmr_2br_usd else mf.fmr_2br_usd end as fmr_2br_usd,
    mf.fiscal_year as fmr_fiscal_year,
    s.month >= make_date(mf.fiscal_year, 10, 1) as fmr_is_carried_forward
from {{ ref('int_spine') }} as s
left join {{ ref('fct_rents') }} as r
    on s.geo_level = r.geo_level and s.geo_code = r.geo_code and s.month = r.month
asof left join metro_fmr as mf
    on s.cbsa_code = mf.metro_cbsa_code and s.month >= mf.fiscal_year_start
asof left join zip_fmr as zf
    on s.geo_level = zf.geo_level and s.geo_code = zf.zip and s.month >= zf.fiscal_year_start
