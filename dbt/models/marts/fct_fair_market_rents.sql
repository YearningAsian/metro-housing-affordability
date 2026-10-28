-- HUD Fair Market Rents for the study metros' FMR areas (ingest fetches only those), one row per area, fiscal year
-- and, for Small Area FMR areas, ZIP.
select * from {{ ref('stg_hud_fmr__fmr') }}  -- noqa: AM04
