-- ZIPs in the study metros. A ZIP split across counties belongs to the county holding the largest share of its
-- residential addresses (total addresses break ties and decide for ZIPs with none). County-level values are
-- allocated to ZIPs by res_ratio from stg_hud__zip_county instead, so this rule only sets metro membership.
with ranked as (
    select
        zip,
        county_fips,
        res_ratio,
        count(*) over (partition by zip) as county_count,
        sum(res_ratio) over (partition by zip) as res_ratio_total,
        row_number() over (partition by zip order by res_ratio desc, tot_ratio desc, county_fips asc) as rn
    from {{ ref('stg_hud__zip_county') }}
),

zctas as (
    select geoid20 as zcta from {{ source('samples', 'zcta_shapes') }}
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
    r.res_ratio_total = 0 as is_po_box_only
from ranked as r
inner join {{ ref('dim_county') }} as c on r.county_fips = c.county_fips
left join zctas as z on r.zip = z.zcta
where r.rn = 1 and c.is_study_metro
