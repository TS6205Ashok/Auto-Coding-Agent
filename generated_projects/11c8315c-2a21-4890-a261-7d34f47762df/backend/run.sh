#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
echo "Starting Project..."
if [ ! -f ../.env ] && [ -f ../.env.example ]; then
  cp ../.env.example ../.env
fi
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app/main.py
