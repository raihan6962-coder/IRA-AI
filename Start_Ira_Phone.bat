@echo off
title Ira AI - Phone Mic Mode
cd /d "%~dp0"
cls
echo ============================================
echo    IRA PHONE MIC
echo ============================================
echo.

if not exist .env (
    echo GROQ_API_KEY=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 > .env
)

:: Install ffmpeg if not present (needed for audio conversion)
where ffmpeg >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing ffmpeg (needed for audio)...
    winget install "FFmpeg (Essentials Build)" --accept-package-agreements -h 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo Please install ffmpeg manually from https://ffmpeg.org
    )
)

echo Downloading phone mic server...
powershell -Command "& {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/raihan6962-coder/IRA-AI/main/phone_mic_server.py?v=%random%' -OutFile 'phone_mic_server.py'}"

python phone_mic_server.py

del phone_mic_server.py 2>nul
del .env 2>nul
pause
