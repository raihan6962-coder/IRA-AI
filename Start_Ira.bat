@echo off
echo Starting Ira AI from GitHub...

:: নিচে আপনার GitHub raw link বসান (কোটেশনের ভেতরে)
set "RAW_LINK=https://raw.githubusercontent.com/raihan6962-coder/IRA-AI/refs/heads/main/ira.py"

:: cache-busting যাতে সবসময় সর্বশেষ কোড আসে
curl -s -o ira.py "%RAW_LINK%?v=%random%"

python ira.py
del ira.py
pause
