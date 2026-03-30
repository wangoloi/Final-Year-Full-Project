<#
.SYNOPSIS
  Full integrated stack via scripts/start-integrated.ps1 (three PowerShell windows).

.DESCRIPTION
  Delegates to start-integrated.ps1 — Meal API :8001, GlucoSense portal :5173 + API :8000, Meal UI :5175.

.PARAMETER Clean
  Run scripts/free-dev-ports.ps1 first (in addition to the integrated script’s own port cleanup).

.EXAMPLE
  .\scripts\run-full-stack.ps1
.EXAMPLE
  .\scripts\run-full-stack.ps1 -Clean
#>
param([switch]$Clean)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if ($Clean) {
  Write-Host 'Freeing dev ports (free-dev-ports.ps1)...' -ForegroundColor Cyan
  & (Join-Path $PSScriptRoot 'free-dev-ports.ps1')
}

$integrated = Join-Path $PSScriptRoot 'start-integrated.ps1'
if (-not (Test-Path -LiteralPath $integrated)) {
  Write-Error "Not found: $integrated"
  exit 1
}

& $integrated
