@echo off
echo Installing Face Sequencer Pro testing dependencies...

:: Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python not found in PATH. Please install Python 3.9 or higher.
    exit /b 1
)

:: Install dependencies
python -m pip install -r requirements.txt
python -m pip install -r requirements_audio.txt
python -m pip install -r requirements_testing.txt

echo.
echo Testing dependencies installed successfully!
echo.
echo To run tests:
echo   - Unit tests:       python -m pytest test_audio_basic.py
echo   - Integration:      python -m pytest test_audio_integration.py test_sequence_building.py
echo   - Browser tests:    python -m pytest test_cross_browser.py --driver Chrome
echo   - Performance:      python -m pytest test_performance.py
echo   - Visual tests:     python -m pytest test_visual_regression.py
echo   - Load tests:       python -m locust -f locustfile.py
echo.
echo For CI/CD:            github.com/workflows/ci.yml is configured
echo.