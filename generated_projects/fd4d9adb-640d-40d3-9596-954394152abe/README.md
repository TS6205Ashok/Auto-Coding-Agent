# Customer Chatbot Ivr For

Customer Chatbot Ivr For is a 100% runnable starter project built around React + FastAPI. Fast Mode uses backend templates for all standard project structure so output quality stays complete while generation remains fast.

## What Was Generated
This ZIP contains a 100% runnable starter project from the latest preview, including dependency files, setup scripts, run scripts, starter source code, and required input guidance.

## Generated Project Identity
- Project name: Customer Chatbot Ivr For
- Generated version: Project Agent Generated Starter v1
- Main file: `backend/app/main.py`
- Run command: `cd backend && python -m uvicorn app.main:app --reload`
- Selected Stack:
- Language: Python
- Frontend: React
- Backend: FastAPI
- Database: SQLite
- AI / Tools: None
- Deployment: Render

## Problem Statement
Customer Chatbot / IVR for Banking Services

        Build a banking customer support chatbot and IVR system for web chat,
        mobile app, WhatsApp, and phone IVR. Customers can check account balance,
        view recent transactions, block debit or credit cards, check loan EMI
        details, track complaint status, find nearest branch or ATM, answer FAQs,
        and transfer to a human agent. Balance enquiry asks for customer ID,
        then OTP 123456, then returns the balance for CUST1001 as 45230.75.

## Selected Stack
- Language: Python
- Frontend: React
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
- Frontend: React
- Backend: FastAPI
- Database: SQLite
- AI / Tools: None
- Deployment: Render

## Detected User Choices
- The user did not explicitly specify language, tooling, or framework choices.

## Architecture Highlights
- React handles the user-facing workflows, starter pages, and client-side integration points.
- FastAPI provides the API surface, routing, services, and configuration layer.
- SQLite is configured as the primary persistence layer through environment-driven settings.
- OpenAI API integration is isolated behind service boundaries so model/provider settings can evolve independently.
- Setup, run scripts, and dependency manifests are generated server-side for a consistent starter layout.

## Core Modules
- Frontend Experience: Provides the main user interface, starter pages, and client-side state or API hooks.
  Key files: frontend/src/App.jsx, frontend/src/pages/HomePage.jsx, frontend/src/services/api.js
- Backend API: Provides the routes, services, and integration-ready backend surface.
  Key files: backend/app/main.py, backend/app/routers/items.py, backend/app/services/item_service.py
- Persistence Layer: Supplies data models, configuration, and starter persistence wiring.
  Key files: backend/app/database.py
- Chatbot Module: Handles customer messages, conversation state, OTP prompts, and response formatting.
  Key files: backend/app/routers/chatbot.py, backend/app/services/chatbot_service.py
- Banking Service Module: Provides dummy banking operations for balance, transactions, cards, loans, complaints, and locations.
  Key files: backend/app/routers/banking.py, backend/app/services/banking_service.py
- Intent Detection Module: Maps customer messages to supported banking intents.
  Key files: backend/app/services/intent_service.py
- Dummy Banking Database: Stores sample customer, card, loan, complaint, OTP, branch, and ATM data.
  Key files: backend/app/data/dummy_customers.json
- Frontend Chat Interface: Provides a React chat page, message bubbles, and API client for the banking assistant.
  Key files: frontend/src/pages/ChatbotPage.jsx, frontend/src/components/ChatWindow.jsx, frontend/src/components/MessageBubble.jsx, frontend/src/services/chatbotApi.js
- Complaints Module: Complaint tracking workflow and APIs.
  Key files: backend/app/routers/complaints.py, backend/app/services/complaint_service.py, frontend/src/pages/ComplaintPage.jsx
- Transactions Module: Transaction lookup workflow and APIs.
  Key files: backend/app/routers/transactions.py, backend/app/services/transaction_service.py, frontend/src/pages/TransactionsPage.jsx
- Loans Module: Loan and EMI workflow and APIs.
  Key files: backend/app/routers/loans.py, backend/app/services/loan_service.py, frontend/src/pages/LoanPage.jsx
- Locations Module: Branch and ATM location workflow and APIs.
  Key files: backend/app/routers/locations.py, backend/app/services/location_service.py, frontend/src/pages/LocationsPage.jsx

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
- `OPENAI_API_KEY` (required): Used for AI chatbot responses.
- `VITE_API_BASE_URL` (optional): Frontend base URL for backend API calls.

## Notes
- Fast Mode AI planning was unavailable, so the 100% runnable starter project uses the safe template-generated fallback.
- Template fallback preview was generated because the AI planner could not complete in time or returned invalid output: AI generation is unavailable because OLLAMA_BASE_URL is not configured.
- Fast Mode used backend templates for standard files so project completeness was preserved without waiting for the model to write boilerplate.
- The project is split into frontend and backend folders to keep the full-stack boundary explicit.
- This output is a 100% runnable starter project after `.env` is filled, setup is run, and the run script is started. Business logic can still be customized afterward.
- SQLite was chosen as a lightweight local-first database default.
- Project-specific custom files were layered on top of the standard stack templates.

## Migration Summary
- Source stack: Unknown / Unknown
- Target stack: Auto / Auto
- See `MIGRATION_SUMMARY.md` for the detailed migration notes.
