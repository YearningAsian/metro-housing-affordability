{#
    Body of mart_metro_month and mart_zip_month: the int_spine rows of one geo_level with every int_ model's
    columns, the national series and the derived metrics. key names the place column (cbsa_code or zip).
#}
-- sqlfluff misreads the indentation of jinja blocks inside this macro's select list
-- noqa: disable=LT02
{% macro place_month(geo_level, key) -%}
{% set yoy = {
    'zhvi_usd': 'zhvi_yoy_growth',
    'zori_usd': 'zori_yoy_growth',
    'avg_weekly_wage_usd': 'avg_weekly_wage_yoy_growth',
    'employment': 'employment_yoy_growth',
} %}
{% set ints = ['int_prices', 'int_rents', 'int_supply', 'int_wages', 'int_migration', 'int_income'] %}
with national as (
    select
        month,
        any_value(value) filter (where series_id = 'MORTGAGE30US') as mortgage_rate_pct,
        any_value(value) filter (where series_id = 'CPIAUCSL') as cpi
    from {{ ref('fct_economy') }}
    where cbsa_code is null
    group by month
),

joined as (
    select
        s.geo_code as {{ key }},
        {% if key != 'cbsa_code' %}
            s.cbsa_code,
        {% endif %}
        s.month,
        {% for m in ints %}
            {{ m }}.* exclude (geo_level, geo_code, month),
        {% endfor %}
        n.mortgage_rate_pct,
        n.cpi
    from {{ ref('int_spine') }} as s
    {% for m in ints %}
        left join {{ ref(m) }} as {{ m }}
            on s.geo_level = {{ m }}.geo_level and s.geo_code = {{ m }}.geo_code and s.month = {{ m }}.month
    {% endfor %}
    left join national as n on s.month = n.month
    where s.geo_level = '{{ geo_level }}'
)

select
    *,
    zhvi_usd / median_household_income_usd as price_to_income,
    -- monthly rent over a month of the average weekly wage
    zori_usd / (avg_weekly_wage_usd * 52 / 12) as rent_to_wage,
    {% for col, name in yoy.items() %}
        {{ col }} / lag({{ col }}, 12) over (partition by {{ key }} order by month) - 1 as {{ name }}
        {%- if not loop.last %},{% endif %}
    {% endfor %}
from joined
{%- endmacro %}
