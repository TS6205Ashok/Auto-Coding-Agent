# File Structure

## Final Generated Tree
```text
.env.example
.vscode
  launch.json
  tasks.json
FILE_STRUCTURE.md
FULL_RUNTIME_INSTRUCTIONS.md
MIGRATION_SUMMARY.md
PACKAGE_REQUIREMENTS.md
PROJECT_EXPLANATION.md
README.md
REQUIRED_INPUTS.md
SETUP_INSTRUCTIONS.md
__init__.py
backend
  app
    __init__.py
    config.py
    data
      dummy_customers.json
    database.py
    main.py
    models
      __init__.py
      base.py
      item.py
    routers
      __init__.py
      api.py
      auth.py
      banking.py
      chatbot.py
      complaints.py
      health.py
      items.py
      loans.py
      transactions.py
    schemas
      __init__.py
      health.py
      item.py
    services
      __init__.py
      app_service.py
      auth_service.py
      banking_service.py
      chatbot_service.py
      complaint_service.py
      domain_service.py
      intent_service.py
      item_service.py
      loan_service.py
      otp_service.py
      transaction_service.py
  requirements.txt
  run.bat
  run.sh
  setup.bat
  setup.sh
frontend
  index.html
  package.json
  run.bat
  run.sh
  setup.bat
  setup.sh
  src
    App.jsx
    components
      AppShell.jsx
      ChatWindow.jsx
      MessageBubble.jsx
    main.jsx
    pages
      AdminDashboard.jsx
      ChatbotPage.jsx
      ComplaintPage.jsx
      DashboardPage.jsx
      HomePage.jsx
      LoanPage.jsx
      LoginPage.jsx
      ReportPage.jsx
      TransactionsPage.jsx
    services
      api.js
      chatbotApi.js
    styles.css
  vite.config.js
run.bat
run.sh
setup.bat
setup.sh
```

## Included Modules
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
