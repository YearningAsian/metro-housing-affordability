from ingest.base import BaseExtractor, File

# Redfin moved its feed here in 2026; redfin_market_tracker/ stopped on 2026-06-02 and now returns 403.
BASE = "https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_data_center/housing_market/monthly"


class Redfin(BaseExtractor):
    source = "redfin"

    def files(self):
        # housing_market is all residential; property_types/ has no all-residential rows. all_zips.csv is about 1.3 GB
        return [
            File(e, f"{BASE}/all_{e}.csv", f"all_{e}.csv", refresh=True)
            for e in ("metros", "zips")
        ]
