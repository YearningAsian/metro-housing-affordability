from ingest.base import BaseExtractor, File

BASE = "https://files.zillowstatic.com/research/public_csvs"
# Mid-tier ZHVI and ZORI, both seasonally adjusted and smoothed; ZIP and metro, wide (one column per month)
PATHS = {
    "zip_zhvi": "zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
    "metro_zhvi": "zhvi/Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
    "zip_zori": "zori/Zip_zori_uc_sfrcondomfr_sm_sa_month.csv",
    "metro_zori": "zori/Metro_zori_uc_sfrcondomfr_sm_sa_month.csv",
}


class Zillow(BaseExtractor):
    source = "zillow"

    def files(self):
        return [
            File(e, f"{BASE}/{p}", p.split("/")[1], refresh=True)
            for e, p in PATHS.items()
        ]
