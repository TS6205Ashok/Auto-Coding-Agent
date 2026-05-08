@echo off
setlocal
pushd "%~dp0"
echo Starting Project...
if not exist ..\.env if exist ..\.env.example copy ..\.env.example ..\.env >nul
if not exist .venv python -m venv .venv
call .venv\Scripts\python -m pip install --upgrade pip
call .venv\Scripts\pip install -r requirements.txt
call .venv\Scripts\python app/main.py
popd
