-- FEMA National Risk Index, one row per county. Scores are national percentile ranks (0-100);
-- a blank hazard loss means FEMA found the hazard does not apply to the county.
select
    stcofips as county_fips,
    stateabbrv as state,
    county as county_name,
    nri_ver as nri_version,
    population::bigint as population,
    buildvalue::double as building_value_usd,
    risk_score::double as risk_score,
    risk_ratng as risk_rating,
    eal_score::double as eal_score,
    eal_valb::double as eal_buildings_usd,
    alr_valb::double as building_loss_rate,
    sovi_score::double as social_vulnerability_score,
    resl_score::double as resilience_score,
    hrcn_ealb::double as hurricane_eal_buildings_usd,
    cfld_ealb::double as coastal_flood_eal_buildings_usd,
    ifld_ealb::double as inland_flood_eal_buildings_usd,
    wfir_ealb::double as wildfire_eal_buildings_usd
from {{ source('bronze', 'fema_nri__counties') }}
{{ latest_load() }}
