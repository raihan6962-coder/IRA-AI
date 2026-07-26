@echo off
title Ira AI Assistant
echo Starting Ira AI from GitHub...

:: Create .env file with your API key
echo GROQ_API_KEY=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 > .env

:: Download latest ira.py (cache-busting with random)
powershell -Command "& {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/raihan6962-coder/IRA-AI/main/ira.py?v=%random%' -OutFile 'ira.py'}"

:: Run Ira
python ira.py

:: Clean up
del ira.py
del .env
pause
