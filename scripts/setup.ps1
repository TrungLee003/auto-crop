# Illustration Extractor — First-Time Setup
# Installs all dependencies for backend and frontend

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "=== Illustration Extractor — Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "[Check] Python..." -ForegroundColor Yellow
python --version
Write-Host "[Check] Node.js..." -ForegroundColor Yellow
node --version
Write-Host "[Check] pnpm..." -ForegroundColor Yellow
pnpm --version
Write-Host "[Check] uv..." -ForegroundColor Yellow
uv --version
Write-Host ""

# Backend setup
Write-Host "[Backend] Installing Python dependencies..." -ForegroundColor Yellow
Push-Location "$root\backend"
uv sync
Pop-Location
Write-Host "[Backend] Done." -ForegroundColor Green
Write-Host ""

# Frontend setup
Write-Host "[Frontend] Installing Node dependencies..." -ForegroundColor Yellow
Push-Location "$root\frontend"
pnpm install
Pop-Location
Write-Host "[Frontend] Done." -ForegroundColor Green
Write-Host ""

Write-Host "=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "Run .\scripts\dev.ps1 to start development servers." -ForegroundColor Gray
