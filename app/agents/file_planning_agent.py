from __future__ import annotations

import logging
from typing import Any, Mapping

from app.agents.context import AgentWorkflowContext
from app.services import ai_service as ai
from app.services.architecture_registry import build_final_architecture_decision


logger = logging.getLogger(__name__)


class FilePlanningAgent:
    def run(
        self,
        context: AgentWorkflowContext,
        raw_plan: Mapping[str, Any] | None = None,
    ) -> AgentWorkflowContext:
        raw = dict(raw_plan or {})
        detected_choices = ai.dedupe_list(
            ai.normalize_string_list(raw.get("detectedUserChoices"))
            or context.detected_user_choices
            or ai.detect_user_choices(context.prompt)
        )
        context.detected_user_choices = detected_choices
        if context.final_architecture is None:
            inferred_stack = ai.resolve_selected_stack(
                context.prompt,
                context.requested_stack,
                context.selected_stack or raw.get("selectedStack"),
                detected_choices,
            )
            context.final_architecture = build_final_architecture_decision(
                prompt=context.generation_context or context.prompt,
                requested_stack=context.requested_stack,
                inferred_stack=inferred_stack,
                declared_project_type=raw.get("projectType") or context.declared_project_type,
                project_category=context.project_category,
                migration_summary=context.migration_summary,
                is_migrated=context.migration_active or context.migration_requested,
            )
        context.selected_stack = context.final_architecture.selected_stack
        context.project_kind = ai.determine_project_kind(
            context.selected_stack,
            context.final_architecture.project_type or raw.get("projectType") or context.declared_project_type,
        )
        if context.final_architecture.stack_family == "static_frontend" and context.final_architecture.project_type == "game_or_puzzle":
            context.template_family = "puzzle-game"
        else:
            context.template_family = str(context.template_family or raw.get("templateFamily") or "").strip()
        context.project_name = ai.clean_project_name(raw.get("projectName"), context.prompt)

        if context.template_family == "puzzle-game":
            template_metadata = ai.build_template_preview_metadata(
                "puzzle-game",
                context.project_name,
                context.generation_mode,
            )
            context.modules = ai.normalize_modules(raw.get("modules")) or template_metadata.get("modules", [])
            context.required_inputs = ai.normalize_required_inputs(raw.get("requiredInputs")) or template_metadata.get("requiredInputs", [])
            context.env_variables = ai.normalize_env_variables(raw.get("envVariables")) or template_metadata.get("envVariables", [])
            context.package_requirements = list(context.final_architecture.package_requirements)
            context.install_commands = list(context.final_architecture.install_commands)
            context.run_commands = list(context.final_architecture.run_commands)
            context.summary = (
                str(raw.get("summary") or "").strip()
                or str(template_metadata.get("summary") or "").strip()
            )
            context.problem_statement = (
                str(raw.get("problemStatement") or "").strip()
                or context.prompt.strip()
                or f"Build a starter project for {context.project_name}."
            )
            context.assumptions = ai.dedupe_list(
                ai.normalize_string_list(raw.get("assumptions"))
                + ai.normalize_string_list(template_metadata.get("assumptions"))
            )
        else:
            context.modules = ai.merge_modules(
                ai.normalize_modules(raw.get("modules")) + context.domain_modules,
                ai.build_default_modules(context.selected_stack, context.project_kind),
            )
            context.required_inputs = ai.merge_required_inputs(
                ai.normalize_required_inputs(raw.get("requiredInputs")),
                ai.build_required_inputs(
                    context.generation_context or context.prompt,
                    context.selected_stack,
                    context.project_kind,
                    context.modules,
                ),
            )
            context.env_variables = ai.merge_env_variables(
                ai.normalize_env_variables(raw.get("envVariables")),
                ai.required_inputs_to_env_variables(context.required_inputs),
            )
            context.package_requirements = list(context.final_architecture.package_requirements)
            context.install_commands = list(context.final_architecture.install_commands)
            context.run_commands = list(context.final_architecture.run_commands)
            context.summary = (
                str(raw.get("summary") or "").strip()
                or ai.build_summary(
                    context.project_name,
                    context.project_kind,
                    context.selected_stack,
                    context.generation_mode,
                )
            )
            context.problem_statement = (
                str(raw.get("problemStatement") or "").strip()
                or context.prompt.strip()
                or f"Build a starter project for {context.project_name}."
            )
            context.assumptions = ai.dedupe_list(
                ai.normalize_string_list(raw.get("assumptions"))
                + ai.build_assumptions(
                    context.selected_stack,
                    context.project_kind,
                    context.requested_stack,
                    context.generation_mode,
                    bool(raw.get("customFiles")),
                )
            )

        context.custom_manifest = ai.normalize_custom_manifest(
            raw.get("customFiles") or context.requested_custom_files or context.custom_manifest,
            context.selected_stack,
            context.project_kind,
        )
        context.custom_manifest = ai.dedupe_manifest(
            [*context.custom_manifest, *context.domain_required_files]
        )
        removed_paths = set(ai.normalize_removed_paths(raw.get("filesToRemove") or context.files_to_remove))
        context.files_to_remove = sorted(removed_paths)
        context.custom_manifest = [
            item for item in context.custom_manifest
            if item.get("path") not in removed_paths
        ]
        context.files = [
            item for item in ai.normalize_files(raw.get("files"))
            if item.get("path") not in removed_paths
        ]
        context.architecture = ai.dedupe_list(
            ai.normalize_string_list(raw.get("architecture")) + context.architecture
        )
        context.file_manifest = sorted(context.final_architecture.required_files)
        logger.info(
            "FilePlanningAgent planned files template=%s file_manifest_count=%s modules=%s",
            context.template_family or "generic",
            len(context.file_manifest),
            len(context.modules),
        )
        return context
