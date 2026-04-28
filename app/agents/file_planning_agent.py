from __future__ import annotations

import logging
from typing import Any, Mapping

from app.agents.context import AgentWorkflowContext
from app.services import ai_service as ai


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
        context.selected_stack = ai.resolve_selected_stack(
            context.prompt,
            context.requested_stack,
            raw.get("selectedStack") or context.selected_stack,
            detected_choices,
        )
        context.project_kind = ai.determine_project_kind(
            context.selected_stack,
            raw.get("projectType") or context.declared_project_type,
        )
        context.template_family = str(raw.get("templateFamily") or context.template_family or "").strip()
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
            context.package_requirements = ai.dedupe_list(
                ai.normalize_string_list(raw.get("packageRequirements"))
                or list(template_metadata.get("packageRequirements", []))
            )
            context.install_commands = ai.dedupe_list(
                ai.normalize_string_list(raw.get("installCommands"))
                or list(template_metadata.get("installCommands", []))
            )
            context.run_commands = ai.dedupe_list(
                ai.normalize_string_list(raw.get("runCommands"))
                or list(template_metadata.get("runCommands", []))
            )
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
                ai.normalize_modules(raw.get("modules")),
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
            context.package_requirements = ai.dedupe_list(
                ai.normalize_string_list(raw.get("packageRequirements"))
                + ai.build_package_requirements(context.selected_stack, context.project_kind)
            )
            context.install_commands = ai.dedupe_list(
                ai.normalize_string_list(raw.get("installCommands"))
                + ai.build_install_commands(context.selected_stack, context.project_kind)
            )
            context.run_commands = ai.dedupe_list(
                ai.normalize_string_list(raw.get("runCommands"))
                + ai.build_run_commands(context.selected_stack, context.project_kind)
            )
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
            raw.get("customFiles"),
            context.selected_stack,
            context.project_kind,
        )
        context.files = ai.normalize_files(raw.get("files"))
        context.architecture = ai.dedupe_list(
            ai.normalize_string_list(raw.get("architecture")) + context.architecture
        )
        context.file_manifest = sorted(
            ai.required_preview_paths(
                context.selected_stack,
                context.project_kind,
                context.template_family,
            )
        )
        logger.info(
            "FilePlanningAgent planned files template=%s file_manifest_count=%s modules=%s",
            context.template_family or "generic",
            len(context.file_manifest),
            len(context.modules),
        )
        return context
