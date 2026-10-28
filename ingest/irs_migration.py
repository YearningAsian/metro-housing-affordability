from datetime import date

from ingest.base import BaseExtractor, File, lit

BASE = "https://www.irs.gov/pub/irs-soi"


class IRSMigration(BaseExtractor):
    source = "irs_migration"

    def files(self):
        # county-to-county flows for filing-year pairs from 2014-15; the newest pair lags about two years
        names = [
            (d, f"county{d}{y % 100:02d}{(y + 1) % 100:02d}.csv")
            for y in range(2014, date.today().year)
            for d in ("inflow", "outflow")
        ]
        return [File(d, f"{BASE}/{n}", n, optional=True) for d, n in names]

    def read(self, con, path, file):
        return con.sql(
            f"select * from read_csv({lit(path.as_posix())}, encoding = 'latin-1', all_varchar = true)"
        )
