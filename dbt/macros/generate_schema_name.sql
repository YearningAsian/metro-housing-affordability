{# Build into the configured schema as is (silver, gold, ml); dbt's default would prefix it with main_. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ (custom_schema_name or target.schema) | trim }}
{%- endmacro %}
