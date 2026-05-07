Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Push-Location "vscode-extension/project-agent"
npm install
npm run compile
npm run package
Pop-Location
