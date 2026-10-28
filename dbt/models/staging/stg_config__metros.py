import pandas as pd
import yaml


def model(dbt, session):
    # Python models cannot be views, the staging default
    dbt.config(materialized="table")
    # config/metros.yml stays the one place to add a metro; dbt runs from the repo root
    with open("config/metros.yml", encoding="utf-8") as f:
        metros = pd.DataFrame(yaml.safe_load(f)["metros"])
    metros["redfin_table_ids"] = metros["redfin_table_ids"].map(
        lambda ids: [str(i) for i in ids]
    )
    return metros
