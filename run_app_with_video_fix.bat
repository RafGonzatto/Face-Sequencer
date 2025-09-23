#!/bin/bash
@echo off
echo Starting MP4 video export with compatibility fixes...

REM This bat file fixes MP4 export issues by forcing a compatible MoviePy workflow

REM Run app with special environment variables 
set MOVIEPY_COMPAT_MODE=1
set MOVIEPY_DEBUG=1

echo Starting app with enhanced video export...
python app.py

pause