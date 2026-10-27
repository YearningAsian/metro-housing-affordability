# Prompt for Claude Code

Open Claude Code in the folder where you want this project to live (an empty folder is fine), then paste everything below the line.

---

I'm starting a portfolio project: a multi-metro housing affordability pipeline with a dashboard, ML models and a presentation video. The full plan is in two files in my Downloads folder (`%USERPROFILE%\Downloads` on Windows):

- `PROJECT_PLAN.md` — the plan you'll work from
- `PROJECT_PLAN.html` — the same plan with diagrams, for me to read in a browser

**Step 1: Set up the project files**

1. Make sure we're in a git repo in this folder; if not, run `git init`.
2. Create a `docs/` folder and move both files from Downloads into it: `docs/PROJECT_PLAN.md` and `docs/PROJECT_PLAN.html`. Also move this prompt file, `CLAUDE_CODE_PROMPT.md`, into `docs/`.
3. Create a `CLAUDE.md` at the repo root that says:
   - The project plan lives in `docs/PROJECT_PLAN.md`. Read it before starting any work.
   - Work one phase at a time, in order. Don't start the next phase until I say so.
   - When a task in the plan is done, tick its checkbox (`- [ ]` → `- [x]`) in `docs/PROJECT_PLAN.md`.
   - Stack: Python 3.12, DuckDB, dbt-duckdb, GitHub Actions; ML later with LightGBM, statsforecast, SHAP and MLflow.
   - Never commit API keys or the `.env` file. Never commit raw data; it goes under `data/`, which is git-ignored.
   - I'm on Windows, so give commands that work in PowerShell, or say when something needs WSL.
   - Ask before deleting files or installing anything system-wide.

**Step 2: Do Phase 1 (Setup and planning)**

Read `docs/PROJECT_PLAN.md`, then do Phase 1:

- Create the folder structure: `ingest/`, `dbt/`, `notebooks/`, `ml/`, `dashboard/`, `docs/`, `config/` and `data/` (git-ignored).
- Set up a Python 3.12 environment with `uv` (or `venv` if uv isn't installed) and add the Phase 1 dependencies.
- Create `.env.example` with placeholders for `CENSUS_API_KEY`, `FRED_API_KEY` and `HUD_API_TOKEN`, and a `.gitignore` that excludes `.env`, `data/` and `*.duckdb`.
- Write `config/metros.yml` with the 11 metros and CBSA codes from the plan's Metros table.
- Write a README stub: the question, the metros, the data sources.
- Add pre-commit hooks for `ruff` and `sqlfluff`.
- Add a `Makefile` (or a `tasks.py` / PowerShell script if `make` isn't available) with a `setup` target.

API keys are the one thing I have to do myself. List the three sign-up pages from the plan's Data sources table so I can request them.

When Phase 1 is done, show me a short summary of what you created, tick the Phase 1 boxes in the plan, make the first git commit, and stop. Don't start Phase 2.
