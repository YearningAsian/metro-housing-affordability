import zipfile

import pandas as pd

from ingest.base import BaseExtractor, File

# OpenFEMA hosts the NRI since hazards.fema.gov was retired; the path names the release (v1.20, December 2025)
URL = "https://www.fema.gov/about/reports-and-data/openfema/nri/v120/NRI_Table_Counties.zip"


class FEMANRI(BaseExtractor):
    """FEMA National Risk Index by county: one fixed release, fetched once."""

    source = "fema_nri"

    def files(self):
        # fema.gov answered 403 to the generic User-Agent run() sets, then loaded with this one on 4 Nov 2026 and
        # refused it again on 5 Nov. shortcut: a fixed release loads once, so the pushed state spares CI the fetch;
        # a rebuild without that state may need a retry from another network
        self.headers = {
            "User-Agent": "metro-housing-affordability (+https://github.com/YearningAsian/metro-housing-affordability)"
        }
        return [File("counties", URL, "NRI_Table_Counties.zip")]

    def read(self, con, path, file):
        # the zip also holds a PDF and the data dictionary; utf-8-sig drops the BOM on the first header
        with zipfile.ZipFile(path) as z, z.open("NRI_Table_Counties.csv") as f:
            return pd.read_csv(f, dtype=str, encoding="utf-8-sig")
