# Setup Instructions

## Quick Start
Generated version: Project Agent Generated Starter v1
Main file to open: `backend/app/main.py`
Primary run command: `cd backend && python -m uvicorn app.main:app --reload`
1. Run `run.bat` on Windows or `./run.sh` on Mac/Linux.
2. Enter any missing required inputs when the app prompts for them at runtime.
3. The application will finish startup automatically after dependencies install and required values are provided.

## Windows
1. Run `run.bat`.
2. If `.env` is missing, the script will create it from `.env.example` automatically.
3. If a required backend value is still missing, enter it when prompted in the terminal.

## Mac/Linux
1. Run `chmod +x setup.sh run.sh` once if the scripts are not executable.
2. Run `./run.sh`.
3. If `.env` is missing, the script will create it from `.env.example` automatically.
4. If a required backend value is still missing, enter it when prompted in the terminal.

## Setup Scripts
- Windows: `setup.bat`
- Mac/Linux: `setup.sh`

## Selected Stack
- Language: Python
- Frontend: React
- Backend: FastAPI
- Database: SQLite
- AI / Tools: None
- Deployment: Render

## Install Commands
- cd backend
- pip install -r requirements.txt

## Run Commands
- cd backend
- python -m uvicorn app.main:app --reload

## Recommended IDE And Tools
- Recommended IDE: VS Code
- Alternative IDE: PyCharm
- Runtime tools: Python 3.11+, pip, Uvicorn
- Package manager: pip

## Environment Variables
- `APP_ENV` (Application environment name.) default `development`
- `PORT` (Local port used when the backend starts from the generated run scripts.) default `8000`
- `DATABASE_URL` (SQLite connection string for local development.) default `sqlite:///./app.db`
- `VITE_API_BASE_URL` (Frontend base URL for backend API calls.) default `http://localhost:8000`

## Troubleshooting
- If dependencies fail to install, confirm Python, Node.js, or Maven is installed for the selected stack.
- If the app cannot connect to a service, double-check the values in `.env` against `REQUIRED_INPUTS.md`.
- If frontend and backend both start locally, verify `VITE_API_BASE_URL` or related API host settings match the backend URL.

## Notes
- Some stack choices were inferred automatically to provide a complete beginner-friendly starter.
- Fast Mode used backend templates for standard files so project completeness was preserved without waiting for the model to write boilerplate.
- The project is split into frontend and backend folders to keep the full-stack boundary explicit.
- This output is a 100% runnable starter project after `.env` is filled, setup is run, and the run script is started. Business logic can still be customized afterward.
- SQLite was chosen as a lightweight local-first database default.
- Project-specific custom files were layered on top of the standard stack templates.
- Validation fallback rebuilt the project from deterministic safe templates after repair attempts.
