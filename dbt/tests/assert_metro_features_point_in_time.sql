-- As assert_features_point_in_time, for the metro feature table.
{% set sources = ['zillow', 'mortgage', 'realtor'] %}
select
    cbsa_code,
    month,
    prediction_date,
    {% for s in sources %}
        {{ s }}_available_on{% if not loop.last %},{% endif %}
    {% endfor %}
from {{ ref('features_metro_month') }}
where
    {% for s in sources %}
        {{ s }}_available_on > prediction_date{% if not loop.last %} or{% endif %}
    {% endfor %}
