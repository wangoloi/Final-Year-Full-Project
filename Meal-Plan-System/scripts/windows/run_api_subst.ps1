# Run FastAPI using the venv created by setup_venv_subst.ps1 (works with ';' in real folder path).
# Ensures SUBST is applied, then runs:  <drive>:\.venv\Scripts\python.exe <drive>:\backend\run.py

$ErrorActionPreference = "Stop"
$ProjectRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
$MarkerFile = Join-Path $ProjectRoot ".glocusense_subst_drive"

if (-not (Test-Path $MarkerFile)) {
    Write-Host "No .glocusense_subst_drive — run first:" -ForegroundColor Red
    Write-Host "  .\scripts\windows\setup_venv_subst.ps1" -ForegroundColor Yellow
    exit 1
}

$DriveLetter = (Get-Content -LiteralPath $MarkerFile -Raw).Trim().ToUpperInvariant()
if ($DriveLetter.Length -ne 1) {
    throw "Invalid .glocusense_subst_drive content"
}

$SubstPath = "${DriveLetter}:"
# Re-apply SUBST if this session lost it (e.g. new terminal after reboot)
if (-not (Test-Path "${SubstPath}\")) {
    Write-Host "Applying SUBST $SubstPath -> $ProjectRoot" -ForegroundColor Cyan
    $exit = (Start-Process -FilePath "cmd.exe" -ArgumentList @('/c', "subst ${DriveLetter}: `"$ProjectRoot`"") -Wait -PassThru -NoNewWindow).ExitCode
    if ($exit -ne 0) {
        Write-Host "subst failed. Run: .\scripts\windows\setup_venv_subst.ps1" -ForegroundColor Red
        exit 1
    }
}

$py = "${SubstPath}\.venv\Scripts\python.exe"
$run = "${SubstPath}\backend\run.py"
if (-not (Test-Path $py)) {
    Write-Host "Missing $py — run setup_venv_subst.ps1" -ForegroundColor Red
    exit 1
}

Set-Location $SubstPath
& $py $run
