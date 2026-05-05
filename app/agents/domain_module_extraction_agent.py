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
