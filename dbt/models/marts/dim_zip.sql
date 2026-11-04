-- ZIPs in the study metros. A ZIP split across counties belongs to the county holding the largest share of its
-- residential addresses (total addresses break ties and decide for ZIPs with none). County-level values are
-- allocated to ZIPs by res_ratio from stg_hud_crosswalk__zip_county instead, so this rule only sets metro membership.
with ranked as (
    select
        zip,
        county_fips,
        res_ratio,
        count(*) over (partition by zip) as county_count,
        sum(res_ratio) over (partition by zip) as res_ratio_total,
        row_number() over (partition by zip order by res_ratio desc, tot_ratio desc, county_fips asc) as rn
    from {{ ref('stg_hud_crosswalk__zip_county') }}
),

-- FEMA expected annual building loss as a share of building value, res_ratio-weighted over the ZIP's counties;
-- a blank hazard loss means the hazard does not apply, so it counts as 0
risk as (
    select
        x.zip,
        sum(x.res_ratio * n.building_loss_rate) / sum(x.res_ratio) as building_loss_rate,
        sum(x.res_ratio * coalesce(n.hurricane_eal_buildings_usd, 0) / n.building_value_usd)
        / sum(x.res_ratio) as hurricane_loss_rate,
        sum(
            x.res_ratio
            * (coalesce(n.coastal_flood_eal_buildings_usd, 0) + coalesce(n.inland_flood_eal_buildings_usd, 0))
            / n.building_value_usd
        ) / sum(x.res_ratio) as flood_loss_rate
    from {{ ref('stg_hud_crosswalk__zip_county') }} as x
    inner join {{ ref('stg_fema_nri__counties') }} as n on x.county_fips = n.county_fips
    where x.res_ratio > 0
    group by x.zip
)

select
    r.zip,
    r.county_fips,
    c.cbsa_code,
    c.metro_division_code,
    r.res_ratio as primary_county_res_ratio,
    r.county_count,
    -- shortcut: assumes a ZIP maps to the ZCTA with the same code; use a ZIP-to-ZCTA crosswalk if joins look off
    z.zcta,
    z.zcta is not null as has_zcta,
    -- PO-box and business-only ZIPs: no residential addresses, and usually no ZCTA
    r.res_ratio_total = 0 as is_po_box_only,
    k.building_loss_rate,
    k.hurricane_loss_rate,
    k.flood_loss_rate
from ranked as r
inner join {{ ref('dim_county') }} as c on r.county_fips = c.county_fips
left join {{ ref('stg_census_geo__zcta_shapes') }} as z on r.zip = z.zcta
left join risk as k on r.zip = k.zip
where r.rn = 1 and c.is_study_metro
