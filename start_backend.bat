@echo off
REM Start Flask server using the .venv Python with async support
cd /d "%~dp0"
echo Starting Face-Sequencer backend...
echo Using virtual environment Python with Flask[async]...
.venv\Scripts\python.exe -c "import flask, asgiref; print(f'Flask {flask.__version__}, asgiref {asgiref.__version__}')"
echo.
.venv\Scripts\python.exe run.py
pause
