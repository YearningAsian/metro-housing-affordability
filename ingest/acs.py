import json
from datetime import date
from urllib.parse import urlencode

import pandas as pd

from ingest.base import BaseExtractor, File, load_env

# median household income, population, median gross rent, median gross rent as % of income
VARIABLES = "NAME,B19013_001E,B01003_001E,B25064_001E,B25071_001E"
GEOS = {
    "zcta": "zip code tabulation area:*",
    "county": "county:*",
    "cbsa": "metropolitan statistical area/micropolitan statistical area:*",
}


class ACS(BaseExtractor):
    source = "acs"

    def files(self):
        key = load_env("CENSUS_API_KEY")
        return [
            File(
                geo,
                f"https://api.census.gov/data/{y}/acs/acs5?{urlencode({'get': VARIABLES, 'for': clause, 'key': key})}",
                f"acs5_{y}_{geo}.json",
                optional=True,
            )
            # the 5-year vintage ending in Y comes out in December of Y+1
            for y in range(2015, date.today().year)
            for geo, clause in GEOS.items()
        ]

    def read(self, con, path, file):
        # array of arrays, header first
        rows = json.loads(path.read_text(encoding="utf-8"))
        df = pd.DataFrame(rows[1:], columns=rows[0])
        df["vintage"] = path.stem.split("_")[1]
        return df
