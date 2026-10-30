-- One row per ZIP and scored month: the monthly model's 12-month forecast and hot-ZIP flag (ml.predictions), with the
-- ZIP's home value then and, once 12 months have passed, what actually happened. A view, so scores written by
-- ml/train.py after dbt build show up without another dbt run.
{{ config(materialized='view') }}

select
    p.zip,
    p.cbsa_code,
    p.month,
    p.prediction_date,
    f.zhvi_usd,
    p.growth_pred,
    p.growth_lo,
    p.growth_hi,
    f.zhvi_usd * (1 + p.growth_pred) as zhvi_pred_usd,
    p.hot_score,
    p.hot_rank_pct,
    p.hot_flag,
    f.target_growth_12m as actual_growth_12m,
    f.target_top20 as actual_top20,
    p.run_date,
    p.model_version,
    p.mlflow_run_id
from {{ source('ml', 'predictions') }} as p
left join {{ ref('features_zip_month') }} as f on p.zip = f.zip and p.month = f.month
