# Illustration Extractor — Desktop Packaging Script
# Builds frontend, packages backend, and compiles Electron installer / portable exe

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  Illustration Extractor v2.0 — Packaging Build" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Build Frontend Production Assets
Write-Host "[1/3] Building Frontend production bundle..." -ForegroundColor Yellow
Push-Location "$root\frontend"
pnpm run build
Pop-Location
Write-Host "Frontend build complete." -ForegroundColor Green
Write-Host ""

# 2. Check Backend Environment
Write-Host "[2/3] Checking Backend Python environment..." -ForegroundColor Yellow
Push-Location "$root\backend"
uv sync
Pop-Location
Write-Host "Backend environment ready." -ForegroundColor Green
Write-Host ""

# 3. Package Electron Application
Write-Host "[3/3] Packaging Electron Desktop Application (Windows x64)..." -ForegroundColor Yellow
Push-Location "$root\apps\desktop"
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing desktop app dependencies..." -ForegroundColor Gray
    pnpm install
}
npx electron-builder --win --x64
Pop-Location

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  Packaging Complete!" -ForegroundColor Green
Write-Host "  Distribution output: $root\dist-desktop" -ForegroundColor Yellow
Write-Host "======================================================" -ForegroundColor Cyan
