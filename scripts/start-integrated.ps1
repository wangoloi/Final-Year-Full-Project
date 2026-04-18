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

function Stop-ListenOnPort {
  param([int]$Port)
  try {
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
      ForEach-Object { taskkill /PID $_.OwningProcess /F /T | Out-Null }
  } catch {}
}
$DesiredPorts = @{
  MealApi = 8001
  GlucoApi = 8000
  GlucoWeb = 5173
  MealWeb = 5175
}

function Test-PortBindable {
  param([int]$Port)
  try {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
    $listener.Start()
    $listener.Stop()
    return $true
  } catch {
    return $false
  }
}

function Test-PortBindableAny {
  param([int]$Port)
  try {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, $Port)
    $listener.Start()
    $listener.Stop()
    return $true
  } catch {
    return $false
  }
}

function Assert-PortFree {
  param(
    [int]$Port,
    [string]$Label
  )
  if (-not (Test-PortBindable -Port $Port)) {
    throw "$Label port :$Port is still in use after cleanup. Reboot Windows or stop the conflicting listener, then rerun .\scripts\start-integrated.ps1."
  }
}

function Get-HttpStatus {
  param(
    [string]$Url
  )
  try {
    $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 4
    return @{ ok = $true; status = [int]$resp.StatusCode; content = [string]$resp.Content }
  } catch {
    $webResp = $_.Exception.Response
    if ($null -ne $webResp) {
      try {
        $statusCode = [int]$webResp.StatusCode
      } catch {
        $statusCode = 0
      }
      return @{ ok = $false; status = $statusCode; content = "" }
    }
    return @{ ok = $false; status = 0; content = "" }
  }
}

function Get-PrimaryIPv4 {
  return Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notmatch '^127\.' -and $_.PrefixOrigin -ne 'WellKnown' } |
    Select-Object -ExpandProperty IPAddress -First 1
}

function Get-PortOccupantKind {
  param(
    [int]$Port,
    [string]$ApiHost = '127.0.0.1'
  )
  switch ($Port) {
    8000 {
      $resp = Get-HttpStatus -Url "http://${ApiHost}:$Port/api/health/ready"
      if ($resp.status -in @(200, 503)) { return 'gluco-api' }
      $openapi = Get-HttpStatus -Url "http://${ApiHost}:$Port/openapi.json"
      if ($openapi.status -eq 200 -and $openapi.content -match 'GlucoSense Clinical Support API') { return 'gluco-api' }
      return 'unknown'
    }
    8001 {
      $resp = Get-HttpStatus -Url "http://${ApiHost}:$Port/health/ready"
      if ($resp.status -in @(200, 503)) { return 'meal-api' }
      $apiHealth = Get-HttpStatus -Url "http://${ApiHost}:$Port/api/health"
      if ($apiHealth.status -eq 200 -and $apiHealth.content -match 'glocusense-meal-plan') { return 'meal-api' }
      $openapi = Get-HttpStatus -Url "http://${ApiHost}:$Port/openapi.json"
      if ($openapi.status -eq 200 -and $openapi.content -match 'GlucoSense Clinical Support API') { return 'gluco-api' }
      if ($openapi.status -eq 200 -and $openapi.content -match '"title":"Glocusense API"') { return 'meal-api' }
      return 'unknown'
    }
    5173 { return 'gluco-web' }
    5175 { return 'meal-web' }
    default { return 'unknown' }
  }
}

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

<<<<<<< HEAD
Write-Step "Freeing ports 8000, 8001, 5173, 5174, 5175 (best effort; times out so VS Code is not stuck)"
$killPortsJob = Start-Job -ScriptBlock {
  foreach ($port in 8000, 8001, 5173, 5174, 5175) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
      ForEach-Object { taskkill /PID $_.OwningProcess /F /T | Out-Null }
  }
=======
Write-Step "Freeing ports 8000, 8001, 5173, 5174, 5175 (netstat + taskkill; avoids Get-NetTCPConnection hangs on some Windows builds)"
$freePortsScript = Join-Path $PSScriptRoot 'free-dev-ports.ps1'
if (Test-Path -LiteralPath $freePortsScript) {
  & $freePortsScript
}
else {
  Write-Warning "Port-free script not found: $freePortsScript - you may need to close old dev servers manually."
>>>>>>> b6816fd33938d1f6eb4b13b3b7093ccb1d6508fa
}
Start-Sleep -Seconds 1

$mealApiPort = $DesiredPorts.MealApi
$glucoApiPort = $DesiredPorts.GlucoApi
$glucoWebPort = $DesiredPorts.GlucoWeb
$mealWebPort = $DesiredPorts.MealWeb
$machineIp = Get-PrimaryIPv4
$glucoApiHost = '127.0.0.1'
$mealApiHost = '127.0.0.1'

