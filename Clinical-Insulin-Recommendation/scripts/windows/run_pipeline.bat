@echo off
REM Run GlucoSense pipeline from command prompt
REM Ensure you have activated your Python environment first (e.g., venv_tf)

cd /d "%~dp0..\.."
python scripts\notebook\execute_development_notebook.py
pause
