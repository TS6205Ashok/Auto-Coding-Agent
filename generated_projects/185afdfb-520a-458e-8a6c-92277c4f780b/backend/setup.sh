#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
if command -v mvn >/dev/null 2>&1; then
  mvn install
else
  echo "Maven not found. Skipping install."
fi