$mealApiRunning = $false
$glucoApiRunning = $false
$glucoWebRunning = $false
$mealWebRunning = $false

if (Test-PortBindable -Port $mealApiPort) {
  $mealApiRunning = $false
} else {
  $occupant = Get-PortOccupantKind -Port $mealApiPort -ApiHost '127.0.0.1'
  if ($occupant -eq 'meal-api') {
    $mealApiRunning = $true
  } elseif ($occupant -eq 'gluco-api' -and $machineIp) {
    $ipOccupant = Get-PortOccupantKind -Port $mealApiPort -ApiHost $machineIp
    if ($ipOccupant -eq 'meal-api') {
      $mealApiRunning = $true
      $mealApiHost = $machineIp
      Write-Host "Meal Plan API on :$mealApiPort is reachable via $machineIp because 127.0.0.1:$mealApiPort is shadowed by a stale GlucoSense listener." -ForegroundColor Yellow
    } elseif (Test-PortBindableAny -Port $mealApiPort) {
      $mealApiRunning = $false
      $mealApiHost = $machineIp
      Write-Host "Meal Plan API will start on :$mealApiPort and be reached via $machineIp because 127.0.0.1:$mealApiPort is shadowed by a stale GlucoSense listener." -ForegroundColor Yellow
    } else {
      throw "Meal Plan API port :$mealApiPort is occupied by gluco-api on 127.0.0.1 and $ipOccupant on $machineIp. Clear the conflicting listener before rerunning .\scripts\start-integrated.ps1."
    }
  } else {
    throw "Meal Plan API port :$mealApiPort is occupied by $occupant, not the Meal API. Clear that listener before rerunning .\scripts\start-integrated.ps1."
  }
}

if (Test-PortBindable -Port $glucoApiPort) {
  $glucoApiRunning = $false
} else {
  $readyResp = Get-HttpStatus -Url "http://127.0.0.1:$glucoApiPort/api/health/ready"
  $occupant = Get-PortOccupantKind -Port $glucoApiPort
  if ($readyResp.status -in @(200, 503)) {
    $glucoApiRunning = $true
  } elseif ($occupant -eq 'gluco-api' -and $machineIp -and (Test-PortBindableAny -Port $glucoApiPort)) {
    $glucoApiRunning = $false
    $glucoApiHost = $machineIp
    Write-Host "GlucoSense API will start on :$glucoApiPort and be reached via $machineIp because 127.0.0.1:$glucoApiPort is shadowed by a stale Clinical listener." -ForegroundColor Yellow
  } elseif ($occupant -eq 'gluco-api') {
    $glucoApiRunning = $true
  } else {
    throw "GlucoSense API port :$glucoApiPort is occupied by $occupant, not the Clinical API. Clear that listener before rerunning .\scripts\start-integrated.ps1."
  }
}

if (Test-PortBindable -Port $glucoWebPort) {
  $glucoWebRunning = $false
} else {
  $glucoWebRunning = $true
}

if (Test-PortBindable -Port $mealWebPort) {
  $mealWebRunning = $false
} else {
  $mealWebRunning = $true
}

$glucoApiUrl = "http://${glucoApiHost}:$glucoApiPort"
$mealApiUrl = "http://${mealApiHost}:$mealApiPort"
$mealWebUrl = "http://localhost:$mealWebPort"

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

