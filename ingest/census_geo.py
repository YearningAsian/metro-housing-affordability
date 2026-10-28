from ingest.base import BaseExtractor, File, lit

DELINEATION = (
    "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/"
    "list1_2023.xlsx"
)
TIGER = "https://www2.census.gov/geo/tiger"
BOUNDARIES = {
    "cbsa_shapes": "GENZ2024/shp/cb_2024_us_cbsa_500k.zip",
    "county_shapes": "GENZ2024/shp/cb_2024_us_county_500k.zip",
    "zcta_shapes": "GENZ2020/shp/cb_2020_us_zcta520_500k.zip",  # the only ZCTA vintage
}


class CensusGeo(BaseExtractor):
    """CBSA delineation (July 2023) and cartographic boundaries: fixed vintages, fetched once."""

    source = "census_geo"

    def files(self):
        return [File("cbsa_delineation", DELINEATION, "list1_2023.xlsx")] + [
            File(e, f"{TIGER}/{p}", p.split("/")[-1]) for e, p in BOUNDARIES.items()
        ]

    def read(self, con, path, file):
        p = path.as_posix()
        if path.suffix == ".xlsx":
            con.sql("install excel; load excel")
            # header on row 3 under two title rows; stop at the blank row before the footnotes
            return con.sql(
                f"select * from read_xlsx({lit(p)}, range = 'A3:L5000', all_varchar = true, stop_at_empty = true)"
            )
        con.sql("install spatial; load spatial")
        # geometry kept as WKB; every other column text, like the rest of bronze
        return con.sql(
            f"select columns(* exclude (geom))::varchar, st_aswkb(geom) as geom "
            f"from st_read({lit(f'/vsizip/{p}/{path.stem}.shp')})"
        )
