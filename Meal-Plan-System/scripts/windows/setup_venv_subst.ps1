# Glocusense / Meal Plan — create .venv when your path contains ';' (Windows PATH separator).
# Python refuses: python -m venv  →  "contains the PATH separator ;"
# This script maps a drive letter to the project root (no ';' in the drive path), then creates .venv there.
#
# Usage (from anywhere):
#   powershell -ExecutionPolicy Bypass -File "E:\...\Meal-Plan-System\scripts\windows\setup_venv_subst.ps1"
# Or cd to project root and:
#   .\scripts\windows\setup_venv_subst.ps1
#
# Optional: choose a free drive letter (default G:)
#   .\scripts\windows\setup_venv_subst.ps1 -DriveLetter Z

param(
    [ValidatePattern('^[A-Za-z]$')]
    [string]$DriveLetter = 'G'
)

$ErrorActionPreference = "Stop"
$DriveLetter = $DriveLetter.ToUpperInvariant()
$ProjectRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
$MarkerFile = Join-Path $ProjectRoot ".glocusense_subst_drive"
$SubstPath = "${DriveLetter}:"

function Test-PathHasSemicolon([string]$p) {
    return $p -match ';'
}

Write-Host "Project root: $ProjectRoot" -ForegroundColor Cyan

if (-not (Test-PathHasSemicolon $ProjectRoot)) {
    Write-Host "Tip: Path has no ';' — you can also use: python -m venv .venv" -ForegroundColor DarkYellow
}

# Remove only an existing SUBST mapping for this letter (safe: does not remove a physical volume)
$subList = (cmd.exe /c subst 2>&1) | Out-String
if ($subList -match "(?m)^$DriveLetter`:\\s") {
    Write-Host "Clearing existing SUBST $SubstPath ..." -ForegroundColor Yellow
    cmd.exe /c "subst ${DriveLetter}: /d" | Out-Null
}

Write-Host "Mapping $SubstPath -> $ProjectRoot" -ForegroundColor Green
# cmd.exe quoting handles ';' inside the path reliably
$exit = (Start-Process -FilePath "cmd.exe" -ArgumentList @('/c', "subst ${DriveLetter}: `"$ProjectRoot`"") -Wait -PassThru -NoNewWindow).ExitCode
if ($exit -ne 0) {
    throw "subst failed (exit $exit). Pick a free unused letter: .\setup_venv_subst.ps1 -DriveLetter Z"
}
if (-not (Test-Path "${SubstPath}\")) {
    throw "SUBST reported OK but ${SubstPath}\ is not visible. Try another -DriveLetter or run without admin if blocked."
}

$DriveLetter | Set-Content -Path $MarkerFile -Encoding ascii -NoNewline
Write-Host "Saved drive letter to $MarkerFile" -ForegroundColor DarkGray

Push-Location $SubstPath
try {
    if (Test-Path ".venv") {
        Write-Host ".venv already exists on $SubstPath" -ForegroundColor Yellow
    } else {
        Write-Host "Creating venv at ${SubstPath}\.venv ..." -ForegroundColor Cyan
        python -m venv .venv
    }
    $py = Join-Path $SubstPath ".venv\Scripts\python.exe"
    if (-not (Test-Path $py)) {
        throw "venv python not found at $py"
    }
    & $py -m pip install --upgrade pip
    & $py -m pip install -r (Join-Path $SubstPath "backend\requirements.txt")
    Write-Host ""
    Write-Host "Done." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps (use the $SubstPath drive so paths stay valid):" -ForegroundColor White
    Write-Host "  ${DriveLetter}:" -ForegroundColor Yellow
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "  python backend\run.py" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Or without activating (from any cwd):" -ForegroundColor White
    Write-Host "  & '${DriveLetter}:\.venv\Scripts\python.exe' '${DriveLetter}:\backend\run.py'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Remove mapping later:  subst $DriveLetter`:" /d" -ForegroundColor DarkGray
}
finally {
    Pop-Location
}
