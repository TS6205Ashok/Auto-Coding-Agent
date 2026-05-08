#!/usr/bin/env bash
set -e
if [ -f backend/pom.xml ]; then
  if command -v mvn >/dev/null 2>&1; then
    (cd backend && mvn install)
  else
    echo "Maven not found. Skipping backend install."
  fi
fi
if [ -f frontend/package.json ]; then
  (cd frontend && npm install)
fi
echo "Setup complete."
