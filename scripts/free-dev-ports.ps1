# Free GlucoSense integrated dev ports (Windows). Single netstat parse; then taskkill.
$ErrorActionPreference = 'SilentlyContinue'
$ports = @(8000, 8001, 5173, 5174, 5175)
$toKill = @{}

$lines = @(netstat -ano)
foreach ($line in $lines) {
  if ($line -notmatch 'LISTENING') { continue }
  foreach ($port in $ports) {
    if ($line -match ":$port\s" -and $line -match 'LISTENING\s+(\d+)\s*$') {
      $procId = [int]$Matches[1]
      if ($procId -gt 0) { $toKill[$procId] = $true }
    }
  }
}

foreach ($procId in $toKill.Keys) {
  Write-Host "Stopping PID $procId"
  Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
}

Write-Host "Done."
