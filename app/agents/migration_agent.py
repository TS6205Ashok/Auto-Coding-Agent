from __future__ import annotations

import logging

from app.agents.context import AgentWorkflowContext


logger = logging.getLogger(__name__)


class MigrationAgent:
    def run(self, context: AgentWorkflowContext) -> AgentWorkflowContext:
        if not context.migration_active:
            return context

        target_stack = dict(context.requested_stack)
        explicit_target = self._detect_explicit_target(context.prompt.lower())
        if explicit_target:
            target_stack.update(explicit_target)
        else:
            same_stack_target = self._same_stack_target(context)
            target_stack.update({key: value for key, value in same_stack_target.items() if value})

        context.requested_stack = target_stack
        context.target_language = target_stack.get("language", "")
        context.target_framework = target_stack.get("backend") or target_stack.get("frontend") or ""
        context.target_project_type = self._target_project_type(context)
        context.migration_summary = {
            "sourceLanguage": context.source_language or "Unknown",
            "sourceFramework": context.source_framework or "Unknown",
            "sourceProjectType": context.source_project_type or "Unknown",
            "targetLanguage": context.target_language or "Unknown",
            "targetFramework": context.target_framework or "Unknown",
            "targetProjectType": context.target_project_type or "Unknown",
            "keyChanges": self._key_changes(context),
        }

        logger.info(
            "MigrationAgent planned migration active=%s source=%s/%s target=%s/%s",
            context.migration_active,
            context.source_language or "unknown",
            context.source_framework or "unknown",
            context.target_language or "unknown",
            context.target_framework or "unknown",
        )
        return context

    def _detect_explicit_target(self, lowered: str) -> dict[str, str]:
        if " to python" in lowered or " into python" in lowered:
            return {
                "language": "Python",
                "backend": "FastAPI",
                "frontend": "None",
                "database": "SQLite",
                "deployment": "Render",
            }
        if " to java" in lowered or " into java" in lowered or " to spring boot" in lowered:
            return {
                "language": "Java",
                "backend": "Spring Boot",
                "frontend": "None",
                "database": "PostgreSQL",
                "deployment": "Docker",
            }
        if " to node" in lowered or " to javascript" in lowered or " to express" in lowered:
            return {
                "language": "JavaScript",
                "backend": "Express",
                "frontend": "None",
                "database": "PostgreSQL",
                "deployment": "Render",
            }
        if " to react" in lowered:
            return {
                "language": "JavaScript",
                "frontend": "React",
                "backend": "None",
                "database": "None",
                "deployment": "Vercel",
            }
        return {}

    def _same_stack_target(self, context: AgentWorkflowContext) -> dict[str, str]:
        if context.source_framework == "Spring Boot" or context.source_language == "Java":
            return {
                "language": "Java",
                "frontend": "None",
                "backend": "Spring Boot",
                "database": "PostgreSQL",
                "deployment": "Docker",
            }
        if context.source_framework == "Express" or context.source_language in {"JavaScript", "TypeScript"}:
            return {
                "language": "JavaScript",
                "frontend": "None" if context.source_project_type == "backend" else "React",
                "backend": "Express" if context.source_project_type != "frontend" else "None",
                "database": "PostgreSQL" if context.source_project_type != "frontend" else "None",
                "deployment": "Render",
            }
        if context.source_framework in {"FastAPI", "Flask"} or context.source_language == "Python":
            return {
                "language": "Python",
                "frontend": "None" if context.source_project_type == "backend" else "React",
                "backend": "FastAPI" if context.source_project_type != "frontend" else "None",
                "database": "SQLite" if context.source_project_type != "frontend" else "None",
                "deployment": "Render",
            }
        if context.source_framework == "React":
            return {
                "language": "JavaScript",
                "frontend": "React",
                "backend": "None",
                "database": "None",
                "deployment": "Vercel",
            }
        if context.source_language == "C++":
            return {
                "language": "Python",
                "frontend": "None",
                "backend": "FastAPI" if context.source_project_type != "cli" else "None",
                "database": "None" if context.source_project_type == "cli" else "SQLite",
                "deployment": "Docker",
            }
        return {}

    def _target_project_type(self, context: AgentWorkflowContext) -> str:
        if context.requested_stack.get("frontend") not in {"", "Auto", "None"} and context.requested_stack.get("backend") not in {"", "Auto", "None"}:
            return "full-stack"
        if context.requested_stack.get("backend") not in {"", "Auto", "None"}:
            return "backend"
        if context.requested_stack.get("frontend") not in {"", "Auto", "None"}:
            return "frontend"
        return context.source_project_type or "generic"

    def _key_changes(self, context: AgentWorkflowContext) -> list[str]:
        changes: list[str] = []
        if context.source_framework and context.target_framework and context.source_framework != context.target_framework:
            changes.append(f"Migrated backend/runtime from {context.source_framework} to {context.target_framework}.")
        if context.source_language and context.target_language and context.source_language != context.target_language:
            changes.append(f"Converted implementation language from {context.source_language} to {context.target_language}.")
        if context.source_project_type and context.target_project_type and context.source_project_type != context.target_project_type:
            changes.append(f"Adjusted project shape from {context.source_project_type} to {context.target_project_type}.")
        if not changes:
            changes.append("Rebuilt the project in a clean runnable starter structure while preserving the original stack intent.")
        return changes
