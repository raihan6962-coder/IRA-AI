:Start_Ira
@echo off

curl -s https://github.com/yourusername/ira-assistant/raw/main/ira.py -o ira.py
python ira.py
if exist ira.py del ira.py
