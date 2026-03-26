<#
.SYNOPSIS
  Full integrated stack: GlucoSense (FastAPI :8000 + portal), Meal Plan API (:8001), Meal Plan Vite (:5175).

.DESCRIPTION
  Frees ports 8000, 8001, 5173, 5174, 5175; opens THREE PowerShell windows with clear titles.
  MAIN APP (landing, clinician workspace): GlucoSense Vite - usually http://localhost:5173
  Meal Plan :5175 is only for the embedded iframe - open GlucoSense first.

.NOTES
  Paths with ';' break if passed inside -Command; this script uses -WorkingDirectory instead.

  From project root:
    powershell -ExecutionPolicy Bypass -File ".\scripts\start-integrated.ps1"
#>

$ErrorActionPreference = 'Continue'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$GlucoRoot = Join-Path $ProjectRoot 'Clinical-Insulin-Recommendation'
$GlucoFront = Join-Path $GlucoRoot 'frontend'
$MealRoot = Join-Path $ProjectRoot 'Meal-Plan-System'
$MealFront = Join-Path $MealRoot 'frontend'
$MealBackend = Join-Path $MealRoot 'backend'

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }

if (-not (Test-Path -LiteralPath $GlucoFront)) {
  Write-Error "GlucoSense frontend not found: $GlucoFront"
  exit 1
}
if (-not (Test-Path -LiteralPath $MealFront)) {
  Write-Error "Meal Plan frontend not found: $MealFront"
  exit 1
}
if (-not (Test-Path -LiteralPath (Join-Path $MealBackend 'run.py'))) {
  Write-Error "Meal Plan backend not found: $MealBackend\run.py"
  exit 1
}

Write-Step "Freeing ports 8000, 8001, 5173, 5174, 5175 (best effort; times out so VS Code is not stuck)"
$killPortsJob = Start-Job -ScriptBlock {
  foreach ($port in 8000, 8001, 5173, 5174, 5175) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
      ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
  }
}
$null = Wait-Job $killPortsJob -Timeout 6
Stop-Job $killPortsJob -ErrorAction SilentlyContinue
Remove-Job $killPortsJob -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

$envExample = Join-Path $GlucoFront '.env.example'
$envFile = Join-Path $GlucoFront '.env'
if (-not (Test-Path -LiteralPath $envFile) -and (Test-Path -LiteralPath $envExample)) {
  Write-Step "Creating GlucoSense frontend .env from .env.example"
  Copy-Item -LiteralPath $envExample -Destination $envFile
}

function Start-StackWindow {
  param(
    [string]$Title,
    [string]$WorkingDir,
    [string]$CommandLine
  )
  # Do not embed $WorkingDir in the -Command script: ';' in paths like 'year3;2' breaks parsing.
  $inner = @"
`$Host.UI.RawUI.WindowTitle = '$Title'
Write-Host ''
Write-Host '=== $Title ===' -ForegroundColor Cyan
Write-Host '(cwd is set by the launcher - path with semicolons is not echoed to avoid parse errors)'
Write-Host ''
$CommandLine
"@
  Start-Process -FilePath 'powershell.exe' -WorkingDirectory $WorkingDir -ArgumentList @(
    '-NoExit',
    '-NoLogo',
    '-ExecutionPolicy', 'Bypass',
    '-Command',
    $inner
  ) | Out-Null
}

Write-Step "Window 1/3: Meal Plan API on :8001 (Python)"
Start-StackWindow -Title 'Meal Plan API :8001' -WorkingDir $MealBackend -CommandLine @'
$env:PORT = '8001'
python run.py
'@

Start-Sleep -Seconds 3

Write-Step "Window 2/3: GlucoSense - clinical API :8000 + MAIN PORTAL (npm run start)"
Start-StackWindow -Title 'GlucoSense: MAIN APP (portal + API)' -WorkingDir $GlucoFront -CommandLine @'
$env:NODE_OPTIONS = '--max-old-space-size=6144'
npm run start
'@

Start-Sleep -Seconds 2

Write-Step "Window 3/3: Meal Plan Vite on :5175 (for iframe only)"
Start-StackWindow -Title 'Meal Plan UI :5175 (iframe target)' -WorkingDir $MealFront -CommandLine @'
$env:MEAL_PLAN_API_PROXY = 'http://127.0.0.1:8001'
node ./node_modules/vite/bin/vite.js --port 5175 --strictPort
'@

Write-Host ""
Write-Host "Three windows should be open. Use them in this order:" -ForegroundColor Green
Write-Host ""
Write-Host "  1) Wait for Meal Plan API: Uvicorn on :8001" -ForegroundColor White
Write-Host "  2) Wait for GlucoSense: Uvicorn :8000 AND Vite ready (usually :5173)" -ForegroundColor Yellow
Write-Host "  3) Wait for Meal Plan Vite on :5175" -ForegroundColor White
Write-Host ""
Write-Host "  >>> OPEN THIS IN YOUR BROWSER (main app, not meal-only):" -ForegroundColor Yellow
Write-Host "      http://localhost:5173   (or :5174 if GlucoSense says port in use)" -ForegroundColor Cyan
Write-Host ""
Write-Host "  http://localhost:5175 is ONLY the meal app for the iframe - do not use it as your main entry." -ForegroundColor DarkGray
Write-Host ""
Write-Host "  GlucoSense API docs: http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  Meal Plan API docs:   http://127.0.0.1:8001/docs" -ForegroundColor White
Write-Host ""
Write-Host "GlucoSense frontend/.env should include:" -ForegroundColor Yellow
Write-Host "  VITE_MEAL_PLAN_URL=http://localhost:5175" -ForegroundColor Gray
Write-Host "  VITE_MEAL_PLAN_API_URL=http://127.0.0.1:8001" -ForegroundColor Gray
Write-Host ""
