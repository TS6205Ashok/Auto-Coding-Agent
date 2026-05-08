# Convert My C Project

Convert My C Project is a 100% runnable starter project built around FastAPI. Fast Mode uses backend templates for all standard project structure so output quality stays complete while generation remains fast.

## What Was Generated
This ZIP contains a 100% runnable starter project from the latest preview, including dependency files, setup scripts, run scripts, starter source code, and required input guidance.

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

## Problem Statement
Convert my C++ project to Python

## Selected Stack
- Language: Python
- Frontend: None
- Backend: FastAPI
- Database: SQLite
- AI / Tools: None
- Deployment: Render

## Recommended IDE And Tools
- Recommended IDE: VS Code
- Alternative IDE: PyCharm
- Runtime tools: Python 3.11+, pip, Uvicorn
- Package manager: pip

## Chosen Stack
- Language: Python
- Frontend: None
- Backend: FastAPI
- Database: SQLite
- AI / Tools: None
- Deployment: Render

## Detected User Choices
- Language: Python

## Architecture Highlights
- FastAPI provides the API surface, routing, services, and configuration layer.
- SQLite is configured as the primary persistence layer through environment-driven settings.
- Setup, run scripts, and dependency manifests are generated server-side for a consistent starter layout.

## Core Modules
- Backend API: Provides the routes, services, and integration-ready backend surface.
  Key files: app/main.py, app/routers/items.py, app/services/item_service.py
- Persistence Layer: Supplies data models, configuration, and starter persistence wiring.
  Key files: app/database.py

## Setup
Fill `.env` from `.env.example`, then run the setup script before starting the project.
- Windows: `setup.bat`
- Mac/Linux: `setup.sh`
- Full guided setup: `FULL_RUNTIME_INSTRUCTIONS.md`

## How To Run
- Main file: `backend/app/main.py`
- Primary run command: `cd backend && python -m uvicorn app.main:app --reload`
- Run method: `Click IDE Play button or run run.bat / run.sh`
- Local URL: `http://localhost:8000`
- cd backend
- python -m uvicorn app.main:app --reload

## Required Inputs
Fill these values in `.env` before running the project.

- `APP_ENV` (optional): Application environment name.
- `PORT` (optional): Local port used when the backend starts from the generated run scripts.
- `DATABASE_URL` (required): SQLite connection string for local development.

## Notes
- Fast Mode AI planning was unavailable, so the 100% runnable starter project uses the safe template-generated fallback.
- Template fallback preview was generated because the AI planner could not complete in time or returned invalid output: AI generation is unavailable because OLLAMA_BASE_URL is not configured.
- Fast Mode used backend templates for standard files so project completeness was preserved without waiting for the model to write boilerplate.
- This output is a 100% runnable starter project after `.env` is filled, setup is run, and the run script is started. Business logic can still be customized afterward.
- SQLite was chosen as a lightweight local-first database default.
- Project-specific custom files were layered on top of the standard stack templates.

## Migration Summary
- Source stack: C++ / Unknown
- Target stack: Python / FastAPI
- See `MIGRATION_SUMMARY.md` for the detailed migration notes.
