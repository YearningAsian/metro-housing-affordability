{# Write the gold marts and the map geometry to <path> for the dashboard. Run after dbt build: .\tasks.ps1 export #}
{% macro export_marts(path='data/export') %}
    {% for mart in ['dim_metro', 'mart_metro_month', 'mart_zip_month', 'mart_migration_origins', 'mart_zip_forecast'] %}
        {% do run_query("copy " ~ ref(mart) ~ " to '" ~ path ~ "/" ~ mart ~ ".parquet' (format parquet)") %}
        {% do log("exported " ~ mart, info=true) %}
    {% endfor %}

    {# study ZIP outlines keyed by zip (one zcta per zip in dim_zip); 0.001 degrees (~100 m) keeps it near 3 MB #}
    {% do run_query(
        "copy (select z.zip, st_simplifypreservetopology(st_geomfromwkb(s.geom), 0.001) as geom
            from " ~ ref('dim_zip') ~ " as z
            inner join " ~ source('bronze', 'census_geo__zcta_shapes') ~ " as s on z.zcta = s.zcta5ce20)
        to '" ~ path ~ "/zip_shapes.geojson'
        with (format gdal, driver 'GeoJSON', layer_creation_options 'COORDINATE_PRECISION=4')"
    ) %}
    {% do log("exported zip_shapes", info=true) %}

    {# flow-map endpoints: every county and each study metro (the centroid of its counties) #}
    {% do run_query(
        "copy (
            select 'county' as kind, geoid as code, st_y(st_centroid(st_geomfromwkb(geom))) as lat,
                st_x(st_centroid(st_geomfromwkb(geom))) as lon
            from " ~ source('bronze', 'census_geo__county_shapes') ~ "
            union all
            select 'metro', d.cbsa_code, st_y(st_centroid(st_union_agg(st_geomfromwkb(s.geom)))),
                st_x(st_centroid(st_union_agg(st_geomfromwkb(s.geom))))
            from " ~ ref('dim_county') ~ " as d
            inner join " ~ source('bronze', 'census_geo__county_shapes') ~ " as s on d.county_fips = s.geoid
            where d.is_study_metro
            group by d.cbsa_code
        ) to '" ~ path ~ "/centroids.parquet' (format parquet)"
    ) %}
    {% do log("exported centroids", info=true) %}
{% endmacro %}
