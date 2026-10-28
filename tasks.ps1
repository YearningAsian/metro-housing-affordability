# Task runner (no make on Windows). Usage: .\tasks.ps1 setup
param([Parameter(Position = 0)][string]$Task = "help")
$ErrorActionPreference = "Stop"

function Invoke-Native { & $args[0] $args[1..($args.Count - 1)]; if ($LASTEXITCODE) { throw "$($args -join ' ') failed" } }

switch ($Task) {
    "setup" {
        # x86-64 build on purpose: numba/LightGBM have no Windows ARM64 wheels
        $py = if ($IsWindows -or $env:OS -eq "Windows_NT") { "cpython-3.12-windows-x86_64-none" } else { "3.12" }
        Invoke-Native uv sync --python $py
        Invoke-Native uv run pre-commit install
        if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "Created .env from .env.example; add your API keys." }
    }
    "lint" { Invoke-Native uv run pre-commit run --all-files }
    # dbt resolves data/ and config/ paths from the repo root
    "build" { Invoke-Native uv run dbt build --project-dir dbt --profiles-dir dbt }
    default { Write-Host "Tasks: setup, lint, build" }
}
