#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Serving the puzzle game at http://127.0.0.1:4173"
cd "$SCRIPT_DIR"
python3 -m http.server 4173
