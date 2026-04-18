# Quick check: is the Meal Plan API up on port 8000?
# Run from anywhere: powershell -ExecutionPolicy Bypass -File .\scripts\windows\check_api_health.ps1

$ErrorActionPreference = 'Stop'
$uri = 'http://127.0.0.1:8000/api/health'
try {
    $r = Invoke-WebRequest -Uri $uri -UseBasicParsing -TimeoutSec 8
    Write-Host "OK ($uri):" -ForegroundColor Green
    Write-Host $r.Content
    if ($r.Content -notmatch 'glocusense-meal-plan') {
        Write-Host "`nWarning: Response does not look like the Meal Plan API. Another app may be using port 8000." -ForegroundColor Yellow
    }
} catch {
    Write-Host "API not reachable at $uri" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host "`nFix: from repo root run: python backend\run.py  (or: python run.py)" -ForegroundColor Cyan
    Write-Host "If your path contains ';', use docs/guides/HOW_TO_RUN.md (SUBST)." -ForegroundColor Cyan
    exit 1
}
