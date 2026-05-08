from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

import httpx

from app.services import ai_service as ai


logger = logging.getLogger(__name__)

CHAT_ACTIONS = {
    "none",
    "show_code_in_chat",
    "ask_generate_zip",
    "update_idea",
    "update_requirements",
    "add_files",
    "remove_files",
    "add_feature",
    "remove_feature",
    "change_stack",
    "update_required_inputs",
    "generate_project",
    "regenerate_project",
    "pause_agent_and_update",
    "cancel_pending_change",
}

CHAT_INTENTS = {
    "chat_intent",
    "planning_intent",
    "generation_intent",
    "repair_intent",
    "ide_intent",
    "file_generation_intent",
}


@dataclass(slots=True)
class ChatCoordinatorResult:
    reply: str
    message: str = ""
    intent: str = "chat_intent"
    action: str = "none"
    suggestedProjectDescription: str = ""
    updatedIdea: str = ""
    updatedRequirements: str = ""
    requestedFiles: list[dict[str, Any]] = field(default_factory=list)
    filesToRemove: list[dict[str, Any]] = field(default_factory=list)
    featuresToAdd: list[str] = field(default_factory=list)
    featuresToRemove: list[str] = field(default_factory=list)
    updatedStack: dict[str, Any] = field(default_factory=dict)
    requiredInputs: list[dict[str, Any]] = field(default_factory=list)
    needsConfirmation: bool = False
    confirmationMessage: str = ""
    shouldGenerate: bool = False
    shouldRegenerate: bool = False
    shouldPauseAgent: bool = False
    confidence: str = "medium"
    llmModeUsed: str = "free_rule_based"

    def to_api_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if payload["intent"] not in CHAT_INTENTS:
            payload["intent"] = "chat_intent"
        if payload["action"] not in CHAT_ACTIONS:
            payload["action"] = "none"
        if not payload["reply"]:
            payload["reply"] = "I understood that. Tell me if you want to generate or modify the project."
        if not payload["message"]:
            payload["message"] = payload["reply"]
        if not payload["suggestedProjectDescription"] and payload["intent"] in {"file_generation_intent", "generation_intent"}:
            payload["suggestedProjectDescription"] = payload.get("updatedIdea") or payload.get("updatedRequirements") or ""
        return payload


