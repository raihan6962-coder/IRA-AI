@echo off
title Ira AI - Phone Mic Mode
cd /d "%~dp0"
cls
echo ============================================
echo    IRA PHONE MIC - Starting...
echo ============================================
echo.

:: Check Python
python --version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Install Python from python.org and check "Add to PATH"
    pause
    exit /b 1
)

:: Create .env if missing
if not exist .env (
    echo GROQ_API_KEY=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 > .env
)

:: Download server
echo [1/2] Downloading phone mic server...
powershell -Command "& {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/raihan6962-coder/IRA-AI/main/phone_mic_server.py?v=%random%' -OutFile 'phone_mic_server.py'}" 2>nul
if not exist phone_mic_server.py (
    echo [ERROR] Download failed! Check internet connection.
    pause
    exit /b 1
)

:: Run server
echo [2/2] Starting server...
echo.
echo ============================================
echo   Open Chrome on your PHONE and type:
echo.
echo   THIS PC IP:5050
echo.
echo   (Find your PC IP in network settings)
echo ============================================
echo.
echo Press Ctrl+C in this window to STOP the server.
echo.

python phone_mic_server.py

echo.
echo Server stopped. Cleaning up...
del phone_mic_server.py 2>nul
del .env 2>nul

echo.
echo Press any key to exit...
pause >nul
