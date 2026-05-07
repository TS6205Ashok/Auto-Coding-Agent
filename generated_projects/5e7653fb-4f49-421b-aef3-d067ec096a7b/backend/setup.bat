@echo off
setlocal
pushd "%~dp0"
python -m venv .venv
call .venv\Scripts\python -m pip install --upgrade pip
call .venv\Scripts\pip install -r requirements.txt
popd
echo Backend setup complete.
