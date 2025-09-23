@echo off
echo ------------------------------------------------------
echo Face Sequencer - ElevenLabs Audio Test with PyTorch Fix
echo ------------------------------------------------------
echo.

REM Check if Python is available
py --version 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo Python not found! Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check if the ElevenLabs audio file exists
if not exist "test_audio.mp3" (
    echo ElevenLabs audio file not found!
    echo Please place the ElevenLabs audio file in the project root directory.
    pause
    exit /b 1
)

echo Creating uploads directory if it doesn't exist...
if not exist "uploads\audio" mkdir uploads\audio

echo Pre-processing ElevenLabs audio for better alignment...
py preprocess_elevenlabs.py

echo.
echo Applying PyTorch 2.6 compatibility patch...
py fix_pytorch_whisperx.py

echo.
echo Testing direct transcription of ElevenLabs audio...
py whisperx_test.py

echo.
echo Running app with patched PyTorch...
py -c "import fix_pytorch_whisperx; fix_pytorch_whisperx.patch_all(); import app"

pause