@echo off
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  echo Create the backend virtual environment and install requirements first. See README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" configure_project.py
if errorlevel 1 pause
