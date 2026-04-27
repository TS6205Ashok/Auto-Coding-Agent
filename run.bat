@echo off
setlocal

set "APP_PORT=%PORT%"
if "%APP_PORT%"=="" set "APP_PORT=7860"

if exist ".venv\Scripts\python.exe" (
  call ".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port %APP_PORT%
) else (
  python -m uvicorn app.main:app --host 0.0.0.0 --port %APP_PORT%
)
