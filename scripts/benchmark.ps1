# Illustration Extractor — Detection Benchmark Runner
# Evaluates detection performance against historical document benchmark dataset

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  Illustration Extractor — Benchmark Evaluation" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

Push-Location "$root\backend"
$env:PYTHONIOENCODING = "utf-8"
uv run python ..\benchmark\run_benchmark.py
Pop-Location
