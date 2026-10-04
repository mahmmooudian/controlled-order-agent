@echo off
cd /d "%~dp0"

title Controlled AI Agent

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo ERROR: Virtual environment not found.
    echo Please run SETUP_AGENT.bat first.
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" gui_qt.py

if errorlevel 1 (
    echo.
    echo The application exited with an error.
    pause
)