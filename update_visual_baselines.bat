@echo off
echo Running visual regression tests with baseline update...

:: Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python not found in PATH. Please install Python 3.9 or higher.
    exit /b 1
)

:: Create screenshots directory if it doesn't exist
if not exist screenshots mkdir screenshots
if not exist screenshots\baseline mkdir screenshots\baseline
if not exist screenshots\current mkdir screenshots\current
if not exist screenshots\diff mkdir screenshots\diff

:: Start the Flask server in the background
start /b python app.py

:: Wait for server to start
echo Waiting for server to start...
timeout /t 5 > nul

:: Run the visual tests to generate current screenshots
python -m pytest test_visual_regression.py -v

:: Update baselines from current screenshots
python test_visual_regression.py --update-baselines

:: Shutdown the server (finds and kills the Python process running app.py)
for /f "tokens=2" %%a in ('tasklist ^| findstr "python.*app.py"') do taskkill /pid %%a /f >nul 2>&1

echo.
echo Visual test baselines have been updated.
echo.
echo To run visual regression tests against these baselines:
echo   python -m pytest test_visual_regression.py -v
echo.