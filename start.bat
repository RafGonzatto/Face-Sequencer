@echo off
REM Face Sequencer Pro - Windows Launcher
echo ================================================
echo Face Sequencer Pro - Lip Sync Animation Tool
echo ================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

REM Navigate to the application directory
cd /d "%~dp0"

REM Launch the application
echo Starting Face Sequencer Pro...
echo Web interface will open at: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.
python launch.py

pause