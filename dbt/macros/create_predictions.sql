{# ml.predictions is written by ml/train.py after dbt build; creating it empty here lets mart_zip_forecast (a view)
   build on the first run, before any scores exist. Runs on every dbt invocation (on-run-start). #}
{% macro create_predictions() %}
    create schema if not exists ml;
    create table if not exists ml.predictions (
        zip varchar,
        cbsa_code varchar,
        month date,
        prediction_date date,
        growth_pred double,
        growth_lo double,
        growth_hi double,
        hot_score double,
        hot_rank_pct double,
        hot_flag boolean,
        run_date date,
        model_version varchar,
        mlflow_run_id varchar
    )
{% endmacro %}
