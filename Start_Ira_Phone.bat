@echo off
title Ira AI - Phone Mic Mode
cd /d "%~dp0"
cls
echo ============================================
echo    IRA PHONE MIC
echo    Your Phone = Ira's Microphone
echo ============================================
echo.

if not exist .env (
    echo Creating .env file...
    echo GROQ_API_KEY=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 > .env
)

echo [1/3] Downloading phone mic server...
powershell -Command "& {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/raihan6962-coder/IRA-AI/main/phone_mic_server.py?v=%random%' -OutFile 'phone_mic_server.py'}"

echo [2/3] Starting server...
echo.
echo ============================================
echo   OPEN PHONE BROWSER ^(Chrome^) and TYPE:
echo.
echo   http://THIS_PC_IP:5050
echo.
echo   Find YOUR PC IP:
echo   - Windows: cmd ^> ipconfig ^> IPv4 Address
echo   - Or look just below this message
echo ============================================
python phone_mic_server.py

echo [3/3] Cleaning up...
del phone_mic_server.py 2>nul
del .env 2>nul
pause
