@echo off
title Ira AI Assistant
echo Starting Ira AI from GitHub...

:: সবসময় সর্বশেষ কোড আনার জন্য cache-busting সহ PowerShell download
powershell -Command "& {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/raihan6962-coder/IRA-AI/main/ira.py?v=%random%' -OutFile 'ira.py'}"
python ira.py
del ira.py
pause
