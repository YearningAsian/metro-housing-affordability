# Task runner (no make on Windows). Usage: .\tasks.ps1 setup   or   .\tasks.ps1 ingest [source ...]
param([Parameter(Position = 0)][string]$Task = "help", [Parameter(ValueFromRemainingArguments)][string[]]$Rest)
$ErrorActionPreference = "Stop"

function Invoke-Native { & $args[0] $args[1..($args.Count - 1)]; if ($LASTEXITCODE) { throw "$($args -join ' ') failed" } }

# dbt resolves data/ and config/ paths from the repo root
$dbt = "--project-dir", "dbt", "--profiles-dir", "dbt"

function Export-Marts { New-Item -ItemType Directory -Force data/export | Out-Null; Invoke-Native uv run dbt run-operation export_marts @dbt }

# aws s3 against the Cloudflare R2 bucket, written r2:/path; reads R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
# R2_ENDPOINT_URL and R2_BUCKET from the environment (CI secrets) or .env
function Invoke-R2 {
    if (Test-Path .env) {
        foreach ($line in Get-Content .env) {
            if ($line -match '^\s*(R2_\w+)\s*=\s*(.+)$' -and -not (Test-Path "env:$($Matches[1])")) {
                Set-Item "env:$($Matches[1])" $Matches[2].Trim().Trim("'`"")
            }
        }
    }
    foreach ($name in "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_ENDPOINT_URL", "R2_BUCKET") {
        if (-not [Environment]::GetEnvironmentVariable($name)) { throw "$name not set in the environment or .env" }
    }
    $env:AWS_ACCESS_KEY_ID = $env:R2_ACCESS_KEY_ID
    $env:AWS_SECRET_ACCESS_KEY = $env:R2_SECRET_ACCESS_KEY
    $env:AWS_ENDPOINT_URL = $env:R2_ENDPOINT_URL
    $env:AWS_DEFAULT_REGION = "auto"
    # R2 rejects the checksums newer AWS clients send by default
    $env:AWS_REQUEST_CHECKSUM_CALCULATION = "when_required"
    $env:AWS_RESPONSE_CHECKSUM_VALIDATION = "when_required"
    $a = $args -replace '^r2:', "s3://$env:R2_BUCKET"
    Invoke-Native uvx --from awscli==1.46.1 aws s3 @a --only-show-errors
}

switch ($Task) {
    "setup" {
        # x86-64 build on purpose: numba/LightGBM have no Windows ARM64 wheels
        $py = if ($IsWindows -or $env:OS -eq "Windows_NT") { "cpython-3.12-windows-x86_64-none" } else { "3.12" }
        Invoke-Native uv sync --python $py
        Invoke-Native uv run pre-commit install
        Invoke-Native uv run dbt deps @dbt
        if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created .env from .env.example; add your API keys." }
    }
    "lint" { Invoke-Native uv run pre-commit run --all-files }
    "build" { Invoke-Native uv run dbt build @dbt }
    # build the dbt docs site and open it at http://localhost:8080
    "docs" { Invoke-Native uv run dbt docs generate @dbt; Invoke-Native uv run dbt docs serve @dbt }
    # download new source files into data/raw and data/bronze; skips what this month already has
    "ingest" { Invoke-Native uv run python -m ingest @Rest }
    # write the gold marts to data/export/*.parquet
    "export" { Export-Marts }
    # the monthly run: ingest, build and test, export
    "pipeline" {
        Invoke-Native uv run python -m ingest
        # --full-refresh: rebuild incremental models in full, since sources restate past months
        Invoke-Native uv run dbt build --full-refresh @dbt
        Export-Marts
    }
    # the state the pipeline keeps between runs: the load log in warehouse.duckdb and every bronze load. Raw
    # downloads are not kept; bronze holds their content. pull-state overwrites the local warehouse.
    "pull-state" {
        Invoke-R2 sync r2:/bronze data/bronze
        Invoke-R2 cp r2:/warehouse.duckdb data/warehouse.duckdb
        # the pulled bronze views point at the pushing machine's paths; census_geo is fetched once, so this run
        # downloads nothing and only rebuilds the views
        Invoke-Native uv run python -m ingest census_geo
    }
    # no --delete: a bronze load is never removed from the bucket
    # shortcut: every monthly copy of a rolling file is kept (about 450 MB a month, mostly Redfin and Zillow ZIPs);
    # prune superseded copies before the bucket nears R2's 10 GB free tier
    "push-state" {
        Invoke-R2 sync data/bronze r2:/bronze
        Invoke-R2 cp data/warehouse.duckdb r2:/warehouse.duckdb
        if (Test-Path data/export) { Invoke-R2 sync data/export r2:/export }
    }
    "test" { Invoke-Native uv run pytest }
    default { Write-Host "Tasks: setup, lint, test, ingest [source ...], build, export, pipeline, pull-state, push-state, docs" }
}
