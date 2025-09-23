@echo off
echo --------------------------------------------------------
echo Enhanced ElevenLabs Audio Processor for Lip Sync Animation
echo --------------------------------------------------------
echo.

REM Check if Python is available
py --version 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo Python not found! Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check if required packages are installed
echo Checking required packages...
py -c "import librosa, soundfile, numpy, scipy, matplotlib" 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo Installing required packages...
    py -m pip install librosa soundfile numpy scipy matplotlib
)

REM Check if any ElevenLabs audio file exists in the current directory
py -c "import pathlib; files = list(pathlib.Path('.').glob('ElevenLabs*.mp3')); print('FOUND' if files else 'NOTFOUND')" > temp.txt
set /p HAS_FILES=<temp.txt
del temp.txt

if "%HAS_FILES%"=="NOTFOUND" (
    echo No ElevenLabs audio files found in the project root directory!
    echo.
    echo Please place your ElevenLabs audio file in this folder.
    echo File name should start with "ElevenLabs" and have .mp3 extension.
    echo.
    pause
    exit /b 1
)

echo Creating uploads directory if it doesn't exist...
if not exist "uploads\audio" mkdir uploads\audio

echo.
echo Running enhanced ElevenLabs audio processor with visualization...
py enhanced_elevenlabs_processor.py --plot

echo.
echo If the app is not already running, start it with:
echo    py app.py
echo.
echo Or use the standard start.bat script to run the full application.

pause