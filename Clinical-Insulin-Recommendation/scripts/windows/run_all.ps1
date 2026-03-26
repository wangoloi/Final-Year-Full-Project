# GlucoSense - Run API and Frontend
# Usage: .\scripts\windows\run_all.ps1
# Or run in separate terminals:
#   Terminal 1: uvicorn app:app --reload --port 8000
#   Terminal 2: cd frontend; npm run dev

$Root = (Get-Item $PSScriptRoot).Parent.Parent.FullName

Write-Host "Starting GlucoSense API on port 8000..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root'; uvicorn app:app --reload --port 8000"

Start-Sleep -Seconds 3

Write-Host "Starting Frontend on port 5173..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\frontend'; npm run dev"

Write-Host "`nAPI: http://localhost:8000"
Write-Host "Frontend: http://localhost:5173"
Write-Host "API Docs: http://localhost:8000/docs"
