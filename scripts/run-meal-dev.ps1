<#
.SYNOPSIS
  Starts the Meal Plan FastAPI (:8001) and Meal Plan Vite (:5175) in one terminal.

.DESCRIPTION
  Runs `npm run dev:meal` from the workspace root (requires `npm install` once at repo root).

.EXAMPLE
  .\scripts\run-meal-dev.ps1
#>
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not (Test-Path (Join-Path $RepoRoot 'node_modules\concurrently'))) {
  Write-Host 'Installing workspace dependencies (first run)...' -ForegroundColor Yellow
  npm install
}

Write-Host 'Meal Plan API :8001 + Meal web :5175 — Ctrl+C stops both.' -ForegroundColor Green
npm run dev:meal
