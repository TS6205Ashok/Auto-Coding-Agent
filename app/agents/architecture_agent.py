from __future__ import annotations

import logging

from app.agents.context import AgentWorkflowContext
from app.services import ai_service as ai
from app.services.architecture_registry import build_final_architecture_decision


logger = logging.getLogger(__name__)


class ArchitectureAgent:
    def run(self, context: AgentWorkflowContext) -> AgentWorkflowContext:
        if context.target_language or context.target_framework:
            context.requested_stack = self._apply_target_preferences(context)
        inferred_stack = ai.resolve_selected_stack(
            context.prompt,
            context.requested_stack,
            None,
            context.detected_user_choices,
        )
        context.final_architecture = build_final_architecture_decision(
            prompt=context.generation_context or context.prompt,
            requested_stack=context.requested_stack,
            inferred_stack=inferred_stack,
            declared_project_type=context.declared_project_type,
            project_category=context.project_category,
            migration_summary=context.migration_summary,
            is_migrated=context.migration_active or context.migration_requested,
            stack_selection_source=context.stack_selection_source,
            is_user_confirmed_stack=context.is_user_confirmed_stack,
            last_modified_field=context.last_modified_field,
        )
        context.selected_stack = context.final_architecture.selected_stack
        context.project_kind = ai.determine_project_kind(
            context.selected_stack,
            context.final_architecture.project_type or context.declared_project_type,
        )
        context.template_family = self._resolve_template_family(context)
        context.architecture = self._build_architecture(context)
        context.understanding = ai.build_agent_understanding(
            context.prompt,
            context.selected_stack,
            context.project_kind,
        )
        logger.info(
            "ArchitectureAgent selected stack from=%s category=%s template=%s stack=%s package_manager=%s runtime_tools=%s",
            context.final_architecture.stack_selection_source,
            context.project_category,
            context.template_family or "generic",
            ", ".join(ai.build_chosen_stack(context.selected_stack)),
            context.final_architecture.package_manager,
            ", ".join(context.final_architecture.runtime_tools),
        )
        return context

    def _build_architecture(self, context: AgentWorkflowContext) -> list[str]:
        if context.template_family == "puzzle-game":
            return [
                "Static frontend application",
                "Single-page browser game",
                "No backend or database required",
            ]
        if context.final_architecture:
            return ai.build_architecture(context.final_architecture.selected_stack, context.project_kind)
        return ai.build_architecture(context.selected_stack, context.project_kind)

    def _resolve_template_family(self, context: AgentWorkflowContext) -> str:
        if context.final_architecture and context.final_architecture.stack_family == "static_frontend":
            if context.final_architecture.project_type == "game_or_puzzle":
                return "puzzle-game"
        selected_frontend = str(context.selected_stack.get("frontend") or "Auto")
        selected_backend = str(context.selected_stack.get("backend") or "Auto")
        explicit_frontend = str(context.requested_stack.get("frontend") or "Auto")
        explicit_backend = str(context.requested_stack.get("backend") or "Auto")
        explicit_language = str(context.requested_stack.get("language") or "Auto")
        if context.project_category == "game":
            explicit_non_static = (
                explicit_frontend not in {"", "Auto", "HTML/CSS/JavaScript", "None"}
                or explicit_backend not in {"", "Auto", "None"}
                or explicit_language not in {"", "Auto", "JavaScript"}
            )
            if (
                not explicit_non_static
                and selected_frontend == "HTML/CSS/JavaScript"
                and selected_backend == "None"
            ):
                return "puzzle-game"
        return ai.category_template_family(context.project_category)

    def _apply_target_preferences(self, context: AgentWorkflowContext) -> dict[str, str]:
        requested = dict(context.requested_stack)
        if context.target_language and requested.get("language", "Auto") in {"", "Auto"}:
            requested["language"] = context.target_language
        if context.target_framework:
            if context.target_framework in {"FastAPI", "Flask", "Express", "NestJS", "Spring Boot"} and requested.get("backend", "Auto") in {"", "Auto"}:
                requested["backend"] = context.target_framework
            if context.target_framework in {"React", "Next.js", "Vue", "HTML/CSS/JavaScript"} and requested.get("frontend", "Auto") in {"", "Auto"}:
                requested["frontend"] = context.target_framework
        if context.target_project_type == "backend":
            if requested.get("frontend", "Auto") in {"", "Auto"}:
                requested["frontend"] = "None"
        elif context.target_project_type == "frontend":
            if requested.get("backend", "Auto") in {"", "Auto"}:
                requested["backend"] = "None"
            if requested.get("database", "Auto") in {"", "Auto"}:
                requested["database"] = "None"
        return requested
