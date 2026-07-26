@echo off
title Ira AI - Phone Mic Mode
cls
echo ============================================
echo    IRA PHONE MIC MODE
echo    Your Phone = Ira's Microphone
echo ============================================
echo.

if not exist .env (
    echo Creating .env file...
    echo GROQ_API_KEY=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 > .env
)

echo Downloading phone mic server...
powershell -Command "& {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/raihan6962-coder/IRA-AI/main/phone_mic_server.py?v=%random%' -OutFile 'phone_mic_server.py'}"

python phone_mic_server.py

del phone_mic_server.py 2>nul
del .env 2>nul
pause
