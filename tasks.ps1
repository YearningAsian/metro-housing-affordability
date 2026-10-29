# Task runner (no make on Windows). Usage: .\tasks.ps1 setup   or   .\tasks.ps1 ingest [source ...]
param([Parameter(Position = 0)][string]$Task = "help", [Parameter(ValueFromRemainingArguments)][string[]]$Rest)
$ErrorActionPreference = "Stop"

function Invoke-Native { & $args[0] $args[1..($args.Count - 1)]; if ($LASTEXITCODE) { throw "$($args -join ' ') failed" } }

switch ($Task) {
    "setup" {
        # x86-64 build on purpose: numba/LightGBM have no Windows ARM64 wheels
        $py = if ($IsWindows -or $env:OS -eq "Windows_NT") { "cpython-3.12-windows-x86_64-none" } else { "3.12" }
        Invoke-Native uv sync --python $py
        Invoke-Native uv run pre-commit install
        Invoke-Native uv run dbt deps --project-dir dbt --profiles-dir dbt
        if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created .env from .env.example; add your API keys." }
    }
    "lint" { Invoke-Native uv run pre-commit run --all-files }
    # dbt resolves data/ and config/ paths from the repo root
    "build" { Invoke-Native uv run dbt build --project-dir dbt --profiles-dir dbt }
    # build the dbt docs site and open it at http://localhost:8080
    "docs" { Invoke-Native uv run dbt docs generate --project-dir dbt --profiles-dir dbt; Invoke-Native uv run dbt docs serve --project-dir dbt --profiles-dir dbt }
    # download new source files into data/raw and data/bronze; skips what this month already has
    "ingest" { Invoke-Native uv run python -m ingest @Rest }
    "test" { Invoke-Native uv run pytest }
    default { Write-Host "Tasks: setup, lint, test, ingest [source ...], build, docs" }
}
