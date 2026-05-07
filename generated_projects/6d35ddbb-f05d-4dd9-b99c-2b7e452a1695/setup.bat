@echo off
setlocal
if exist backend\requirements.txt (
  pushd backend
  python -m venv .venv
  call .venv\Scripts\python -m pip install --upgrade pip
  call .venv\Scripts\pip install -r requirements.txt
  popd
)
if exist frontend\package.json (
  pushd frontend
  call npm install
  popd
)
echo Setup complete.
