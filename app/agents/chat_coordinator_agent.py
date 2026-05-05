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


@dataclass(slots=True)
class ChatCoordinatorResult:
    reply: str
    action: str = "none"
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
        if payload["action"] not in CHAT_ACTIONS:
            payload["action"] = "none"
        if not payload["reply"]:
            payload["reply"] = "I understood that. Tell me if you want to generate or modify the project."
        return payload


class ChatCoordinatorAgent:
    def __init__(self) -> None:
        self.default_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.default_model = os.getenv("OLLAMA_MODEL", "llama3.1")
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
        base_url = os.getenv("OLLAMA_BASE_URL", "").strip().rstrip("/")
        model = os.getenv("OLLAMA_MODEL", self.default_model).strip() or self.default_model
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
                payload = response.json()
            raw_text = str(payload.get("response") or "").strip()
            parsed = json.loads(ai.extract_json_object(raw_text))
            result = self._normalize_result(parsed, llm_mode_used="ollama")
            if result.action == "none" and self._looks_like_project_action(message.lower()):
                return None
            return result
        except Exception as exc:
            logger.info("ChatCoordinatorAgent Ollama unavailable; using rule-based fallback: %s", exc)
            return None

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
            "You are a ChatGPT-like project co-pilot connected to a software project generation agent. "
            "Your job is to discuss project ideas, improve requirements, and return structured actions. "
            "You can add files, remove files, add features, remove features, change stack, and request regeneration. "
            "Do not generate final project files directly. Always return strict JSON. "
            "If the user wants a project created, return action generate_project. "
            "If the user wants modification, return action add_files/remove_files/add_feature/remove_feature/change_stack. "
            "Ask confirmation for project-changing actions. Never require paid APIs for chatbot behavior.\n\n"
            "Allowed actions: none, update_idea, update_requirements, generate_project, regenerate_project, "
            "add_files, remove_files, add_feature, remove_feature, change_stack, update_required_inputs, "
            "pause_agent_and_update, cancel_pending_change.\n"
            "Return fields: reply, action, updatedIdea, updatedRequirements, requestedFiles, filesToRemove, "
            "featuresToAdd, featuresToRemove, updatedStack, requiredInputs, needsConfirmation, "
            "confirmationMessage, shouldGenerate, shouldRegenerate, shouldPauseAgent, confidence.\n\n"
            f"STATE:\n{json.dumps(state, indent=2)}"
        )

    def _normalize_result(self, payload: Mapping[str, Any], *, llm_mode_used: str) -> ChatCoordinatorResult:
        result = ChatCoordinatorResult(
            reply=str(payload.get("reply") or "").strip(),
            action=str(payload.get("action") or "none").strip(),
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
                action="cancel_pending_change",
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
                reply=f"I detected a stack change to {updated_stack.get('language')} / {updated_stack.get('backend')}.",
                action="change_stack",
                updatedStack=updated_stack,
                needsConfirmation=True,
                confirmationMessage="Apply this stack change and regenerate the project?",
                shouldRegenerate=has_preview,
                confidence="high",
            )

        required_inputs = self._detect_required_inputs(lowered)
        requested_files = self._detect_requested_files(lowered, normalized_stack)
        files_to_remove = self._detect_files_to_remove(lowered, current_preview, normalized_stack)
        features_to_add = self._detect_features_to_add(lowered)
        features_to_remove = self._detect_features_to_remove(lowered)
        if not requested_files and not has_preview and self._looks_like_file_request(lowered):
            return ChatCoordinatorResult(
                reply="I can add that file, but I need a selected stack or generated preview first so I can choose the correct path.",
                action="none",
                confidence="medium",
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

        if any(phrase in lowered for phrase in ["generate this", "build it now", "create project", "finalize and generate", "generate project"]):
            idea = current_idea or message
            return ChatCoordinatorResult(
                reply="Ready. I will send this finalized project description through the Project Agent pipeline.",
                action="generate_project",
                updatedIdea=idea,
                updatedRequirements=self._draft_requirements(idea),
                requiredInputs=required_inputs,
                needsConfirmation=True,
                confirmationMessage="Generate this project through the Project Agent pipeline?",
                shouldGenerate=True,
                confidence="high",
            )

        draft = self._draft_requirements(message)
        return ChatCoordinatorResult(
            reply=(
                "Here is a stronger project direction I can use: "
                f"{draft} Do you want to use this as the project description or add more details?"
            ),
            action="update_requirements",
            updatedIdea=message,
            updatedRequirements=draft,
            requiredInputs=required_inputs,
            needsConfirmation=False,
            confidence="medium",
        )

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
        for feature in ["admin", "report", "login", "payment"]:
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
        }
        route_names = {
            "admin": "admin",
            "report": "reports",
            "login": "login",
            "payment": "payment",
        }
        component = component_names.get(feature, "CustomPage")
        route = route_names.get(feature, ai.safe_js_name(feature))
        if frontend == "React":
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
        return any(word in lowered for word in ["add", "create", "include"]) and any(
            word in lowered for word in ["file", "page", "dashboard", "report", "login", "payment", "checkout"]
        )

    def _looks_like_remove_request(self, lowered: str) -> bool:
        return any(word in lowered for word in ["remove", "delete", "drop"]) and any(
            word in lowered
            for word in ["file", "page", "dashboard", "report", "login", "payment", "module", ".jsx", ".py", ".js", ".html", ".java", ".cpp"]
        )

    def _looks_like_project_action(self, lowered: str) -> bool:
        return (
            self._looks_like_file_request(lowered)
            or self._looks_like_remove_request(lowered)
            or "change backend" in lowered
            or "spring boot" in lowered
            or "generate" in lowered
        )

    def _detect_features_to_add(self, lowered: str) -> list[str]:
        if not any(word in lowered for word in ["add", "include", "make"]):
            return []
        features = []
        for label in ["login", "email otp", "csv export", "payment", "admin dashboard"]:
            if label in lowered:
                features.append(label)
        return sorted(set(features))

    def _detect_features_to_remove(self, lowered: str) -> list[str]:
        if not self._looks_like_remove_request(lowered):
            return []
        features = []
        for label in ["login", "email otp", "csv export", "payment", "admin dashboard", "report page"]:
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
