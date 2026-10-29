{#
    First day a 5-year ACS vintage can be used: the Census publishes vintage V in December of V+1, except 2016-2020,
    which COVID delayed to 17 March 2022.
#}
{% macro acs_available_on(vintage) -%}
    case when {{ vintage }} = 2020 then date '2022-04-01' else make_date({{ vintage }} + 2, 1, 1) end
{%- endmacro %}
