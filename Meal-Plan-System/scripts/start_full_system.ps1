# Glocusense (Meal Plan) — API + React dev servers
# Run: .\scripts\start_full_system.ps1  (from repo root, or from anywhere)
# FastAPI: run.py → port 8000 | Vite: frontend → port 5173

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

Write-Host "=== Glocusense (Meal Plan) ===" -ForegroundColor Green

Write-Host "`n[1/3] Python dependencies..." -ForegroundColor Cyan
python -m pip install -r (Join-Path $Root "backend\requirements.txt") -q

Write-Host "[2/3] Frontend dependencies..." -ForegroundColor Cyan
Push-Location (Join-Path $Root "frontend")
if (-not (Test-Path "node_modules")) {
    npm install
}
Pop-Location

Write-Host "[3/3] Starting API (8000) and frontend (5173)..." -ForegroundColor Cyan
Write-Host "Open: http://localhost:5173  |  API docs: http://127.0.0.1:8000/docs" -ForegroundColor Yellow
Write-Host "Press Ctrl+C in each window to stop.`n" -ForegroundColor Gray

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location -LiteralPath '$Root'; python backend\run.py"
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location -LiteralPath '$Root\frontend'; npm run dev"
