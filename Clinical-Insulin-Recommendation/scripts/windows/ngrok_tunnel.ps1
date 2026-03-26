# GlucoSense - Start ngrok tunnel for public URL
# Run this AFTER starting the app with .\scripts\windows\run_dev.ps1 or .\scripts\windows\run_dev_network.ps1

$ngrokExe = "C:\Users\Dell\AppData\Local\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe"

if (-not (Test-Path $ngrokExe)) {
    # Fallback: try ngrok from PATH (after restarting terminal)
    $ngrokExe = "ngrok"
}

Write-Host "Starting ngrok tunnel to port 5173..." -ForegroundColor Cyan
Write-Host "Make sure GlucoSense is running (.\scripts\windows\run_dev.ps1) first!" -ForegroundColor Yellow
Write-Host ""
Write-Host "First-time visitors: ngrok shows a 'Visit Site' interstitial. Click it to continue." -ForegroundColor Gray
Write-Host ""

& $ngrokExe http 5173
