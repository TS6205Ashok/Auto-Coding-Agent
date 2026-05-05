from __future__ import annotations

import logging
import os
import time

from app.agents.context import AgentWorkflowContext
from app.agents.file_planning_agent import FilePlanningAgent
from app.services import ai_service as ai


logger = logging.getLogger(__name__)


class CodeGenerationAgent:
    def __init__(self, file_planning_agent: FilePlanningAgent) -> None:
        self.file_planning_agent = file_planning_agent

    async def run(self, context: AgentWorkflowContext) -> AgentWorkflowContext:
        if context.project_contract is None:
            raise RuntimeError("CodeGenerationAgent requires CompleteProjectContract before file generation.")
        deadline = self._build_deadline(context)
        if context.direct_generation_allowed:
            context.preview = self._build_preview(context)
            logger.info(
                "CodeGenerationAgent generated files template=%s file_count=%s direct_generation=%s",
                context.template_family or "generic",
                len(context.preview.get("files", [])),
                True,
            )
            return context

        deterministic_preview = self._build_preview(context)
        configured_base_url = str(os.getenv("OLLAMA_BASE_URL") or "").strip()
        if not configured_base_url:
            context.fallback_used = True
            context.fallback_reason = "AI generation is unavailable because OLLAMA_BASE_URL is not configured."
            context.preview = self._apply_fallback_assumptions(
                deterministic_preview,
                context.generation_mode,
                context.fallback_reason,
            )
            logger.info(
                "CodeGenerationAgent generated files template=%s file_count=%s fallback=%s",
                context.template_family or "generic",
                len(context.preview.get("files", [])),
                True,
            )
            return context

        try:
            raw_plan = await ai.generate_project_plan(
                context.generation_context,
                context.requested_stack,
                context.generation_mode,
                deadline,
            )
            context.ai_raw_plan = dict(raw_plan)
            self.file_planning_agent.run(context, raw_plan)
            context.preview = self._build_preview(context)
            if context.generation_mode == "deep" and context.custom_manifest:
                remaining = ai.remaining_time(deadline)
                if remaining >= ai.MIN_CUSTOM_PASS_SECONDS:
                    try:
                        generated_custom_files = await ai.generate_deep_custom_files(
                            context.generation_context,
                            context.project_name,
                            context.selected_stack,
                            context.custom_manifest,
                            remaining,
                        )
                        context.preview = ai.apply_custom_file_overrides(
                            context.preview,
                            generated_custom_files,
                        )
                        context.preview["assumptions"] = ai.dedupe_list(
                            context.preview["assumptions"]
                            + ["Deep Mode enriched custom business logic with a second scoped AI pass."]
                        )
                    except Exception as exc:
                        context.preview["assumptions"] = ai.dedupe_list(
                            context.preview["assumptions"]
                            + [f"Deep Mode custom enrichment was skipped, so template custom files were kept: {exc}"]
                        )
                else:
                    context.preview["assumptions"] = ai.dedupe_list(
                        context.preview["assumptions"]
                        + ["Deep Mode used the fast template custom files because the 70-second preview budget was nearly exhausted."]
                    )
        except Exception as exc:
            context.fallback_used = True
            context.fallback_reason = str(exc)
            context.preview = self._apply_fallback_assumptions(
                deterministic_preview,
                context.generation_mode,
                context.fallback_reason,
            )

        logger.info(
            "CodeGenerationAgent generated files template=%s file_count=%s fallback=%s",
            context.template_family or "generic",
            len(context.preview.get("files", [])),
            context.fallback_used,
        )
        return context

    def _build_deadline(self, context: AgentWorkflowContext) -> float:
        ai_budget = ai.preview_budget_seconds(context.generation_mode)
        if context.generation_mode == "fast":
            ai_budget = min(ai_budget, 5.0)
        return time.monotonic() + ai_budget

    def _build_preview(self, context: AgentWorkflowContext) -> dict[str, object]:
        raw_preview: dict[str, object] = {
            "projectName": context.project_name or ai.clean_project_name(None, context.prompt),
            "detectedUserChoices": context.detected_user_choices,
            "selectedStack": context.selected_stack,
            "generatedVersion": ai.GENERATED_VERSION_LABEL,
            "mainFile": ai.main_file_for_stack(context.selected_stack),
            "primaryRunCommand": ai.primary_run_command(context.selected_stack, context.run_commands),
            "mainRunTarget": ai.main_run_target_for_stack(context.selected_stack),
            "localUrl": ai.local_url_for_stack(context.selected_stack),
            "setupInstructions": context.install_commands or ["setup.bat", "./setup.sh"],
            "runInstructions": [
                ai.main_run_target_for_stack(context.selected_stack),
                ai.primary_run_command(context.selected_stack, context.run_commands),
                "run.bat",
                "./run.sh",
            ],
            "stackSelectionSource": context.stack_selection_source,
            "isUserConfirmedStack": context.is_user_confirmed_stack,
            "projectType": context.declared_project_type or context.project_kind.get("label", ""),
            "modules": context.modules,
            "packageRequirements": context.package_requirements,
            "installCommands": context.install_commands,
            "runCommands": context.run_commands,
            "requiredInputs": context.required_inputs,
            "envVariables": context.env_variables,
            "customFiles": context.custom_manifest,
            "requestedFiles": context.custom_manifest,
            "filesToRemove": [{"path": path} for path in context.files_to_remove],
            "chatPendingCorrections": context.chat_pending_corrections,
            "projectContract": context.project_contract.to_dict(),
            "summary": context.summary,
            "problemStatement": context.problem_statement,
            "assumptions": context.assumptions,
            "architecture": context.architecture,
            "files": ai.finalize_preview_files(
                project_name=context.project_name or ai.clean_project_name(None, context.prompt),
                selected_stack=context.selected_stack,
                project_kind=context.project_kind,
                required_inputs=context.required_inputs,
                custom_manifest=context.custom_manifest,
                template_family=context.template_family,
                raw_files=context.files,
                project_contract=context.project_contract.to_dict(),
            ),
        }
        if context.final_architecture:
            raw_preview["finalArchitecture"] = context.final_architecture.to_dict()
        if context.template_family:
            raw_preview["templateFamily"] = context.template_family
        return ai.normalize_preview(
            raw_preview,
            context.prompt,
            context.requested_stack,
            context.generation_mode,
            context.generation_context,
        )

    def _apply_fallback_assumptions(
        self,
        preview: dict[str, object],
        generation_mode: str,
        reason: str,
    ) -> dict[str, object]:
        fallback_note = (
            "Deep Mode AI enrichment was unavailable, so the 100% runnable starter project uses the safe template-generated fallback."
            if generation_mode == "deep"
            else "Fast Mode AI planning was unavailable, so the 100% runnable starter project uses the safe template-generated fallback."
        )
        preview["assumptions"] = ai.dedupe_list(
            [
                fallback_note,
                f"Template fallback preview was generated because the AI planner could not complete in time or returned invalid output: {reason}",
                *preview.get("assumptions", []),
            ]
        )
        return preview
