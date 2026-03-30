@echo off
REM Free ports, then full stack (start-integrated.ps1)
cd /d "%~dp0.."
call npm run ports:free
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-integrated.ps1"
