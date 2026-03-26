# GlucoSense – create a fresh .venv on THIS machine (fixes copied/broken venvs from another PC).
# Usage (from repo root):
#   .\scripts\windows\setup_venv.ps1
# Force remove and recreate:
#   .\scripts\windows\setup_venv.ps1 -Recreate

param(
    [switch]$Recreate
)

$ErrorActionPreference = "Stop"
$Root = (Get-Item $PSScriptRoot).Parent.Parent.FullName
Set-Location -LiteralPath $Root

$venvPath = Join-Path $Root ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

function Test-VenvPython {
    param([string]$PythonExe)
    if (-not (Test-Path -LiteralPath $PythonExe)) { return $false }
    try {
        & $PythonExe -c "import sys; sys.exit(0)" 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

if ($Recreate -and (Test-Path -LiteralPath $venvPath)) {
    Write-Host "Removing existing .venv (-Recreate)..." -ForegroundColor Yellow
    Remove-Item -LiteralPath $venvPath -Recurse -Force
}

if ((Test-Path -LiteralPath $venvPath) -and -not $Recreate) {
    if (Test-VenvPython $venvPython) {
        Write-Host ".venv OK: $venvPython" -ForegroundColor Green
        Write-Host "Reinstall deps: .\.venv\Scripts\python.exe -m pip install -r requirements.txt" -ForegroundColor Cyan
        Write-Host "Full recreate:   .\scripts\windows\setup_venv.ps1 -Recreate" -ForegroundColor Cyan
        exit 0
    }
    Write-Host ".venv exists but python is broken (common after copying the project). Removing..." -ForegroundColor Yellow
    Remove-Item -LiteralPath $venvPath -Recurse -Force
}

$created = $false
foreach ($ver in @("3.12", "3.11", "3")) {
    try {
        & py "-$ver" -m venv .venv 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0 -and (Test-VenvPython $venvPython)) {
            $created = $true
            Write-Host "Created .venv with py -$ver" -ForegroundColor Green
            break
        }
    } catch {}
    if (Test-Path -LiteralPath $venvPath) {
        Remove-Item -LiteralPath $venvPath -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if (-not $created) {
    Write-Host "py launcher not available or failed; trying: python -m venv .venv" -ForegroundColor Yellow
    python -m venv .venv
    if (-not (Test-VenvPython $venvPython)) {
        Write-Host "Could not create a working venv. Install Python 3.11+ and ensure 'py' or 'python' is on PATH." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Installing requirements.txt (may take several minutes)..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $Root "requirements.txt")

Write-Host ""
Write-Host "Done. Activate:  .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host "Start API:       python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000" -ForegroundColor Green
