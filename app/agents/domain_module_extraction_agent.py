from __future__ import annotations

import logging

from app.agents.context import AgentWorkflowContext
from app.services import ai_service as ai
from app.services.architecture_registry import build_final_architecture_decision


logger = logging.getLogger(__name__)


class DomainModuleExtractionAgent:
    def run(self, context: AgentWorkflowContext) -> AgentWorkflowContext:
        description = "\n".join(
            [
                context.final_requirements,
                context.generation_context,
                context.problem_statement,
                context.prompt,
            ]
        ).lower()
        if self._is_banking_chatbot(description):
            self._apply_banking_chatbot_profile(context)
        self._apply_general_domain_files(context, description)
        logger.info(
            "DomainModuleExtractionAgent extracted domain=%s files=%s modules=%s",
            context.domain_project_type or "generic",
            len(context.domain_required_files),
            len(context.domain_modules),
        )
        return context

    def _is_banking_chatbot(self, text: str) -> bool:
        banking_terms = [
            "banking",
            "account balance",
            "recent transactions",
            "transaction",
            "debit card",
            "credit card",
            "loan emi",
            "complaint status",
            "branch",
            "atm",
            "otp",
            "ivr",
            "customer support chatbot",
            "banking api",
        ]
        return "chatbot" in text and any(term in text for term in banking_terms)

    def _apply_banking_chatbot_profile(self, context: AgentWorkflowContext) -> None:
        context.domain_project_type = "banking_chatbot"
        if not context.is_user_confirmed_stack:
            context.requested_stack = {
                **ai.normalize_stack_selection(context.requested_stack),
                "language": "Python",
                "frontend": "React",
                "backend": "FastAPI",
                "database": "SQLite",
                "aiTools": "None",
                "deployment": "Render",
            }
            context.final_architecture = build_final_architecture_decision(
                prompt=context.generation_context or context.prompt,
                requested_stack=context.requested_stack,
                inferred_stack=context.requested_stack,
                declared_project_type="full-stack",
                project_category=context.project_category,
                migration_summary=context.migration_summary,
                is_migrated=context.migration_active or context.migration_requested,
                stack_selection_source=context.stack_selection_source,
                is_user_confirmed_stack=False,
            )
            context.selected_stack = context.final_architecture.selected_stack
            context.project_kind = ai.determine_project_kind(context.selected_stack, "full-stack")
            context.template_family = ""

        context.domain_modules = [
            {
                "name": "Chatbot Module",
                "purpose": "Handles customer messages, conversation state, OTP prompts, and response formatting.",
                "keyFiles": ["backend/app/routers/chatbot.py", "backend/app/services/chatbot_service.py"],
            },
            {
                "name": "Banking Service Module",
                "purpose": "Provides dummy banking operations for balance, transactions, cards, loans, complaints, and locations.",
                "keyFiles": ["backend/app/routers/banking.py", "backend/app/services/banking_service.py"],
            },
            {
                "name": "Intent Detection Module",
                "purpose": "Maps customer messages to supported banking intents.",
                "keyFiles": ["backend/app/services/intent_service.py"],
            },
            {
                "name": "Dummy Banking Database",
                "purpose": "Stores sample customer, card, loan, complaint, OTP, branch, and ATM data.",
                "keyFiles": ["backend/app/data/dummy_customers.json"],
            },
            {
                "name": "Frontend Chat Interface",
                "purpose": "Provides a React chat page, message bubbles, and API client for the banking assistant.",
                "keyFiles": [
                    "frontend/src/pages/ChatbotPage.jsx",
                    "frontend/src/components/ChatWindow.jsx",
                    "frontend/src/components/MessageBubble.jsx",
                    "frontend/src/services/chatbotApi.js",
                ],
            },
        ]
        context.domain_required_files = [
            {"path": "backend/app/routers/chatbot.py", "purpose": "FastAPI chat endpoint for customer messages."},
            {"path": "backend/app/routers/banking.py", "purpose": "FastAPI banking operation endpoints."},
            {"path": "backend/app/services/chatbot_service.py", "purpose": "Conversation flow and banking response orchestration."},
            {"path": "backend/app/services/banking_service.py", "purpose": "Dummy banking data loader and operations."},
            {"path": "backend/app/services/intent_service.py", "purpose": "Banking intent detection from customer messages."},
            {"path": "backend/app/data/dummy_customers.json", "purpose": "Sample banking customer data for runnable demos."},
            {"path": "frontend/src/pages/ChatbotPage.jsx", "purpose": "Main banking chatbot page."},
            {"path": "frontend/src/components/ChatWindow.jsx", "purpose": "Interactive chat window with input and send flow."},
            {"path": "frontend/src/components/MessageBubble.jsx", "purpose": "User and bot message bubble component."},
            {"path": "frontend/src/services/chatbotApi.js", "purpose": "Frontend API client for the chat endpoint."},
        ]

    def _apply_general_domain_files(self, context: AgentWorkflowContext, text: str) -> None:
        additions: list[dict[str, str]] = []
        modules: list[dict[str, object]] = []
        has_backend = bool(context.project_kind.get("hasBackend"))
        has_frontend = bool(context.project_kind.get("hasFrontend"))

        def add(path: str, purpose: str) -> None:
            additions.append({"path": path, "purpose": purpose})

        def module(name: str, purpose: str, paths: list[str]) -> None:
            modules.append({"name": name, "purpose": purpose, "keyFiles": paths})

        if "chatbot" in text and context.domain_project_type != "banking_chatbot":
            paths = []
            if has_backend:
                paths.extend(["backend/app/routers/chatbot.py", "backend/app/services/chatbot_service.py"])
            if has_frontend:
                paths.extend([
                    "frontend/src/pages/ChatbotPage.jsx",
                    "frontend/src/components/ChatWindow.jsx",
                    "frontend/src/services/chatbotApi.js",
                ])
            if paths:
                for path in paths:
                    add(path, "Chatbot conversation workflow file.")
                module("Chatbot Module", "Handles chat messages and the frontend conversation UI.", paths)

        feature_map = [
            (("admin", "administrator"), "Admin", "admin", "AdminDashboard", "Admin management dashboard and APIs."),
            (("report", "analytics"), "Reports", "reports", "ReportPage", "Reporting workflow and APIs."),
            (("payment", "checkout", "subscription"), "Payments", "payments", "PaymentPage", "Payment workflow and APIs."),
            (("complaint",), "Complaints", "complaints", "ComplaintPage", "Complaint tracking workflow and APIs."),
            (("transaction", "transactions"), "Transactions", "transactions", "TransactionsPage", "Transaction lookup workflow and APIs."),
            (("loan", "emi"), "Loans", "loans", "LoanPage", "Loan and EMI workflow and APIs."),
            (("branch", "atm", "location"), "Locations", "locations", "LocationsPage", "Branch and ATM location workflow and APIs."),
            (("inventory", "stock"), "Inventory", "inventory", "InventoryPage", "Inventory workflow and APIs."),
            (("login", "auth", "authentication"), "Auth", "auth", "LoginPage", "Authentication workflow and APIs."),
            (("profile",), "Profile", "profile", "ProfilePage", "Customer profile workflow and APIs."),
            (("upload", "file upload"), "Uploads", "uploads", "UploadPage", "File upload workflow and APIs."),
            (("search",), "Search", "search", "SearchPage", "Search workflow and APIs."),
        ]
        for keywords, name, slug, page, purpose in feature_map:
            if not any(keyword in text for keyword in keywords):
                continue
            paths = []
            if has_backend:
                paths.extend([
                    f"backend/app/routers/{slug}.py",
                    f"backend/app/services/{slug.rstrip('s')}_service.py",
                ])
            if has_frontend:
                paths.append(f"frontend/src/pages/{page}.jsx")
            if not paths:
                continue
            for path in paths:
                add(path, purpose)
            module(f"{name} Module", purpose, paths)

        if has_backend and ("intent detection" in text or "intent" in text):
            add("backend/app/services/intent_service.py", "Intent detection service for routing user requests.")
        if has_backend and "otp" in text:
            add("backend/app/services/otp_service.py", "OTP verification helper for secure workflows.")
        if has_backend and ("email" in text or "smtp" in text):
            add("backend/app/services/email_service.py", "Email and SMTP notification service.")

        existing_paths = {item.get("path") for item in context.domain_required_files}
        context.domain_required_files.extend(
            item for item in additions if item.get("path") and item.get("path") not in existing_paths
        )
        existing_modules = {item.get("name") for item in context.domain_modules}
        context.domain_modules.extend(
            item for item in modules if item.get("name") and item.get("name") not in existing_modules
        )
