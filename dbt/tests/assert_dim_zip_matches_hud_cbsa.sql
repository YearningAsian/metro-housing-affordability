{{ config(severity='warn') }}
-- dim_zip derives the metro through the ZIP's main county. HUD's own ZIP-to-CBSA file should agree; a
-- disagreement means the two crosswalks or the delineation drifted apart.
with hud as (
    select unnest(data.results, recursive := true)
    from {{ source('samples', 'hud_zip_cbsa') }}
),

hud_main as (
    select
        zip,
        geoid as cbsa_code
    from hud
    qualify row_number() over (partition by zip order by res_ratio desc, tot_ratio desc, geoid asc) = 1
)

select
    d.zip,
    d.cbsa_code,
    h.cbsa_code as hud_cbsa_code
from {{ ref('dim_zip') }} as d
left join hud_main as h on d.zip = h.zip
where h.cbsa_code is distinct from d.cbsa_code
