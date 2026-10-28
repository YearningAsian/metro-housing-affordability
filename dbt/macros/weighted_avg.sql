{# Average of value weighted by weight, over the rows where value is known. #}
{% macro weighted_avg(value, weight) -%}
    sum({{ value }} * {{ weight }}) / nullif(sum({{ weight }}) filter (where {{ value }} is not null), 0)
{%- endmacro %}
