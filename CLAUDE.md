# Metro Housing Affordability

- The project plan lives in `docs/PROJECT_PLAN.md`. Read it before starting any work.
- Work one phase at a time, in order. Don't start the next phase until the user says so.
- When a task in the plan is done, tick its checkbox (`- [ ]` → `- [x]`) in `docs/PROJECT_PLAN.md`.
- Stack: Python 3.12, DuckDB, dbt-duckdb, GitHub Actions; ML later with LightGBM, statsforecast, SHAP and MLflow.
- Never commit API keys or the `.env` file. Never commit raw data; it goes under `data/`, which is git-ignored.
- The user is on Windows: give commands that work in PowerShell, or say when something needs WSL.
- Ask before deleting files or installing anything system-wide.
- The venv is x86-64 Python 3.12 on an ARM64 machine, because numba/LightGBM lack Windows ARM64 wheels. Polars' x64 build fails its CPU check under emulation, so use pandas.
- This is a public repo.
