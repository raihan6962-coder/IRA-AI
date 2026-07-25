@echo off
title Ira AI Assistant
echo Starting Ira AI from GitHub...

set "RAW_LINK=https://raw.githubusercontent.com/raihan6962-coder/IRA-AI/main/ira.py"
curl -s -o ira.py "%RAW_LINK%?v=%random%"
python ira.py
del ira.py
pause
