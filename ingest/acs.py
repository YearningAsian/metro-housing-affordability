import json
from datetime import date
from urllib.parse import urlencode

import pandas as pd

from ingest.base import BaseExtractor, File, load_env

# median household income, population, median gross rent, median gross rent as % of income, median owner home
# value, median real estate taxes paid, and households in the 16 income brackets (B19001_002E to _017E)
VARIABLES = (
    "NAME,B19013_001E,B01003_001E,B25064_001E,B25071_001E,B25077_001E,B25103_001E,"
    + ",".join(f"B19001_{i:03d}E" for i in range(2, 18))
)
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
        ] + [
            # 1-year estimates by CBSA, fresher and single-year, for the metro grain; year Y comes out in September
            # of Y+1, and 2020 was never released in the standard tables (404, skipped as optional)
            File(
                "cbsa_1yr",
                f"https://api.census.gov/data/{y}/acs/acs1?{urlencode({'get': VARIABLES, 'for': GEOS['cbsa'], 'key': key})}",
                f"acs1_{y}_cbsa.json",
                optional=True,
            )
            for y in range(2015, date.today().year)
        ]

    def read(self, con, path, file):
        # array of arrays, header first
        rows = json.loads(path.read_text(encoding="utf-8"))
        df = pd.DataFrame(rows[1:], columns=rows[0])
        df["vintage"] = path.stem.split("_")[1]
        return df
