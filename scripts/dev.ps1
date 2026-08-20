# Illustration Extractor — Development Server Launcher
# Starts both backend (FastAPI) and frontend (Vite) servers

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "=== Illustration Extractor — Dev Mode ===" -ForegroundColor Cyan
Write-Host ""

# Start backend
Write-Host "[Backend] Starting FastAPI on http://127.0.0.1:8000 ..." -ForegroundColor Yellow
$backend = Start-Process -FilePath "uv" `
    -ArgumentList "run", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory "$root\backend" `
    -PassThru -NoNewWindow

Start-Sleep -Seconds 2

# Start frontend
Write-Host "[Frontend] Starting Vite on http://127.0.0.1:5173 ..." -ForegroundColor Yellow
$frontend = Start-Process -FilePath "pnpm" `
    -ArgumentList "dev" `
    -WorkingDirectory "$root\frontend" `
    -PassThru -NoNewWindow

Write-Host ""
Write-Host "Both servers running. Press Ctrl+C to stop." -ForegroundColor Green
Write-Host "  Backend:  http://127.0.0.1:8000/api/v2/health" -ForegroundColor Gray
Write-Host "  Frontend: http://127.0.0.1:5173" -ForegroundColor Gray
Write-Host ""

try {
    Wait-Process -Id $backend.Id, $frontend.Id
}
finally {
    Write-Host "Stopping servers..." -ForegroundColor Yellow
    Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $frontend.Id -ErrorAction SilentlyContinue
}
