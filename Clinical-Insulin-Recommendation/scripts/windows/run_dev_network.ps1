# GlucoSense - Start backend and frontend exposed on your local network
# Others on the same Wi-Fi can access via http://<YOUR-IP>:5173

$ErrorActionPreference = "Stop"
$Root = (Get-Item $PSScriptRoot).Parent.Parent.FullName
$BackendUrl = "http://127.0.0.1:8000/api/health"
$MaxWaitSeconds = 60

function Get-GlucoPythonExe {
    param([string]$ProjectRoot)
    if ($env:GLUCOSENSE_PYTHON -and (Test-Path -LiteralPath $env:GLUCOSENSE_PYTHON)) {
        return $env:GLUCOSENSE_PYTHON
    }
    $venvPy = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPy) {
        try {
            & $venvPy -c "import sys" 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { return $venvPy }
        } catch {}
    }
    return "python"
}

$PythonExe = Get-GlucoPythonExe $Root
Write-Host "GlucoSense - Using Python: $PythonExe" -ForegroundColor DarkGray
Write-Host "GlucoSense - Starting (network mode)..." -ForegroundColor Cyan

# Start backend bound to all interfaces (0.0.0.0) so it accepts external connections
$backendJob = Start-Job -ScriptBlock {
    param($r, $py)
    Set-Location -LiteralPath $r
    & $py -m uvicorn app:app --reload --host 0.0.0.0 --port 8000 2>&1
} -ArgumentList $Root, $PythonExe

Write-Host "Backend starting (port 8000, listening on all interfaces)..." -ForegroundColor Yellow
$elapsed = 0
while ($elapsed -lt $MaxWaitSeconds) {
    try {
        $r = Invoke-WebRequest -Uri $BackendUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($r.StatusCode -eq 200) {
            Write-Host "Backend ready." -ForegroundColor Green
            break
        }
    } catch {}
    Start-Sleep -Seconds 2
    $elapsed += 2
}

if ($elapsed -ge $MaxWaitSeconds) {
    Write-Host "Backend did not become ready in time. Check for port conflicts." -ForegroundColor Red
    Stop-Job $backendJob
    exit 1
}

# Get local IP for sharing
$localIp = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.*" } | Select-Object -First 1).IPAddress
if (-not $localIp) { $localIp = "YOUR-IP" }

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Share this link with others:" -ForegroundColor Green
Write-Host "  http://${localIp}:5173" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green
Write-Host "  (Others must be on the same Wi-Fi/network)" -ForegroundColor Gray
Write-Host ""

# Start frontend with --host so it listens on all interfaces (shareable URL)
Write-Host "Starting frontend (port 5173)..." -ForegroundColor Yellow
Push-Location "$Root\frontend"
try {
    npm run dev -- --host
} finally {
    Pop-Location
    Stop-Job $backendJob -ErrorAction SilentlyContinue
}
