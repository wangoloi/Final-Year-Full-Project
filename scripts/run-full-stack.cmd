@echo off
REM Full stack: opens 3 windows via scripts\start-integrated.ps1
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-integrated.ps1"
