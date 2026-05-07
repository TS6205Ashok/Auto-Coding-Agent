#!/usr/bin/env bash
set -euo pipefail

cd vscode-extension/project-agent
npm install
npm run compile
npm run package
