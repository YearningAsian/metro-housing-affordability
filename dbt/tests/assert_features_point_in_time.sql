-- Phase 11 done-when: no feature row uses a source release dated after its prediction date. A row here means a
-- feature leaked data the model could not have had when it predicted.
{% set sources = ['zillow', 'redfin', 'permits', 'mortgage', 'income', 'wages'] %}
select
    zip,
    month,
    prediction_date,
    {% for s in sources %}
        {{ s }}_available_on{% if not loop.last %},{% endif %}
    {% endfor %}
from {{ ref('features_zip_month') }}
where
    {% for s in sources %}
        {{ s }}_available_on > prediction_date{% if not loop.last %} or{% endif %}
    {% endfor %}
