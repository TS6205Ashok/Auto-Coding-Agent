# Project Agent

Project Agent is a local-only VS Code/code-server assistant for generated projects.
It sends workspace context to Ollama and never calls paid or cloud AI APIs.

## Settings

- `projectAgent.model`: default `qwen2.5-coder:latest`
- `projectAgent.fallbackModel`: default `codellama:7b`
- `projectAgent.ollamaUrl`: default `http://host.docker.internal:11434/api/generate`

## Build

```powershell
npm install
npm run compile
npm run package
```
