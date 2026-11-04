from ingest.acs import ACS
from ingest.bps import BPS
from ingest.census_geo import CensusGeo
from ingest.fema_nri import FEMANRI
from ingest.fred import FRED
from ingest.hud_crosswalk import HUDCrosswalk
from ingest.hud_fmr import HUDFMR
from ingest.irs_migration import IRSMigration
from ingest.qcew import QCEW
from ingest.realtor import Realtor
from ingest.redfin import Redfin
from ingest.zillow import Zillow

EXTRACTORS = {
    e.source: e
    for e in (
        Zillow,
        Redfin,
        BPS,
        ACS,
        QCEW,
        FRED,
        IRSMigration,
        HUDFMR,
        HUDCrosswalk,
        CensusGeo,
        FEMANRI,
        Realtor,
    )
}
