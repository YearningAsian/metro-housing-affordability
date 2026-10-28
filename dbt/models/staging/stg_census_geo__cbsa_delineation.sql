-- Census CBSA delineation (July 2023), one row per county in a CBSA. The footnote rows at the end of the file are
-- dropped.
-- noqa: disable=RF05
-- the delineation file's column names contain spaces
select
    "CBSA Code" as cbsa_code,
    "CBSA Title" as cbsa_title,
    "Metropolitan Division Code" as metro_division_code,
    "Metropolitan Division Title" as metro_division_title,
    "CSA Code" as csa_code,
    "FIPS State Code" || "FIPS County Code" as county_fips,
    "Metropolitan/Micropolitan Statistical Area" = 'Metropolitan Statistical Area' as is_metropolitan,
    "Central/Outlying County" = 'Central' as is_central_county
from {{ source('bronze', 'census_geo__cbsa_delineation') }}
where regexp_full_match("CBSA Code", '\d{5}')
{{ latest_load() }}
-- noqa: enable=RF05
