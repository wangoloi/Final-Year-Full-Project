# GlucoSense - Start backend and frontend in correct order
# Usage (from repo root): .\scripts\windows\run_dev.ps1
# Ensures backend is healthy before frontend starts (avoids proxy ECONNREFUSED errors)
# Use scripts\windows\run_dev_network.ps1 to expose on your local network for sharing.

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
Write-Host "GlucoSense - Starting backend and frontend..." -ForegroundColor Cyan

# Start backend in background (127.0.0.1 = localhost only)
$backendJob = Start-Job -ScriptBlock {
    param($r, $py)
    Set-Location -LiteralPath $r
    & $py -m uvicorn app:app --reload --host 127.0.0.1 --port 8000 2>&1
} -ArgumentList $Root, $PythonExe

Write-Host "Backend starting (port 8000)..." -ForegroundColor Yellow
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

# Start frontend (foreground - user sees logs)
Write-Host "Starting frontend (port 5173)..." -ForegroundColor Yellow
Push-Location "$Root\frontend"
try {
    npm run dev
} finally {
    Pop-Location
    Stop-Job $backendJob -ErrorAction SilentlyContinue
}
