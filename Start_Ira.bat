:Start_Ira
@echo off

curl -s https://raw.githubusercontent.com/raihan6962-coder/IRA-AI/main/ira.py -o ira.py
python ira.py
if exist ira.py del ira.py
