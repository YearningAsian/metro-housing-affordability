import json
from urllib.parse import urlencode

import pandas as pd

from ingest.base import BaseExtractor, File, load_env, metros

# 30-year mortgage rate (weekly) and CPI-U (monthly, SA); metro unemployment IDs live in config/metros.yml
NATIONAL = ["MORTGAGE30US", "CPIAUCSL"]


class FRED(BaseExtractor):
    source = "fred"

    def files(self):
        key = load_env("FRED_API_KEY")
        series = NATIONAL + [m["fred_unemployment_series"] for m in metros()]
        return [
            File(
                "observations",
                "https://api.stlouisfed.org/fred/series/observations?"
                + urlencode({"series_id": s, "file_type": "json", "api_key": key}),
                f"{s}.json",
                refresh=True,
            )
            for s in series
        ]

    def read(self, con, path, file):
        df = pd.DataFrame(json.loads(path.read_text(encoding="utf-8"))["observations"])
        df["series_id"] = path.stem
        return df
