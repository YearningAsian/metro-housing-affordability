from datetime import date

from ingest.base import BaseExtractor, File, lit, months

BASE = "https://www2.census.gov/econ/bps/County"
# County files only: they aggregate to 2023 CBSAs through dim_county and report value in dollars
# (the CBSA files use thousands and switch delineation in 2024).
GROUPS = [f"{t}{s}" for s in ("", "_rep") for t in ("u1", "u2", "u34", "u5p")]
COLUMNS = [
    "survey_date",
    "state_fips",
    "county_fips",
    "region_code",
    "division_code",
    "county_name",
] + [f"{g}_{m}" for g in GROUPS for m in ("bldgs", "units", "value")]


class BPS(BaseExtractor):
    source = "bps"
    # back-to-back requests get an HTML "Request Rejected" page from Census
    throttle = 0.5

    def files(self):
        today = date.today()
        monthly = [
            ("county_monthly", f"co{y % 100:02d}{m:02d}c.txt")
            for y, m in months((2015, 1), (today.year, today.month))
            if (y, m) != (2015, 4)
        ]
        # Census's firewall always rejects co1504c.txt; staging derives April 2015 as co1504y - co1503y
        monthly += [("county_ytd", "co1503y.txt"), ("county_ytd", "co1504y.txt")]
        # annual files carry late corrections the monthly files miss; same layout
        annual = [("county_annual", f"co{y}a.txt") for y in range(2015, today.year)]
        return [File(e, f"{BASE}/{n}", n, optional=True) for e, n in monthly + annual]

    def read(self, con, path, file):
        # two header rows and a blank line; county names are padded with spaces
        return con.sql(
            f"select * replace (trim(county_name) as county_name) from read_csv({lit(path.as_posix())}, skip = 3, "
            f"header = false, encoding = 'latin-1', all_varchar = true, names = {COLUMNS})"
        )
