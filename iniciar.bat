@echo off
cd /d "%~dp0"
if not exist .venv (
    echo Preparando Luma por primera vez, un momento...
    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt
)
start "" .venv\Scripts\pythonw.exe main.py