if ($mealApiRunning) {
  Write-Step "Window 1/3: Meal Plan API already running on :$mealApiPort"
} else {
  Write-Step "Window 1/3: Meal Plan API on :$mealApiPort (Python)"
  Start-StackWindow -Title "Meal Plan API :$mealApiPort" -WorkingDir $MealBackend -CommandLine @"
`$env:PORT = '$mealApiPort'
python run.py
"@
}

Start-Sleep -Seconds 3

<<<<<<< HEAD
if ($glucoApiRunning -and $glucoWebRunning) {
  Write-Step "Window 2/3: GlucoSense API and UI already running on :$glucoApiPort + :$glucoWebPort"
} elseif ($glucoApiRunning) {
  Write-Step "Window 2/3: GlucoSense UI on :$glucoWebPort (API already running on :$glucoApiPort)"
  Start-StackWindow -Title "GlucoSense: MAIN APP (portal only)" -WorkingDir $GlucoFront -CommandLine @"
`$env:GLUCOSENSE_API_PORT = '$glucoApiPort'
`$env:GLUCOSENSE_API_HOST = '$glucoApiHost'
`$env:GLUCOSENSE_WEB_PORT = '$glucoWebPort'
`$env:MEAL_PLAN_API_URL = '$mealApiUrl'
`$env:VITE_MEAL_PLAN_API_URL = '$mealApiUrl'
`$env:MEAL_PLAN_URL = '$mealWebUrl'
`$env:VITE_MEAL_PLAN_URL = '$mealWebUrl'
node --max-old-space-size=4096 ./scripts/start-web.cjs
"@
} else {
  Write-Step "Window 2/3: GlucoSense - clinical API :$glucoApiPort + MAIN PORTAL :$glucoWebPort"
  Start-StackWindow -Title "GlucoSense: MAIN APP (portal + API)" -WorkingDir $GlucoFront -CommandLine @"
`$env:GLUCOSENSE_API_PORT = '$glucoApiPort'
`$env:GLUCOSENSE_API_HOST = '$glucoApiHost'
`$env:GLUCOSENSE_RESERVED_PORTS = '$mealApiPort'
`$env:GLUCOSENSE_WEB_PORT = '$glucoWebPort'
`$env:MEAL_PLAN_API_URL = '$mealApiUrl'
`$env:VITE_MEAL_PLAN_API_URL = '$mealApiUrl'
`$env:MEAL_PLAN_URL = '$mealWebUrl'
`$env:VITE_MEAL_PLAN_URL = '$mealWebUrl'
`$env:NODE_OPTIONS = '--max-old-space-size=6144'
=======
Write-Step "Window 2/3: GlucoSense - clinical API :8000 + MAIN PORTAL (npm run start = dev:full; Vite waits for API so no proxy spam)"
Start-StackWindow -Title 'GlucoSense: MAIN APP (portal + API)' -WorkingDir $GlucoFront -CommandLine @'
# Avoid OOM when multiple Node/Vite processes run (do not set 6GB+ heap here).
$env:NODE_OPTIONS = '--max-old-space-size=2048'
# Pick up backend Python changes without manually killing uvicorn (scoped --reload-dir in start-api.cjs).
# If you hit Windows bind error 10048, set GLUCOSENSE_UVICORN_RELOAD=0 for this window only.
$env:GLUCOSENSE_UVICORN_RELOAD = '1'
>>>>>>> b6816fd33938d1f6eb4b13b3b7093ccb1d6508fa
npm run start
"@
}

Start-Sleep -Seconds 2

if ($mealWebRunning) {
  Write-Step "Window 3/3: Meal Plan UI already running on :$mealWebPort"
} else {
  Write-Step "Window 3/3: Meal Plan Vite on :$mealWebPort (for iframe only)"
  Write-Host "  Freeing :$mealWebPort again (strict job timeout can miss this)..." -ForegroundColor DarkGray
  Stop-ListenOnPort $mealWebPort
  Start-Sleep -Seconds 2
  Start-StackWindow -Title "Meal Plan UI :$mealWebPort (iframe target)" -WorkingDir $MealFront -CommandLine @"
`$env:MEAL_PLAN_API_PORT = '$mealApiPort'
`$env:MEAL_PLAN_API_HOST = '$mealApiHost'
`$env:MEAL_PLAN_VITE_PORT = '$mealWebPort'
`$env:MEAL_PLAN_API_PROXY = '$mealApiUrl'
npm run dev:ready
"@
}

Write-Host ""
Write-Host "Three windows should be open. Use them in this order:" -ForegroundColor Green
Write-Host ""
Write-Host "  1) Wait for Meal Plan API warmup to finish on :$mealApiPort" -ForegroundColor White
Write-Host "  2) Wait for GlucoSense model readiness on :$glucoApiPort and Vite on :$glucoWebPort" -ForegroundColor Yellow
Write-Host "  3) Wait for Meal Plan Vite on :$mealWebPort (starts after Meal API readiness)" -ForegroundColor White
Write-Host ""
<<<<<<< HEAD
Write-Host "  >>> OPEN THIS IN YOUR BROWSER (main app, not meal-only):" -ForegroundColor Yellow
Write-Host "      http://localhost:$glucoWebPort" -ForegroundColor Cyan
=======
Write-Host '  OPEN THIS IN YOUR BROWSER (main app, not meal-only):' -ForegroundColor Yellow
Write-Host '      http://localhost:5173   (or :5174 if GlucoSense says port in use)' -ForegroundColor Cyan
>>>>>>> b6816fd33938d1f6eb4b13b3b7093ccb1d6508fa
Write-Host ""
Write-Host "  $mealWebUrl is ONLY the meal app for the iframe - do not use it as your main entry." -ForegroundColor DarkGray
Write-Host ""
Write-Host "  GlucoSense API docs: $glucoApiUrl/docs" -ForegroundColor White
Write-Host "  Meal Plan API docs:   $mealApiUrl/docs" -ForegroundColor White
Write-Host ""
Write-Host "GlucoSense frontend/.env should include:" -ForegroundColor Yellow
Write-Host "  VITE_MEAL_PLAN_URL=$mealWebUrl" -ForegroundColor Gray
Write-Host "  VITE_MEAL_PLAN_API_URL=$mealApiUrl" -ForegroundColor Gray
Write-Host ""
