# The Proposed System Is Explanation

## Summary
The Proposed System Is is a 100% runnable starter project built around React + FastAPI. Fast Mode uses backend templates for all standard project structure so output quality stays complete while generation remains fast.

## Generated Project Identity
- Project name: The Proposed System Is
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
The proposed system is an AI-powered multilingual banking assistant designed to provide intelligent banking support through both text-based chatbot and voice-based IVR interactions.
The assistant is capable of handling:
1. Existing Customer Services2. Non-Existing Customer Product Enquiries
The system simulates how real banking support agents work by:


Identifying users


Verifying customers


Understanding customer queries


Fetching banking information


Providing accurate responses


Supporting multilingual communication


The assistant aims to improve customer experience, reduce manual support workload, and provide 24/7 banking assistance.

🎯 Problem Statement
Modern banks receive a massive number of customer support requests daily, including:


Account balance enquiries


Transaction-related queries


Card blocking requests


Loan EMI enquiries


Product information requests


Account opening guidance


Traditional customer support systems face several limitations:


Long waiting times in call centers


High dependency on human agents


Limited multilingual support


Poor accessibility for regional language users


Lack of unified support across chat and voice channels


Additionally:


Existing customers require quick issue resolution


Non-existing customers need guidance regarding banking products and services


Most current systems are either:


Chat-only systems


IVR-only systems


English-only systems


which creates communication barriers and inconsistent customer experience.

💡 Proposed Solution
The proposed solution is a:
Multilingual Conversational Banking Assistant
that can:


Support both chat and voice interactions


Assist existing and non-existing customers


Understand multiple languages


Provide real-time banking assistance


Simulate real banking support workflows


The system uses:


Conversational AI


Intent detection


Voice processing


Multilingual response generation


Mock banking data and APIs



👥 User Categories

1. Existing Customers
The assistant provides customer service support such as:
Balance enquiryMini statementCard status checkCard block/unblockLoan EMI detailsKYC verification statusComplaint trackingAccount informationHuman agent handoff

2. Non-Existing Customers
The assistant provides banking product guidance such as:
Savings account detailsCurrent account detailsCredit card informationLoan detailsFixed deposit informationEligibility criteriaRequired documentsAccount opening guidance

🌐 Multilingual Capability
The assistant supports multiple languages including:
EnglishHindiTeluguTamil
The system detects the user language and responds in the same language.
Example:
User: Mera balance bataoBot: Aapka balance ₹45,230.75 haiUser: Na card block cheyyaliBot: Mee card block cheyabadindi

🎙️ Voice Assistant / IVR Support
The system also functions as a voice-based banking assistant.
Features include:


Speech-to-Text conversion


Voice response generation


Voice navigation


IVR-style conversation flow


Example:
Bot: Welcome to Smart Bank Assistant.Are you an existing customer?User: YesBot: Please say your customer ID.

🧩 System Workflow
User (Voice/Text)        ↓Language Detection        ↓Speech-to-Text (if voice)        ↓Intent Detection        ↓Customer Identification        ↓Authentication (OTP Simulation)        ↓Banking Service Processing        ↓Fetch Data from Mock Banking System        ↓Generate Response        ↓Translate to User Language        ↓Text / Voice Response

🏗️ Technology Stack
Frontend
React + Vite
Backend
FastAPI (Python)
Voice Processing
SpeechRecognition APISpeechSynthesis API
Data Layer
JSON / Excel Mock Banking Data

📊 Features of the System
Existing Customer Features
Balance enquiryLast transactionAccount detailsCard statusCard balanceLoan EMI detailsKYC statusComplaint support
Non-Existing Customer Features
Savings account guidanceCredit card detailsLoan eligibilityRequired documentsBank product informationSales support
Voice Features
Speech recognitionVoice responseIVR-style interaction
Multilingual Features
Language detectionRegional language supportTranslated responses

🔐 Security Features
The system includes:


OTP-based verification (simulated)


Data masking


Secure session handling


Role-based logic separation


No sensitive data exposure



🚀 Benefits of the System
24/7 banking supportReduced call center workloadImproved customer experienceFaster issue resolutionMultilingual accessibilityReduced operational costScalable banking support platform

📈 Future Enhancements
Real Core Banking System integrationWhatsApp bankingAI-powered NLP enginesFraud detection alertsPersonalized banking recommendationsReal IVR phone integration

🏁 Conclusion
The proposed system delivers a modern AI-powered banking support solution capable of handling both customer service and product enquiry workflows through multilingual chat and voice interactions.
The assistant simulates real banking support operations while improving accessibility, efficiency, and customer satisfaction.

## Selected Stack
- Language: Python
- Frontend: React
- Backend: FastAPI
- Database: SQLite
- AI / Tools: None
- Deployment: Render

## Architecture
- React handles the user-facing workflows, starter pages, and client-side integration points.
- FastAPI provides the API surface, routing, services, and configuration layer.
- PostgreSQL is configured as the primary persistence layer through environment-driven settings.
- Setup, run scripts, and dependency manifests are generated server-side for a consistent starter layout.
- SQLite is configured as the primary persistence layer through environment-driven settings.

## Modules
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
- Auth Module: Authentication workflow and APIs.
  Key files: backend/app/routers/auth.py, backend/app/services/auth_service.py, frontend/src/pages/LoginPage.jsx

## Assumptions
- Fast Mode AI planning was unavailable, so the 100% runnable starter project uses the safe template-generated fallback.
- Template fallback preview was generated because the AI planner could not complete in time or returned invalid output: AI generation is unavailable because Ollama could not be reached at http://127.0.0.1:11434.
- Fast Mode used backend templates for standard files so project completeness was preserved without waiting for the model to write boilerplate.
- The project is split into frontend and backend folders to keep the full-stack boundary explicit.
- This output is a 100% runnable starter project after `.env` is filled, setup is run, and the run script is started. Business logic can still be customized afterward.
- SQLite was chosen as a lightweight local-first database default.
- Project-specific custom files were layered on top of the standard stack templates.
