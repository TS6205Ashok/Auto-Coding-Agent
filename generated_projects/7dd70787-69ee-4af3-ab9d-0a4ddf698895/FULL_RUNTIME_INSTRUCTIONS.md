# Full Runtime Instructions

## 1. PROJECT OVERVIEW
- Project: The Proposed System Is
- Generated version: Project Agent Generated Starter v1
- What this project does: The Proposed System Is is a 100% runnable starter project built around React + FastAPI. Fast Mode uses backend templates for all standard project structure so output quality stays complete while generation remains fast.
- Tech stack used:
- Language: Python
- Frontend: React
- Backend: FastAPI
- Database: SQLite
- AI / Tools: None
- Deployment: Render
- What should happen when it runs successfully: The backend server starts, the frontend opens or becomes available locally, and the UI can talk to the API.

## 2. RECOMMENDED IDE
- Primary IDE: VS Code
- Alternative IDE: PyCharm

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

## 3. REQUIRED EXTENSIONS / PLUGINS
- VS Code: Python extension
- VS Code: Pylance
- PyCharm: Python support is built in

## 4. SYSTEM REQUIREMENTS
- Git and a terminal available inside your IDE.
- Python 3.10+ (3.11+ recommended).
- Node.js 18+ (20+ recommended).
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
- `JWT_SECRET` (required): Secret used to sign authentication tokens.
- `OPENAI_API_KEY` (required): Used for AI chatbot responses.
- `VITE_API_BASE_URL` (optional): Frontend base URL for backend API calls.

| Input Name | Required | Example | Where To Enter | Purpose |
|---|---|---|---|---|
| APP_ENV | No | development | .env | Application environment name. |
| PORT | No | 8000 | .env | Local port used when the backend starts from the generated run scripts. |
| DATABASE_URL | Yes | sqlite:///./app.db | Terminal prompt or .env | SQLite connection string for local development. |
| JWT_SECRET | Yes | change-me-super-secret | Terminal prompt or .env | Secret used to sign authentication tokens. |
| OPENAI_API_KEY | Yes | sk-... | Terminal prompt or .env | Used for AI chatbot responses. |
| VITE_API_BASE_URL | No | http://localhost:8000 | .env | Frontend base URL for backend API calls. |

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
- Success looks like this: The backend server starts, the frontend opens or becomes available locally, and the UI can talk to the API.
- Problem statement handled by this starter: The proposed system is an AI-powered multilingual banking assistant designed to provide intelligent banking support through both text-based chatbot and voice-based IVR interactions.
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
- If needed, delete `node_modules` and reinstall with `npm install`.

## 12. MIGRATION NOTES
- Original stack: JavaScript / FastAPI
- New stack: JavaScript / Express
- Key changes:
- Migrated backend/runtime from FastAPI to Express.
- Limitations: this is a runnable rebuilt starter in the target stack, not a byte-for-byte source translation.

- Package manager: pip
