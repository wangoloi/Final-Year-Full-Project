# Quick check: is the Meal Plan API up on port 8001? (default for python run.py)
# Run from anywhere: powershell -ExecutionPolicy Bypass -File .\scripts\windows\check_api_health.ps1

$ErrorActionPreference = 'Stop'
$uri = 'http://127.0.0.1:8001/api/health'
try {
    $r = Invoke-WebRequest -Uri $uri -UseBasicParsing -TimeoutSec 8
    Write-Host "OK ($uri):" -ForegroundColor Green
    Write-Host $r.Content
    if ($r.Content -notmatch 'glocusense-meal-plan') {
        Write-Host "`nWarning: Response does not look like the Meal Plan API. Another app may be using port 8001." -ForegroundColor Yellow
    }
} catch {
    Write-Host "API not reachable at $uri" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host "`nFix: from repo root run: python backend\run.py  (default PORT=8001)" -ForegroundColor Cyan
    Write-Host "If your path contains ';', use docs/guides/HOW_TO_RUN.md (SUBST)." -ForegroundColor Cyan
    exit 1
}
