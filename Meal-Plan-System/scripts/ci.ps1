# Meal-Plan-System — local CI (pytest + frontend build)
# Run from repo root Meal-Plan-System/:  .\scripts\ci.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

Write-Host "=== Meal-Plan-System CI ===" -ForegroundColor Green

Write-Host "`n[1/2] Backend: pytest..." -ForegroundColor Cyan
python -m pytest backend/tests -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n[2/2] Frontend: npm ci + build..." -ForegroundColor Cyan
Push-Location (Join-Path $Root "frontend")
npm ci
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
npm run build
$buildExit = $LASTEXITCODE
Pop-Location
if ($buildExit -ne 0) { exit $buildExit }

Write-Host "`nOK - same checks as .github/workflows/meal-plan-ci.yml" -ForegroundColor Green
