#!/usr/bin/env bash
set -e
if [ -f backend/requirements.txt ]; then
  (
    cd backend
    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
  )
fi
if [ -f frontend/package.json ]; then
  (cd frontend && npm install)
fi
echo "Setup complete."
