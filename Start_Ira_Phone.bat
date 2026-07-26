@echo off
title Ira AI - Phone Mic Mode
cls
echo ============================================
echo    🎤 IRA PHONE MIC MODE
echo    Your Phone = Ira's Microphone
echo ============================================
echo.

:: Check for .env file
if not exist .env (
    echo Creating .env file with your API key...
    echo GROQ_API_KEY=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 > .env
)

:: Check if flask is installed
python -c "import flask" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing flask for phone mic server...
    pip install flask flask-cors
)

:: Download latest phone_mic_server.py
echo Downloading phone mic server from GitHub...
powershell -Command "& {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/raihan6962-coder/IRA-AI/main/phone_mic_server.py?v=%random%' -OutFile 'phone_mic_server.py'}"

:: Download latest ira.py (used by the server)
echo Downloading Ira engine...
powershell -Command "& {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/raihan6962-coder/IRA-AI/main/ira.py?v=%random%' -OutFile 'ira.py'}"

:: Run the server
python phone_mic_server.py

:: Clean up
del phone_mic_server.py 2>nul
del ira.py 2>nul
del .env 2>nul

pause