class ChatCoordinatorAgent:
    def __init__(self) -> None:
        self.default_base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.default_model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:latest")
        self.fallback_model = os.getenv("OLLAMA_FALLBACK_MODEL", "codellama:7b")
        self.timeout_seconds = float(os.getenv("OLLAMA_CHAT_TIMEOUT_SECONDS", "8"))

    async def run(
        self,
        *,
        message: str,
        conversation: Sequence[Mapping[str, Any]] | None = None,
        current_idea: str = "",
        current_preview: Mapping[str, Any] | None = None,
        selected_stack: Mapping[str, Any] | None = None,
        agent_state: str = "idle",
        pending_corrections: Sequence[Mapping[str, Any]] | None = None,
        llm_mode: str = "auto",
    ) -> dict[str, Any]:
        clean_message = str(message or "").strip()
        if not clean_message:
            return ChatCoordinatorResult(
                reply="Type a project idea, change request, or stack update and I will help shape it.",
                confidence="high",
            ).to_api_dict()

        mode = str(llm_mode or "auto").strip() or "auto"
        if mode != "free_rule_based":
            ollama_result = await self._try_ollama(
                message=clean_message,
                conversation=conversation or [],
                current_idea=current_idea,
                current_preview=current_preview or {},
                selected_stack=selected_stack or {},
                agent_state=agent_state,
                pending_corrections=pending_corrections or [],
                force=mode == "ollama",
            )
            if ollama_result is not None:
                return ollama_result.to_api_dict()

        return self._rule_based(
            clean_message,
            current_idea=current_idea,
            current_preview=current_preview or {},
            selected_stack=selected_stack or {},
            agent_state=agent_state,
            pending_corrections=pending_corrections or [],
        ).to_api_dict()

    async def _try_ollama(
        self,
        *,
        message: str,
        conversation: Sequence[Mapping[str, Any]],
        current_idea: str,
        current_preview: Mapping[str, Any],
        selected_stack: Mapping[str, Any],
        agent_state: str,
        pending_corrections: Sequence[Mapping[str, Any]],
        force: bool,
    ) -> ChatCoordinatorResult | None:
        base_url = os.getenv("OLLAMA_BASE_URL", self.default_base_url).strip().rstrip("/")
        model = os.getenv("OLLAMA_MODEL", self.default_model).strip() or self.default_model
        fallback_model = os.getenv("OLLAMA_FALLBACK_MODEL", self.fallback_model).strip() or self.fallback_model
        if not base_url and force:
            base_url = self.default_base_url
        if not base_url:
            return None
        prompt = self._build_ollama_prompt(
            message=message,
            conversation=conversation,
            current_idea=current_idea,
            current_preview=current_preview,
            selected_stack=selected_stack,
            agent_state=agent_state,
            pending_corrections=pending_corrections,
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                payload = await self._post_ollama_chat(client, base_url, model, prompt)
            raw_text = str(payload.get("response") or "").strip()
            parsed = json.loads(ai.extract_json_object(raw_text))
            result = self._normalize_result(parsed, llm_mode_used="ollama")
            return result
        except Exception as first_exc:
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    payload = await self._post_ollama_chat(client, base_url, fallback_model, prompt)
                raw_text = str(payload.get("response") or "").strip()
                parsed = json.loads(ai.extract_json_object(raw_text))
                return self._normalize_result(parsed, llm_mode_used="ollama_fallback")
            except Exception as fallback_exc:
                logger.info(
                    "ChatCoordinatorAgent Ollama unavailable; using rule-based fallback: primary=%s fallback=%s",
                    first_exc,
                    fallback_exc,
                )
                return None

    async def _post_ollama_chat(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        model: str,
        prompt: str,
    ) -> dict[str, Any]:
        response = await client.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
        )
        response.raise_for_status()
        return response.json()

    def _build_ollama_prompt(
        self,
        *,
        message: str,
        conversation: Sequence[Mapping[str, Any]],
        current_idea: str,
        current_preview: Mapping[str, Any],
        selected_stack: Mapping[str, Any],
        agent_state: str,
        pending_corrections: Sequence[Mapping[str, Any]],
    ) -> str:
        state = {
            "message": message,
            "conversation": list(conversation)[-8:],
            "currentIdea": current_idea,
            "hasPreview": bool(current_preview),
            "selectedStack": dict(selected_stack or {}),
            "agentState": agent_state,
            "pendingCorrections": list(pending_corrections or []),
        }
        return (
            "You are Project Assistant, a ChatGPT-like AI software engineer. You can answer normal questions, "
            "generate code, plan projects, explain errors, and help create downloadable projects. Do not refuse "
            "just because no project is locked. If the user asks to create a webpage/app/project, provide useful "
            "code or offer project generation. Always return strict JSON. "
            "Set intent to one of: chat_intent, planning_intent, generation_intent, repair_intent, ide_intent, file_generation_intent. "
            "For file_generation_intent, generate useful code in reply and use action show_code_in_chat or ask_generate_zip. "
            "Only set generation_intent/action generate_project when the user explicitly says generate project, "
            "generate this, build starter, build it now, or confirm and generate. "
            "Normal project ideas, questions, stack suggestions, and plans are planning_intent or chat_intent. "
            "Preview modifications are repair_intent and require confirmation. Never require paid APIs for chatbot behavior.\n\n"
            "Allowed actions: none, show_code_in_chat, ask_generate_zip, update_idea, update_requirements, generate_project, regenerate_project, "
            "add_files, remove_files, add_feature, remove_feature, change_stack, update_required_inputs, "
            "pause_agent_and_update, cancel_pending_change.\n"
            "Return fields: reply, message, intent, action, suggestedProjectDescription, updatedIdea, updatedRequirements, requestedFiles, filesToRemove, "
            "featuresToAdd, featuresToRemove, updatedStack, requiredInputs, needsConfirmation, "
            "confirmationMessage, shouldGenerate, shouldRegenerate, shouldPauseAgent, confidence.\n\n"
            f"STATE:\n{json.dumps(state, indent=2)}"
        )

    def _normalize_result(self, payload: Mapping[str, Any], *, llm_mode_used: str) -> ChatCoordinatorResult:
        result = ChatCoordinatorResult(
            reply=str(payload.get("reply") or payload.get("message") or "").strip(),
            message=str(payload.get("message") or payload.get("reply") or "").strip(),
            intent=str(payload.get("intent") or "chat_intent").strip(),
            action=str(payload.get("action") or "none").strip(),
            suggestedProjectDescription=str(payload.get("suggestedProjectDescription") or "").strip(),
            updatedIdea=str(payload.get("updatedIdea") or "").strip(),
            updatedRequirements=str(payload.get("updatedRequirements") or "").strip(),
            requestedFiles=self._normalize_requested_files(payload.get("requestedFiles"), {}),
            filesToRemove=self._normalize_files_to_remove(payload.get("filesToRemove")),
            featuresToAdd=ai.normalize_string_list(payload.get("featuresToAdd")),
            featuresToRemove=ai.normalize_string_list(payload.get("featuresToRemove")),
            updatedStack=self._normalize_updated_stack(payload.get("updatedStack")),
            requiredInputs=ai.normalize_required_inputs(payload.get("requiredInputs")),
            needsConfirmation=bool(payload.get("needsConfirmation")),
            confirmationMessage=str(payload.get("confirmationMessage") or "").strip(),
            shouldGenerate=bool(payload.get("shouldGenerate")),
            shouldRegenerate=bool(payload.get("shouldRegenerate")),
            shouldPauseAgent=bool(payload.get("shouldPauseAgent")),
            confidence=str(payload.get("confidence") or "medium").strip() or "medium",
            llmModeUsed=llm_mode_used,
        )
        if result.action not in CHAT_ACTIONS:
            result.action = "none"
        if result.intent not in CHAT_INTENTS:
            result.intent = self._intent_for_action(result.action, result.shouldGenerate, result.shouldRegenerate)
        if result.action in {"show_code_in_chat", "ask_generate_zip"}:
            result.intent = "file_generation_intent"
            result.shouldGenerate = False
        if result.intent != "generation_intent" and result.shouldGenerate:
            result.shouldGenerate = False
        if result.intent not in {"repair_intent", "generation_intent", "file_generation_intent"} and result.shouldRegenerate:
            result.shouldRegenerate = False
        if result.intent in {"chat_intent", "planning_intent", "ide_intent"}:
            result.requestedFiles = []
            result.filesToRemove = []
            result.featuresToAdd = []
            result.featuresToRemove = []
            result.requiredInputs = []
        return result

    def _rule_based(
        self,
        message: str,
        *,
        current_idea: str,
        current_preview: Mapping[str, Any],
        selected_stack: Mapping[str, Any],
        agent_state: str,
        pending_corrections: Sequence[Mapping[str, Any]],
    ) -> ChatCoordinatorResult:
        del pending_corrections
        lowered = message.lower()
        has_preview = bool(current_preview)
        normalized_stack = ai.normalize_stack_selection(selected_stack or current_preview.get("selectedStack"))
        mode_running = agent_state == "running"

        if any(word in lowered for word in ["cancel", "discard", "never mind", "nevermind"]):
            return ChatCoordinatorResult(
                reply="Okay, I canceled the pending chat suggestion. I did not change the project state.",
                intent="chat_intent",
                action="cancel_pending_change",
                confidence="high",
            )

        if self._looks_like_ide_intent(lowered):
            return ChatCoordinatorResult(
                reply=self._ide_reply(lowered, has_preview),
                intent="ide_intent",
                action="none",
                confidence="high",
            )

        required_inputs = self._detect_required_inputs(lowered)
        if self._looks_like_generation_intent(lowered):
            idea = current_idea or message
            return ChatCoordinatorResult(
                reply=(
                    "Ready to generate. I will only start the project pipeline after you confirm, "
                    "then I will build a fresh contract from the current description and selected stack."
                ),
                intent="generation_intent",
                action="generate_project",
                updatedIdea=idea,
                updatedRequirements=self._draft_requirements(idea),
                requiredInputs=required_inputs,
                needsConfirmation=True,
                confirmationMessage="Generate this project now?",
                shouldGenerate=True,
                confidence="high",
            )

        if self._looks_like_explanation_question(lowered):
            return ChatCoordinatorResult(
                reply=self._answer_general_question(message, lowered, normalized_stack),
                intent="chat_intent",
                action="none",
                confidence="high",
            )

        if not has_preview and self._looks_like_code_generation_request(lowered):
            return ChatCoordinatorResult(
                reply=self._code_generation_reply(message, lowered),
                intent="file_generation_intent",
                action="ask_generate_zip",
                suggestedProjectDescription=message,
                updatedIdea=message,
                updatedRequirements=self._draft_requirements(message),
                needsConfirmation=False,
                shouldGenerate=False,
                confidence="high",
            )

        updated_stack, last_modified = self._detect_stack_change(lowered, normalized_stack)
        if updated_stack:
            updated_stack.update(
                {
                    "source": "chatbot_stack_change",
                    "isUserConfirmedStack": True,
                    "isDirty": True,
                    "lastModifiedField": last_modified,
                }
            )
            return ChatCoordinatorResult(
                reply=self._stack_change_reply(updated_stack, has_preview),
                intent="repair_intent" if has_preview else "planning_intent",
                action="change_stack",
                updatedStack=updated_stack,
                needsConfirmation=True,
                confirmationMessage="Apply this stack change?" + (" Regenerate the preview after applying it?" if has_preview else ""),
                shouldRegenerate=has_preview,
                confidence="high",
            )

        requested_files = self._detect_requested_files(lowered, normalized_stack)
        files_to_remove = self._detect_files_to_remove(lowered, current_preview, normalized_stack)
        features_to_add = self._detect_features_to_add(lowered)
        features_to_remove = self._detect_features_to_remove(lowered)
        if not requested_files and not has_preview and self._looks_like_file_request(lowered):
            return ChatCoordinatorResult(
                reply=self._code_generation_reply(message, lowered),
                intent="file_generation_intent",
                action="ask_generate_zip",
                suggestedProjectDescription=message,
                updatedIdea=message,
                updatedRequirements=self._draft_requirements(message),
                needsConfirmation=False,
                shouldGenerate=False,
                confidence="high",
            )
        looks_like_change = has_preview and (
            requested_files
            or files_to_remove
            or features_to_add
            or features_to_remove
            or required_inputs
            or any(word in lowered for word in ["add", "include", "improve", "change", "modify", "remove", "delete", "otp", "payment", "report", "dashboard", "login", "csv", "export"])
        )
        if mode_running and looks_like_change:
            return ChatCoordinatorResult(
                reply="I captured that correction and will apply it to the current generation before the final preview is accepted.",
                intent="repair_intent",
                action="pause_agent_and_update",
                updatedRequirements=self._merge_requirements(current_idea, message),
                requestedFiles=requested_files,
                filesToRemove=files_to_remove,
                featuresToAdd=features_to_add,
                featuresToRemove=features_to_remove,
                requiredInputs=required_inputs,
                needsConfirmation=True,
                confirmationMessage="Apply this correction to the running generation?",
                shouldPauseAgent=True,
                shouldRegenerate=True,
                confidence="high",
            )
        if looks_like_change:
            action = "add_files" if requested_files else "update_requirements"
            if files_to_remove:
                action = "remove_files"
            elif features_to_add and not requested_files:
                action = "add_feature"
            elif features_to_remove and not files_to_remove:
                action = "remove_feature"
            elif required_inputs and not requested_files:
                action = "update_required_inputs"
            return ChatCoordinatorResult(
                reply=self._correction_reply(
                    requested_files,
                    required_inputs,
                    message,
                    files_to_remove,
                    features_to_add,
                    features_to_remove,
                ),
                intent="repair_intent",
                action=action,
                updatedRequirements=self._merge_requirements(current_idea or str(current_preview.get("problemStatement") or ""), message),
                requestedFiles=requested_files,
                filesToRemove=files_to_remove,
                featuresToAdd=features_to_add,
                featuresToRemove=features_to_remove,
                requiredInputs=required_inputs,
                needsConfirmation=True,
                confirmationMessage="Apply these corrections and regenerate the project?",
                shouldRegenerate=True,
                confidence="high",
            )

        if self._looks_like_planning_intent(lowered):
            draft = self._draft_requirements(message)
            return ChatCoordinatorResult(
                reply=self._planning_reply(message, normalized_stack),
                intent="planning_intent",
                action="update_requirements",
                updatedIdea=message,
                updatedRequirements=draft,
                requiredInputs=required_inputs,
                needsConfirmation=False,
                confidence="high",
            )

        return ChatCoordinatorResult(
            reply=self._conversation_reply(message, normalized_stack, bool(current_idea), has_preview),
            intent="chat_intent",
            action="none",
            requiredInputs=required_inputs,
            needsConfirmation=False,
            confidence="medium",
        )

    def _intent_for_action(self, action: str, should_generate: bool, should_regenerate: bool) -> str:
        if should_generate or action == "generate_project":
            return "generation_intent"
        if should_regenerate or action in {
            "regenerate_project",
            "add_files",
            "remove_files",
            "add_feature",
            "remove_feature",
            "change_stack",
            "update_required_inputs",
            "pause_agent_and_update",
        }:
            return "repair_intent"
        if action in {"update_idea", "update_requirements"}:
            return "planning_intent"
        return "chat_intent"

    def _looks_like_generation_intent(self, lowered: str) -> bool:
        phrases = [
            "generate project",
            "generate this",
            "generate it",
            "create files",
            "create the files",
            "build starter",
            "build a starter",
            "build it now",
            "confirm and generate",
            "finalize and generate",
        ]
        return any(phrase in lowered for phrase in phrases)

    def _looks_like_ide_intent(self, lowered: str) -> bool:
        return any(
            phrase in lowered
            for phrase in [
                "open ide",
                "open the ide",
                "start ide",
                "close ide",
                "ide status",
                "download zip",
                "download project",
                "create zip",
                "package zip",
            ]
        )

    def _looks_like_explanation_question(self, lowered: str) -> bool:
        question_starters = ("what is", "what are", "why", "how does", "how do", "explain", "compare")
        return lowered.endswith("?") or lowered.startswith(question_starters)

    def _looks_like_planning_intent(self, lowered: str) -> bool:
        planning_terms = [
            "plan",
            "suggest",
            "recommend",
            "architecture",
            "stack",
            "should i use",
            "project idea",
            "requirements",
            "frontend-only",
            "backend-only",
            "full-stack",
            "full stack",
            "puzzle game",
            "app",
            "website",
            "portal",
            "dashboard",
            "system",
        ]
        return any(term in lowered for term in planning_terms)

    def _looks_like_code_generation_request(self, lowered: str) -> bool:
        create_terms = ["generate", "create", "build", "write", "make", "code"]
        target_terms = [
            "webpage",
            "web page",
            "html",
            "css",
            "javascript",
            "login page",
            "form",
            "component",
            "script",
            "python",
            "function",
            "file",
            "app",
            "website",
        ]
        return any(term in lowered for term in create_terms) and any(term in lowered for term in target_terms)

    def _ide_reply(self, lowered: str, has_preview: bool) -> str:
        if "close" in lowered:
            return "Use the Close IDE control after a project workspace has been created. I will not touch the project pipeline for this."
        if "download" in lowered or "zip" in lowered or "package" in lowered:
            return (
                "ZIP creation belongs to the packaging step. Generate and review a preview first, then use Create ZIP. "
                "I will not run validation or packaging from a normal chat message."
            )
        if has_preview:
            return "After you create the ZIP/workspace, use Open IDE to launch it. Chat itself will not trigger validation or generation."
        return "There is no generated workspace to open yet. We can discuss or plan first, then generate only when you explicitly ask."

    def _stack_change_reply(self, updated_stack: Mapping[str, Any], has_preview: bool) -> str:
        stack_bits = [
            str(updated_stack.get("language") or "Auto"),
            str(updated_stack.get("frontend") or "Auto"),
            str(updated_stack.get("backend") or "Auto"),
            str(updated_stack.get("database") or "Auto"),
        ]
        suffix = " Because a preview exists, applying this is a repair/regeneration action." if has_preview else " I can stage this preference without generating files."
        return f"I detected this stack preference: {' / '.join(stack_bits)}.{suffix}"

    def _answer_general_question(self, message: str, lowered: str, selected_stack: Mapping[str, str]) -> str:
        del message
        if "fastapi" in lowered:
            return (
                "**FastAPI** is a Python web framework for building APIs. It is a good fit when you want typed request/response models, "
                "automatic OpenAPI docs, and a straightforward backend for React or static frontends.\n\n"
                "Use it when your project needs real backend routes, auth, persistence, or integrations. For frontend-only games or static tools, skip it."
            )
        if "react" in lowered and ("vanilla" in lowered or "html" in lowered or "javascript" in lowered):
            return (
                "**React vs vanilla JavaScript:**\n\n"
                "- Use **React** for component-heavy apps, dashboards, routing, and stateful UI.\n"
                "- Use **HTML/CSS/JavaScript** for small games, landing pages, simple widgets, and projects with no build step.\n\n"
                f"Current selected frontend: `{selected_stack.get('frontend', 'Auto')}`."
            )
        if "backend" in lowered:
            return (
                "A backend is useful for data storage, authentication, server-side validation, scheduled work, and external API secrets. "
                "If the app can run entirely in the browser and does not need protected data or server APIs, frontend-only is cleaner."
            )
        return (
            "Happy to explain. I can answer questions, compare stack options, or help shape the project plan without starting generation. "
            "Tell me the technology or decision you want to unpack."
        )

    def _code_generation_reply(self, message: str, lowered: str) -> str:
        if "login" in lowered and ("congrat" in lowered or "password" in lowered or "ashok" in lowered):
            return (
                "Here is a complete single-file webpage you can run directly in a browser. It uses username `ashok` and password `Ashok@123`, then shows a congratulations screen.\n\n"
                "```html\n"
                "<!doctype html>\n"
                "<html lang=\"en\">\n"
                "<head>\n"
                "  <meta charset=\"UTF-8\" />\n"
                "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n"
                "  <title>Ashok Login</title>\n"
                "  <style>\n"
                "    body {\n"
                "      margin: 0;\n"
                "      min-height: 100vh;\n"
                "      display: grid;\n"
                "      place-items: center;\n"
                "      font-family: Arial, sans-serif;\n"
                "      background: linear-gradient(135deg, #0f766e, #2563eb);\n"
                "      color: #111827;\n"
                "    }\n"
                "    .card {\n"
                "      width: min(92vw, 380px);\n"
                "      padding: 28px;\n"
                "      border-radius: 18px;\n"
                "      background: white;\n"
                "      box-shadow: 0 24px 70px rgba(15, 23, 42, 0.28);\n"
                "    }\n"
                "    h1 { margin: 0 0 18px; color: #0f172a; }\n"
                "    label { display: block; margin-top: 14px; font-weight: 700; }\n"
                "    input {\n"
                "      width: 100%;\n"
                "      box-sizing: border-box;\n"
                "      margin-top: 6px;\n"
                "      padding: 12px;\n"
                "      border: 1px solid #cbd5e1;\n"
                "      border-radius: 10px;\n"
                "      font-size: 16px;\n"
                "    }\n"
                "    button {\n"
                "      width: 100%;\n"
                "      margin-top: 20px;\n"
                "      padding: 13px;\n"
                "      border: 0;\n"
                "      border-radius: 10px;\n"
                "      background: #0f766e;\n"
                "      color: white;\n"
                "      font-size: 16px;\n"
                "      font-weight: 800;\n"
                "      cursor: pointer;\n"
                "    }\n"
                "    .error { margin-top: 12px; color: #dc2626; font-weight: 700; }\n"
                "    .success { text-align: center; }\n"
                "    .success h1 { font-size: 34px; color: #16a34a; }\n"
                "    .tag { display: inline-block; margin-top: 10px; padding: 8px 12px; border-radius: 999px; background: #dcfce7; color: #166534; font-weight: 800; }\n"
                "  </style>\n"
                "</head>\n"
                "<body>\n"
                "  <main class=\"card\" id=\"app\">\n"
                "    <h1>Welcome Back</h1>\n"
                "    <label for=\"userId\">User ID</label>\n"
                "    <input id=\"userId\" autocomplete=\"username\" placeholder=\"Enter user id\" />\n"
                "    <label for=\"password\">Password</label>\n"
                "    <input id=\"password\" type=\"password\" autocomplete=\"current-password\" placeholder=\"Enter password\" />\n"
                "    <button onclick=\"login()\">Login</button>\n"
                "    <p class=\"error\" id=\"error\"></p>\n"
                "  </main>\n"
                "  <script>\n"
                "    function login() {\n"
                "      const userId = document.getElementById('userId').value.trim();\n"
                "      const password = document.getElementById('password').value;\n"
                "      const error = document.getElementById('error');\n"
                "      if (userId === 'ashok' && password === 'Ashok@123') {\n"
                "        document.getElementById('app').innerHTML = `\n"
                "          <section class=\"success\">\n"
                "            <h1>Congratulations!</h1>\n"
                "            <p>You logged in successfully.</p>\n"
                "            <span class=\"tag\">Welcome, Ashok</span>\n"
                "          </section>`;\n"
                "      } else {\n"
                "        error.textContent = 'Invalid user id or password.';\n"
                "      }\n"
                "    }\n"
                "  </script>\n"
                "</body>\n"
                "</html>\n"
                "```\n\n"
                "I can also generate this as a downloadable project ZIP with separate `index.html`, CSS, and JavaScript files."
            )
        return (
            f"I can help build that. Here is a compact starter you can adapt for: **{message.strip()}**\n\n"
            "```html\n"
            "<!doctype html>\n"
            "<html lang=\"en\">\n"
            "<head>\n"
            "  <meta charset=\"UTF-8\" />\n"
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n"
            "  <title>Starter Page</title>\n"
            "  <style>body{font-family:Arial,sans-serif;margin:40px;line-height:1.5}button{padding:10px 14px}</style>\n"
            "</head>\n"
            "<body>\n"
            "  <h1>Starter Page</h1>\n"
            "  <p>Edit this page for your exact workflow.</p>\n"
            "  <button onclick=\"alert('It works!')\">Try it</button>\n"
            "</body>\n"
            "</html>\n"
            "```\n\n"
            "Use **Generate Project** if you want me to turn this request into a ZIP-ready project structure."
        )

    def _planning_reply(self, message: str, selected_stack: Mapping[str, str]) -> str:
        project_name = ai.clean_project_name(None, message)
        suggested_stack = self._suggest_stack_for_text(message.lower(), selected_stack)
        return (
            f"## Project Plan: {project_name}\n\n"
            "### Goal\n"
            f"{message.strip()}\n\n"
            "### Suggested Stack\n"
            f"- Language: `{suggested_stack['language']}`\n"
            f"- Frontend: `{suggested_stack['frontend']}`\n"
            f"- Backend: `{suggested_stack['backend']}`\n"
            f"- Database: `{suggested_stack['database']}`\n\n"
            "### First Modules\n"
            "- Core user workflow\n"
            "- Polished starter UI\n"
            "- Local setup and run instructions\n"
            "- Validation-ready file structure once generation is confirmed\n\n"
            "### Follow-up Questions\n"
            "1. Should this be frontend-only, backend-only, or full-stack?\n"
            "2. What is the most important user action?\n"
            "3. Do you need persistence, login, or external APIs?\n\n"
            "I will not generate files until you explicitly say `generate project`, `create files`, or `build starter`."
        )

    def _conversation_reply(
        self,
        message: str,
        selected_stack: Mapping[str, str],
        has_idea: bool,
        has_preview: bool,
    ) -> str:
        context_note = "I have a preview in context." if has_preview else ("I can use the current idea as context." if has_idea else "I can help directly from your latest message.")
        return (
            f"{context_note} I can help discuss, plan, compare stacks, or answer questions without running the generator.\n\n"
            f"You said: {message}\n\n"
            f"Current stack signal: `{selected_stack.get('language', 'Auto')}` / `{selected_stack.get('frontend', 'Auto')}` / `{selected_stack.get('backend', 'Auto')}`."
        )

    def _suggest_stack_for_text(self, lowered: str, selected_stack: Mapping[str, str]) -> dict[str, str]:
        stack = ai.normalize_stack_selection(selected_stack)
        if "puzzle" in lowered or "game" in lowered or "frontend-only" in lowered:
            return {
                "language": "JavaScript",
                "frontend": "HTML/CSS/JavaScript",
                "backend": "None",
                "database": "None",
                "aiTools": "None",
                "deployment": "None",
            }
        if "api" in lowered or "backend" in lowered:
            return {
                "language": "Python",
                "frontend": "None",
                "backend": "FastAPI",
                "database": "SQLite",
                "aiTools": "None",
                "deployment": "Render",
            }
        if any(value not in {"", "Auto"} for value in stack.values()):
            return stack
        return {
            "language": "Python",
            "frontend": "React",
            "backend": "FastAPI",
            "database": "SQLite",
            "aiTools": "None",
            "deployment": "Render",
        }

    def _detect_stack_change(self, lowered: str, selected_stack: Mapping[str, str]) -> tuple[dict[str, Any], str]:
        stack = dict(selected_stack)
        if "spring boot" in lowered or "use java" in lowered or "backend to java" in lowered:
            stack.update({"language": "Java", "backend": "Spring Boot", "frontend": stack.get("frontend", "None")})
            return stack, "backend" if "backend" in lowered or "spring boot" in lowered else "language"
        if "fastapi" in lowered:
            stack.update({"language": "Python", "backend": "FastAPI"})
            return stack, "backend"
        if "flask" in lowered:
            stack.update({"language": "Python", "backend": "Flask"})
            return stack, "backend"
        if "express" in lowered or "node" in lowered:
            stack.update({"language": "JavaScript", "backend": "Express"})
            return stack, "backend"
        if "react only" in lowered or "frontend only" in lowered:
            stack.update({"language": "JavaScript", "frontend": "React", "backend": "None", "database": "None"})
            return stack, "frontend"
        if "convert to python" in lowered or "use python" in lowered:
            stack.update({"language": "Python", "backend": "FastAPI"})
            return stack, "language"
        return {}, ""

    def _detect_requested_files(self, lowered: str, selected_stack: Mapping[str, str]) -> list[dict[str, Any]]:
        files: list[dict[str, Any]] = []
        if self._looks_like_remove_request(lowered):
            return []
        if not self._has_known_stack(selected_stack):
            return []
        for name in ["admin dashboard", "dashboard"]:
            if name in lowered:
                files.append(self._file_for_feature("admin", "Admin dashboard page", selected_stack))
                break
        if "report" in lowered:
            files.append(self._file_for_feature("report", "Reports page and reporting workflow", selected_stack))
        if "login" in lowered:
            files.append(self._file_for_feature("login", "Login page and authentication workflow", selected_stack))
        if "payment" in lowered or "checkout" in lowered:
            files.append(self._file_for_feature("payment", "Payment checkout page or handler", selected_stack))
        if "profile" in lowered:
            files.append(self._file_for_feature("profile", "Profile page and account details workflow", selected_stack))
        if "controller" in lowered:
            files.append(self._file_for_feature("controller", "Project controller requested from chat", selected_stack))
        if "service" in lowered:
            files.append(self._file_for_feature("service", "Project service layer requested from chat", selected_stack))
        if " api" in lowered or " route" in lowered or "endpoint" in lowered:
            files.append(self._file_for_feature("api", "API route requested from chat", selected_stack))
        explicit_paths = re.findall(r"[\w./-]+\.(?:py|js|jsx|java|cpp|html|css)", lowered)
        for path in explicit_paths:
            files.append({"path": self._clean_chat_path(path), "purpose": "User-requested project file.", "required": True})
        deduped: dict[str, dict[str, Any]] = {}
        for item in files:
            path = str(item.get("path") or "").strip()
            if path:
                deduped[path] = item
        return list(deduped.values())

    def _detect_files_to_remove(
        self,
        lowered: str,
        current_preview: Mapping[str, Any],
        selected_stack: Mapping[str, str],
    ) -> list[dict[str, Any]]:
        if not self._looks_like_remove_request(lowered):
            return []
        candidates: list[str] = []
        explicit_paths = re.findall(r"[\w./-]+\.(?:py|js|jsx|java|cpp|html|css)", lowered)
        candidates.extend(self._clean_chat_path(path) for path in explicit_paths)
        for feature in ["admin", "report", "login", "payment", "profile", "controller", "service", "api"]:
            if feature in lowered or (feature == "report" and "reports" in lowered):
                candidates.append(self._file_for_feature(feature, f"Remove {feature} feature", selected_stack)["path"])
        existing_paths = {
            str(item.get("path") or "")
            for item in current_preview.get("files", [])
            if isinstance(item, Mapping)
        }
        custom_paths = {
            str(item.get("path") or "")
            for item in current_preview.get("customFiles", [])
            if isinstance(item, Mapping)
        }
        allowed = existing_paths | custom_paths
        removals: dict[str, dict[str, Any]] = {}
        for path in candidates:
            if not path:
                continue
            matched_path = next((existing for existing in allowed if existing == path or existing.endswith(path)), path)
            if allowed and matched_path not in allowed:
                continue
            removals[matched_path] = {"path": matched_path, "reason": "Requested by chatbot correction."}
        return list(removals.values())

    def _file_for_feature(self, feature: str, purpose: str, selected_stack: Mapping[str, str]) -> dict[str, Any]:
        frontend = selected_stack.get("frontend")
        backend = selected_stack.get("backend")
        language = selected_stack.get("language")
        component_names = {
            "admin": "AdminDashboard",
            "report": "ReportPage",
            "login": "LoginPage",
            "payment": "PaymentPage",
            "profile": "ProfilePage",
            "controller": "AppController",
            "service": "AppService",
            "api": "ApiRoute",
        }
        route_names = {
            "admin": "admin",
            "report": "reports",
            "login": "login",
            "payment": "payment",
            "profile": "profile",
            "controller": "app",
            "service": "app",
            "api": "api",
        }
        component = component_names.get(feature, "CustomPage")
        route = route_names.get(feature, ai.safe_js_name(feature))
        if backend == "FastAPI" and feature == "service":
            path = f"backend/app/services/{route}_service.py"
        elif backend == "Spring Boot" and feature == "service":
            path = "backend/src/main/java/com/example/app/service/AppService.java"
        elif backend == "Express" and feature == "service":
            path = f"backend/src/services/{route}Service.js"
        elif frontend == "React" and feature not in {"controller", "service", "api"}:
            path = f"frontend/src/pages/{component}.jsx"
        elif frontend == "HTML/CSS/JavaScript":
            path = f"pages/{route}.html"
        elif backend == "FastAPI":
            path = f"backend/app/routers/{route}.py"
        elif backend == "Flask":
            path = f"backend/app/routes/{route}.py"
        elif backend == "Spring Boot":
            controller = component.removesuffix("Page").removesuffix("Dashboard")
            if feature == "admin":
                controller = "Admin"
            path = f"backend/src/main/java/com/example/app/controller/{controller}Controller.java"
        elif backend == "Express":
            path = f"backend/src/routes/{route}.js"
        elif language == "C++":
            path = f"{route.rstrip('s')}.cpp"
        else:
            path = f"{route}.js"
        return {"path": path, "purpose": purpose, "required": True}

    def _has_known_stack(self, selected_stack: Mapping[str, str]) -> bool:
        return any(
            str(selected_stack.get(key) or "") not in {"", "Auto", "None"}
            for key in ("language", "frontend", "backend")
        )

    def _looks_like_file_request(self, lowered: str) -> bool:
        return any(word in lowered for word in ["add", "create", "include", "make"]) and any(
            word in lowered for word in ["file", "page", "dashboard", "report", "login", "payment", "checkout", "profile", "controller", "service", "api", "route", "endpoint"]
        )

    def _looks_like_remove_request(self, lowered: str) -> bool:
        return any(word in lowered for word in ["remove", "delete", "drop"]) and any(
            word in lowered
            for word in ["file", "page", "dashboard", "report", "login", "payment", "profile", "controller", "service", "api", "route", "endpoint", "module", ".jsx", ".py", ".js", ".html", ".java", ".cpp"]
        )

    def _looks_like_project_action(self, lowered: str) -> bool:
        return (
            self._looks_like_generation_intent(lowered)
            or self._looks_like_file_request(lowered)
            or self._looks_like_remove_request(lowered)
            or "change backend" in lowered
            or "spring boot" in lowered
        )

    def _detect_features_to_add(self, lowered: str) -> list[str]:
        if not any(word in lowered for word in ["add", "include", "make"]):
            return []
        features = []
        for label in ["login", "email otp", "csv export", "payment", "admin dashboard", "profile", "controller", "service", "api route"]:
            if label in lowered:
                features.append(label)
        return sorted(set(features))

    def _detect_features_to_remove(self, lowered: str) -> list[str]:
        if not self._looks_like_remove_request(lowered):
            return []
        features = []
        for label in ["login", "email otp", "csv export", "payment", "admin dashboard", "report page", "profile", "controller", "service", "api route"]:
            if label in lowered or (label == "report page" and "report" in lowered):
                features.append(label)
        return sorted(set(features))

    def _detect_required_inputs(self, lowered: str) -> list[dict[str, Any]]:
        inputs: list[dict[str, Any]] = []
        if any(word in lowered for word in ["ai", "chatbot", "llm", "openai", "gpt"]):
            inputs.append(self._required_input("OPENAI_API_KEY", "sk-...", "Used for AI chatbot responses."))
        if any(word in lowered for word in ["email", "contact", "otp", "notification", "smtp"]):
            inputs.extend(
                [
                    self._required_input("SMTP_EMAIL", "yourmail@gmail.com", "SMTP email address used for sending emails."),
                    self._required_input("SMTP_PASSWORD", "app password", "SMTP account password or app password."),
                    self._required_input("SMTP_HOST", "smtp.gmail.com", "SMTP email server host."),
                    self._required_input("SMTP_PORT", "587", "SMTP email server port."),
                ]
            )
        if any(word in lowered for word in ["payment", "checkout", "subscription", "stripe"]):
            inputs.extend(
                [
                    self._required_input("STRIPE_SECRET_KEY", "sk_test_...", "Used for payment processing."),
                    self._required_input("STRIPE_PUBLIC_KEY", "pk_test_...", "Public key used by checkout UI."),
                    self._required_input("PAYMENT_WEBHOOK_SECRET", "whsec_...", "Verifies payment webhook events."),
                ]
            )
        if any(word in lowered for word in ["database", "login", "admin", "inventory", "auth"]):
            inputs.append(self._required_input("DATABASE_URL", "sqlite:///./app.db", "Database connection string."))
        if any(word in lowered for word in ["file upload", "cloud storage", "storage bucket", "s3"]):
            inputs.append(self._required_input("STORAGE_BUCKET", "project-agent-uploads", "Storage bucket used for uploaded files."))
        return ai.dedupe_required_inputs(inputs)

    def _required_input(self, name: str, example: str, purpose: str) -> dict[str, Any]:
        return {
            "name": name,
            "required": True,
            "example": example,
            "whereToAdd": ".env",
            "whereToEnter": "Terminal prompt or .env",
            "purpose": purpose,
        }

    def _normalize_requested_files(self, value: Any, selected_stack: Mapping[str, str]) -> list[dict[str, Any]]:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            return []
        files = []
        for item in value:
            if not isinstance(item, Mapping):
                continue
            path = self._clean_chat_path(item.get("path"))
            if not path:
                continue
            files.append(
                {
                    "path": path,
                    "purpose": str(item.get("purpose") or item.get("description") or "Chat-requested project file.").strip(),
                    "required": bool(item.get("required", True)),
                }
            )
        return files or self._detect_requested_files("", selected_stack)

    def _normalize_files_to_remove(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            return []
        removals = []
        for item in value:
            if isinstance(item, Mapping):
                path = self._clean_chat_path(item.get("path"))
                reason = str(item.get("reason") or "Requested by chatbot correction.").strip()
            else:
                path = self._clean_chat_path(item)
                reason = "Requested by chatbot correction."
            if path:
                removals.append({"path": path, "reason": reason})
        deduped = {item["path"]: item for item in removals}
        return list(deduped.values())

    def _normalize_updated_stack(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, Mapping) or not value:
            return {}
        stack = ai.normalize_stack_selection(value)
        for key in ["source", "isUserConfirmedStack", "isDirty", "lastModifiedField"]:
            if key in value:
                stack[key] = value[key]
        return stack

    def _clean_chat_path(self, value: Any) -> str:
        path = str(value or "").replace("\\", "/").strip().strip("/")
        if not path or path.startswith(".") or ".." in path.split("/"):
            return ""
        return path

    def _merge_requirements(self, base: str, change: str) -> str:
        base_text = str(base or "").strip()
        change_text = str(change or "").strip()
        if not base_text:
            return change_text
        if change_text.lower() in base_text.lower():
            return base_text
        return f"{base_text}\n\nAdditional chatbot correction: {change_text}"

    def _draft_requirements(self, message: str) -> str:
        text = str(message or "").strip()
        if not text:
            return "Build a runnable starter project with clear setup, run instructions, and validation-ready files."
        feature_hint = " Include a clear main workflow, starter modules, setup/run scripts, and runtime instructions."
        return text if text.endswith(feature_hint.strip()) else f"{text}.{feature_hint}"

    def _correction_reply(
        self,
        requested_files: list[dict[str, Any]],
        required_inputs: list[dict[str, Any]],
        message: str,
        files_to_remove: list[dict[str, Any]] | None = None,
        features_to_add: list[str] | None = None,
        features_to_remove: list[str] | None = None,
    ) -> str:
        parts = [f"I understood this correction: {message}"]
        if requested_files:
            parts.append("Requested files: " + ", ".join(item["path"] for item in requested_files))
        if files_to_remove:
            parts.append("Files to remove: " + ", ".join(item["path"] for item in files_to_remove))
        if features_to_add:
            parts.append("Features to add: " + ", ".join(features_to_add))
        if features_to_remove:
            parts.append("Features to remove: " + ", ".join(features_to_remove))
        if required_inputs:
            parts.append("Required inputs: " + ", ".join(item["name"] for item in required_inputs))
        parts.append("Apply these corrections to the project?")
        return " ".join(parts)


chat_coordinator_agent = ChatCoordinatorAgent()
