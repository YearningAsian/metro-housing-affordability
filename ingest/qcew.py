from datetime import date

from ingest.base import BaseExtractor, File


class QCEW(BaseExtractor):
    source = "qcew"

    def files(self):
        # Industry 10 (all industries), every area and ownership; one CSV per quarter.
        # shortcut: a quarter is fetched once, so later BLS revisions are missed; re-pull recent quarters if they matter.
        today = date.today()
        quarters = [
            (y, q)
            for y in range(2015, today.year + 1)
            for q in range(1, 5)
            if (y, q) <= (today.year, (today.month + 2) // 3)
        ]
        return [
            File(
                "industry_10",
                f"https://data.bls.gov/cew/data/api/{y}/{q}/industry/10.csv",
                f"{y}_q{q}_industry_10.csv",
                optional=True,
            )
            for y, q in quarters
        ]
