@echo off
REM Batch wrapper for dev_tools\reorganize_files.py
REM Usage:
REM   reorganize_files.bat          (dry run)
REM   reorganize_files.bat --apply  (apply changes)
REM   reorganize_files.bat --apply --verbose

setlocal ENABLEDELAYEDEXPANSION

if not exist "%~dp0dev_tools\reorganize_files.py" (
  echo [ERROR] Could not find dev_tools\reorganize_files.py relative to script.
  exit /b 1
)

REM Prefer venv if available
if exist "%~dp0.venv\Scripts\python.exe" (
  set PYTHON_EXE=%~dp0.venv\Scripts\python.exe
) else (
  set PYTHON_EXE=python
)

"%PYTHON_EXE%" "%~dp0dev_tools\reorganize_files.py" %*
set EXITCODE=%ERRORLEVEL%

if %EXITCODE% NEQ 0 (
  echo Script exited with code %EXITCODE%.
)

endlocal
exit /b %EXITCODE%
