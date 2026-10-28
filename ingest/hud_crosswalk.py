import json

import pandas as pd

from ingest.base import BaseExtractor, File, load_env

BASE = "https://www.huduser.gov/hudapi/public/usps"


class HUDCrosswalk(BaseExtractor):
    source = "hud_crosswalk"

    def files(self):
        self.headers = {"Authorization": f"Bearer {load_env('HUD_API_TOKEN')}"}
        # latest quarter only; type 2 = ZIP to county, 3 = ZIP to CBSA
        return [
            File(e, f"{BASE}?type={t}&query=All", f"{e}.json", refresh=True)
            for e, t in (("zip_county", 2), ("zip_cbsa", 3))
        ]

    def read(self, con, path, file):
        data = json.loads(path.read_text(encoding="utf-8"))["data"]
        df = pd.DataFrame(data["results"])
        df["year"], df["quarter"] = data["year"], data["quarter"]
        return df
