# Project Agent VS Code Extension

This local VS Code extension connects to the existing Project Agent backend and writes generated project files directly into the current workspace.

## Features

- Generate a runnable starter project from the current VS Code workspace
- Review a lightweight preview summary before writing files
- Safely write generated files with overwrite prompts
- Show required inputs and open `REQUIRED_INPUTS.md`
- Run setup and run scripts only after explicit confirmation
- Open the generated `README.md`

## Configuration

Set the backend API URL in VS Code settings:

- `projectAgent.apiUrl`
- default: `http://localhost:8000`

## Commands

- `Project Agent: Generate Project`
- `Project Agent: Install Dependencies`
- `Project Agent: Run Project`
- `Project Agent: Show Required Inputs`
- `Project Agent: Open README`

## Local Development

1. Open `project-agent-vscode/` in VS Code.
2. Run:

```bash
npm install
npm run compile
```

3. Press `F5`.
4. In the Extension Development Host, run:

```text
Project Agent: Generate Project
```

## Notes

- The extension calls `POST /api/suggest`.
- It does not use `POST /api/zip` in this first local version.
- It only runs known safe local scripts:
  - `setup.bat` / `setup.sh`
  - `run.bat` / `run.sh`
