{# Write the gold marts and the map geometry to <path> for the dashboard. Run after dbt build: .\tasks.ps1 export #}
{% macro export_marts(path='data/export') %}
    {% set marts = [
        'dim_metro', 'dim_zip', 'mart_metro_month', 'mart_zip_month', 'mart_migration_origins', 'mart_zip_forecast'
    ] %}
    {% for mart in marts %}
        {# about a quarter of study ZIPs (PO boxes, tiny places) never get a Zillow value; the dashboard has no
           use for them #}
        {% set priced = "select zip from " ~ ref(mart) ~ " where zhvi_usd is not null" %}
        {% set rows = "(select * from " ~ ref(mart) ~ " where zip in (" ~ priced ~ "))"
            if mart == 'mart_zip_month' else ref(mart) %}
        {% do run_query("copy " ~ rows ~ " to '" ~ path ~ "/" ~ mart ~ ".parquet' (format parquet)") %}
        {% do log("exported " ~ mart, info=true) %}
    {% endfor %}

    {# each study metro's ACS 1-year income brackets, for the findings page's share who can afford the typical home #}
    {% do run_query(
        "copy (
            select cbsa_code, acs_vintage, households_by_income
            from " ~ ref('fct_income') ~ "
            where geo_level = 'metro'
        ) to '" ~ path ~ "/metro_income_brackets.parquet' (format parquet)"
    ) %}
    {% do log("exported metro_income_brackets", info=true) %}

    {# the neighborhood types from ml/clusters.py, which is rerun by hand, not monthly; skipped if it never ran #}
    {% if adapter.get_relation(database=target.database, schema='ml', identifier='zip_clusters') %}
        {% do run_query(
            "copy (select zip, cbsa_code, window_end, cluster, cluster_name from ml.zip_clusters)
            to '" ~ path ~ "/zip_clusters.parquet' (format parquet)"
        ) %}
        {% do log("exported zip_clusters", info=true) %}
    {% endif %}

    {# each ZIP's SHAP values for the latest hot-ZIP scores, written by ml/train.py; skipped before its first run #}
    {% if adapter.get_relation(database=target.database, schema='ml', identifier='hot_zip_reasons') %}
        {% do run_query(
            "copy (select * from ml.hot_zip_reasons) to '" ~ path ~ "/hot_zip_reasons.parquet' (format parquet)"
        ) %}
        {% do log("exported hot_zip_reasons", info=true) %}
    {% endif %}

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
