{# Write each gold mart to <path>/<mart>.parquet for the dashboard. Run after dbt build: .\tasks.ps1 export #}
{% macro export_marts(path='data/export') %}
    {% for mart in ['mart_metro_month', 'mart_zip_month', 'mart_migration_origins'] %}
        {% do run_query("copy " ~ ref(mart) ~ " to '" ~ path ~ "/" ~ mart ~ ".parquet' (format parquet)") %}
        {% do log("exported " ~ mart, info=true) %}
    {% endfor %}
{% endmacro %}
