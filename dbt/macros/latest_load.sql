{# Bronze keeps every monthly copy of a rolling file under the same name; keep only the newest copy of each file. #}
{% macro latest_load() -%}
    qualify _loaded_at = max(_loaded_at) over (partition by _source_file)
{%- endmacro %}
