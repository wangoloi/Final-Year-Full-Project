@echo off
REM Run meal pipeline from project root (repo inner folder with run.py)
cd /d "%~dp0..\.."
python models/run_pipeline.py
pause
