@echo off
echo -------------------------------------------------
echo Face Sequencer with ElevenLabs Audio Optimization
echo -------------------------------------------------
echo.

REM Check if Python is available
py --version 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo Python not found! Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check if the ElevenLabs audio file exists
if not exist "ElevenLabs_2025-09-22T18_53_43_Ethan_pre_sp100_s50_sb75_se0_b_m2.mp3" (
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
echo Applying PyTorch 2.6 compatibility patch for WhisperX...
py fix_pytorch_whisperx.py

echo.
echo Starting the application with PyTorch compatibility patch...
echo.
py -c "import fix_pytorch_whisperx; fix_pytorch_whisperx.patch_all(); import app"

pause