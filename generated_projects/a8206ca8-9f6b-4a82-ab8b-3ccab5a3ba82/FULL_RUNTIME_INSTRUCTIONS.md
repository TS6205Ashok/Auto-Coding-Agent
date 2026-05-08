# Full Runtime Instructions

## 1. PROJECT OVERVIEW
- Project: Convert My C Project
- Generated version: Project Agent Generated Starter v1
- What this project does: Convert My C Project is a 100% runnable starter project built around FastAPI. Fast Mode uses backend templates for all standard project structure so output quality stays complete while generation remains fast.
- Tech stack used:
- Language: Python
- Frontend: None
- Backend: FastAPI
- Database: SQLite
- AI / Tools: None
- Deployment: Render
- What should happen when it runs successfully: The server starts successfully and responds in the terminal and browser/API client.

## 2. RECOMMENDED IDE
- Primary IDE: VS Code
- Alternative IDE: PyCharm

## Generated Project Identity
- Project name: Convert My C Project
- Generated version: Project Agent Generated Starter v1
- Main file: `backend/app/main.py`
- Run command: `cd backend && python -m uvicorn app.main:app --reload`
- Selected Stack:
- Language: Python
- Frontend: None
- Backend: FastAPI
- Database: SQLite
- AI / Tools: None
- Deployment: Render

## 3. REQUIRED EXTENSIONS / PLUGINS
- VS Code: Python extension
- VS Code: Pylance
- PyCharm: Python support is built in

## 4. SYSTEM REQUIREMENTS
- Git and a terminal available inside your IDE.
- Python 3.10+ (3.11+ recommended).
- Runtime tools used by this stack: Python 3.11+, pip, Uvicorn.

## 5. STEP-BY-STEP SETUP INSTRUCTIONS
1. Open the unzipped project folder in your IDE.
2. Open the integrated terminal in the IDE.
3. Review `.env.example` and `REQUIRED_INPUTS.md` before starting.
4. Create or activate a Python environment if needed, then install dependencies.
   - Example: `pip install -r requirements.txt`
   - Alternate command: `cd backend`
   - Alternate command: `pip install -r requirements.txt`
5. Save your changes and keep the terminal open for the run step.

## 6. REQUIRED INPUTS (API KEYS / CONFIG)
- `APP_ENV` (optional): Application environment name.
- `PORT` (optional): Local port used when the backend starts from the generated run scripts.
- `DATABASE_URL` (required): SQLite connection string for local development.

| Input Name | Required | Example | Where To Enter | Purpose |
|---|---|---|---|---|
| APP_ENV | No | development | .env | Application environment name. |
| PORT | No | 8000 | .env | Local port used when the backend starts from the generated run scripts. |
| DATABASE_URL | Yes | sqlite:///./app.db | Terminal prompt or .env | SQLite connection string for local development. |

## 7. HOW RUNTIME INPUT WORKS
- If a required value is missing from the environment, the backend will prompt for it in the terminal.
- Enter the value when asked and the application will continue starting.
- You can avoid repeated prompts by copying `.env.example` to `.env` and filling the values there.

## 8. HOW TO RUN THE PROJECT
- Open main file: `backend/app/main.py`
- Run method: `Click IDE Play button or run run.bat / run.sh`
- Primary run command: `cd backend && python -m uvicorn app.main:app --reload`
- Local URL: `http://localhost:8000`
- IDE Play button: open `.vscode/launch.json`, choose the generated run configuration, and click Run/Play.
- VS Code Run Task: press Ctrl+Shift+P, choose `Tasks: Run Task`, then select `Run Project`.
- Windows: `run.bat`
- Mac/Linux: `chmod +x run.sh` then `./run.sh`
- Manual backend run: `python -m uvicorn app.main:app --reload` from the backend folder.
- Additional run command: `cd backend`
- Additional run command: `python -m uvicorn app.main:app --reload`

## 9. EXPECTED OUTPUT
- Success looks like this: The server starts successfully and responds in the terminal and browser/API client.
- Problem statement handled by this starter: Convert my C++ project to Python

## 10. TROUBLESHOOTING
- If the project does not start, confirm the required dependencies were installed successfully.
- Verify the required language/runtime versions from the System Requirements section.
- Restart the IDE terminal and run the setup and run steps again.
- If an API or configuration error occurs, check the values in `.env` or re-enter them when prompted.
- Ensure your internet connection is available for any external API integrations.
- Confirm these runtime tools are installed and available: Python 3.11+, pip, Uvicorn.
- If an unknown error occurs: stop the program, return to the setup steps, rerun them from the beginning, then start the project again.

## 11. RESET INSTRUCTIONS
- Delete the `.env` file if you want the project to prompt for values again.
- Reinstall dependencies using the setup instructions if the environment became inconsistent.
- Run the project again after the reset steps complete.

## 12. MIGRATION NOTES
- Original stack: C++ / Unknown
- New stack: Python / FastAPI
- Key changes:
- Converted implementation language from C++ to Python.
- Limitations: this is a runnable rebuilt starter in the target stack, not a byte-for-byte source translation.

- Package manager: pip
