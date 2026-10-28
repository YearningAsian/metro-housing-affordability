import json
from datetime import date

import pandas as pd

from ingest.base import BaseExtractor, File, load_env, metros

BASE = "https://www.huduser.gov/hudapi/public/fmr"


class HUDFMR(BaseExtractor):
    source = "hud_fmr"
    throttle = 1.0  # HUD rate-limits its API; the backfill is about 300 calls

    def files(self):
        self.headers = {"Authorization": f"Bearer {load_env('HUD_API_TOKEN')}"}
        areas = [a for m in metros() for a in m["hud_fmr_areas"]]
        # fiscal year Y starts 1 October of Y-1, so next year's FMRs appear in the autumn
        return [
            File("fmr", f"{BASE}/data/{a}?year={y}", f"{a}_{y}.json", optional=True)
            for y in range(2017, date.today().year + 2)
            for a in areas
        ]

    def read(self, con, path, file):
        data = json.loads(path.read_text(encoding="utf-8"))["data"]
        rows = data.pop("basicdata")
        # Small Area FMR areas list one row per ZIP plus "MSA level"; other areas return a single dict
        df = pd.DataFrame(rows if isinstance(rows, list) else [rows])
        for k, v in data.items():
            df[k] = v
        df["fmr_area_code"] = path.stem.rsplit("_", 1)[0]
        return df
