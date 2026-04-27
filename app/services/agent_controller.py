from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Mapping

from . import ai_service as ai

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class IdeaContext:
    idea: str
    requested_stack: dict[str, str]
    generation_mode: str
    final_requirements: str = ""
    generation_context: str = ""
    detected_user_choices: list[str] = field(default_factory=list)
    declared_project_type: str = ""
    selected_stack: dict[str, str] = field(default_factory=dict)
    project_kind: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentAnalysisResult:
    understanding: str
    assumptions: list[str]
    suggested_stack: dict[str, str]
    stack_reasons: list[str]
    questions: list[dict[str, Any]]
    detected_project_type: str
    confidence: int

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "understanding": self.understanding,
            "assumptions": self.assumptions,
            "suggestedStack": self.suggested_stack,
            "stackReasons": self.stack_reasons,
            "questions": self.questions,
            "detectedProjectType": self.detected_project_type,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class FinalizedRequirementsResult:
    final_requirements: str
    selected_stack: dict[str, str]
    assumptions: list[str]
    normalized_answers: dict[str, str] = field(default_factory=dict)
    project_kind: dict[str, Any] = field(default_factory=dict)

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "finalRequirements": self.final_requirements,
            "selectedStack": self.selected_stack,
            "assumptions": self.assumptions,
        }


@dataclass(slots=True)
class ProjectStructurePlan:
    project_name: str
    detected_user_choices: list[str]
    selected_stack: dict[str, str]
    chosen_stack: list[str]
    assumptions: list[str]
    summary: str
    problem_statement: str
    architecture: list[str]
    modules: list[dict[str, Any]]
    package_requirements: list[str]
    install_commands: list[str]
    run_commands: list[str]
    required_inputs: list[dict[str, Any]]
    env_variables: list[dict[str, Any]]
    custom_manifest: list[dict[str, str]]
    files: list[dict[str, str]]
    file_tree: str
    project_kind: dict[str, Any] = field(default_factory=dict)

    def to_preview_dict(self) -> dict[str, Any]:
        return {
            "projectName": self.project_name,
            "detectedUserChoices": self.detected_user_choices,
            "selectedStack": self.selected_stack,
            "chosenStack": self.chosen_stack,
            "assumptions": self.assumptions,
            "summary": self.summary,
            "problemStatement": self.problem_statement,
            "architecture": self.architecture,
            "modules": self.modules,
            "packageRequirements": self.package_requirements,
            "installCommands": self.install_commands,
            "runCommands": self.run_commands,
            "requiredInputs": self.required_inputs,
            "envVariables": self.env_variables,
            "fileTree": self.file_tree,
            "files": self.files,
        }


@dataclass(slots=True)
class GeneratedProjectResult:
    preview: dict[str, Any]
    fallback_used: bool = False
    fallback_reason: str = ""


class AgentController:
    def analyze_idea(self, idea: str) -> dict[str, Any]:
        context = self._build_idea_context(idea)
        questions = self.ask_questions(context)
        result = AgentAnalysisResult(
            understanding=ai.build_agent_understanding(
                context.idea,
                context.selected_stack,
                context.project_kind,
            ),
            assumptions=ai.build_agent_analysis_assumptions(
                context.selected_stack,
                context.project_kind,
                questions,
            ),
            suggested_stack=context.selected_stack,
            stack_reasons=ai.build_stack_reasons(
                context.selected_stack,
                context.project_kind,
            ),
            questions=questions,
            detected_project_type=context.project_kind["label"],
            confidence=ai.compute_agent_confidence(
                context.idea,
                context.detected_user_choices,
                questions,
                context.project_kind,
            ),
        )
        return result.to_api_dict()

    def decide_stack(self, context: IdeaContext, model_stack: Any = None) -> dict[str, str]:
        return ai.resolve_selected_stack(
            context.idea,
            context.requested_stack,
            model_stack,
            context.detected_user_choices,
        )

    def determine_missing_info(self, context: IdeaContext) -> list[dict[str, Any]]:
        return ai.build_agent_questions(
            context.idea,
            context.selected_stack,
            context.project_kind,
        )

    def ask_questions(self, context: IdeaContext) -> list[dict[str, Any]]:
        return self.determine_missing_info(context)

    def finalize_requirements(
        self,
        idea: str,
        answers: Mapping[str, Any] | None,
        selected_stack: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        normalized_answers = ai.normalize_agent_answers(answers)
        resolved_stack = ai.apply_agent_answers_to_stack(
            idea,
            ai.normalize_stack_selection(selected_stack),
            normalized_answers,
        )
        project_kind = ai.determine_project_kind(
            resolved_stack,
            normalized_answers.get("project_scope"),
        )
        result = FinalizedRequirementsResult(
            final_requirements=ai.build_final_requirements_summary(
                idea,
                normalized_answers,
                resolved_stack,
                project_kind,
            ),
            selected_stack=resolved_stack,
            assumptions=ai.build_agent_finalize_assumptions(
                normalized_answers,
                resolved_stack,
                project_kind,
            ),
            normalized_answers=normalized_answers,
            project_kind=project_kind,
        )
        return result.to_api_dict()

    def plan_project_structure(
        self,
        context: IdeaContext,
        raw_plan: Mapping[str, Any] | None = None,
    ) -> ProjectStructurePlan:
        raw = dict(raw_plan or {})
        detected_choices = ai.dedupe_list(
            ai.normalize_string_list(raw.get("detectedUserChoices"))
            or context.detected_user_choices
            or ai.detect_user_choices(context.idea)
        )
        selected_stack = ai.resolve_selected_stack(
            context.idea,
            context.requested_stack,
            raw.get("selectedStack") or context.selected_stack,
            detected_choices,
        )
        project_kind = ai.determine_project_kind(
            selected_stack,
            raw.get("projectType") or context.declared_project_type,
        )
        project_name = ai.clean_project_name(raw.get("projectName"), context.idea)

        modules = ai.merge_modules(
            ai.normalize_modules(raw.get("modules")),
            ai.build_default_modules(selected_stack, project_kind),
        )
        required_inputs = ai.merge_required_inputs(
            ai.normalize_required_inputs(raw.get("requiredInputs")),
            ai.build_required_inputs(
                context.generation_context or context.idea,
                selected_stack,
                project_kind,
                modules,
            ),
        )
        env_variables = ai.merge_env_variables(
            ai.normalize_env_variables(raw.get("envVariables")),
            ai.required_inputs_to_env_variables(required_inputs),
        )
        package_requirements = ai.dedupe_list(
            ai.normalize_string_list(raw.get("packageRequirements"))
            + ai.build_package_requirements(selected_stack, project_kind)
        )
        install_commands = ai.dedupe_list(
            ai.normalize_string_list(raw.get("installCommands"))
            + ai.build_install_commands(selected_stack, project_kind)
        )
        run_commands = ai.dedupe_list(
            ai.normalize_string_list(raw.get("runCommands"))
            + ai.build_run_commands(selected_stack, project_kind)
        )
        custom_manifest = ai.normalize_custom_manifest(
            raw.get("customFiles"),
            selected_stack,
            project_kind,
        )
        files = ai.finalize_preview_files(
            project_name=project_name,
            selected_stack=selected_stack,
            project_kind=project_kind,
            custom_manifest=custom_manifest,
            raw_files=raw.get("files"),
        )
        assumptions = ai.dedupe_list(
            ai.normalize_string_list(raw.get("assumptions"))
            + ai.build_assumptions(
                selected_stack,
                project_kind,
                context.requested_stack,
                context.generation_mode,
                bool(custom_manifest),
            )
        )
        architecture = ai.dedupe_list(
            ai.normalize_string_list(raw.get("architecture"))
            + ai.build_architecture(selected_stack, project_kind)
        )
        file_tree = ai.build_preview_file_tree(
            files,
            include_env_example=bool(env_variables),
        )

        return ProjectStructurePlan(
            project_name=project_name,
            detected_user_choices=detected_choices,
            selected_stack=selected_stack,
            chosen_stack=ai.build_chosen_stack(selected_stack),
            assumptions=assumptions,
            summary=str(raw.get("summary") or "").strip()
            or ai.build_summary(
                project_name,
                project_kind,
                selected_stack,
                context.generation_mode,
            ),
            problem_statement=str(raw.get("problemStatement") or "").strip()
            or context.idea.strip()
            or f"Build a starter project for {project_name}.",
            architecture=architecture,
            modules=modules,
            package_requirements=package_requirements,
            install_commands=install_commands,
            run_commands=run_commands,
            required_inputs=required_inputs,
            env_variables=env_variables,
            custom_manifest=custom_manifest,
            files=files,
            file_tree=file_tree,
            project_kind=project_kind,
        )

    async def generate_files(
        self,
        idea: str,
        selected_stack: dict[str, str] | None = None,
        generation_mode: str = "fast",
        final_requirements: str = "",
    ) -> dict[str, Any]:
        context = self._build_idea_context(
            idea,
            selected_stack=selected_stack,
            generation_mode=generation_mode,
            final_requirements=final_requirements,
        )
        preview_started_at = time.perf_counter()
        deadline = time.monotonic() + ai.preview_budget_seconds(context.generation_mode)
        planner_started_at: float | None = None
        planner_duration = 0.0

        try:
            planner_started_at = time.perf_counter()
            raw_plan = await ai.generate_project_plan(
                context.generation_context,
                context.requested_stack,
                context.generation_mode,
                deadline,
            )
            planner_duration = time.perf_counter() - planner_started_at
            structure_plan = self.plan_project_structure(context, raw_plan)
            preview = structure_plan.to_preview_dict()

            if context.generation_mode == "deep" and structure_plan.custom_manifest:
                remaining = ai.remaining_time(deadline)
                if remaining >= ai.MIN_CUSTOM_PASS_SECONDS:
                    try:
                        generated_custom_files = await ai.generate_deep_custom_files(
                            context.generation_context,
                            structure_plan.project_name,
                            structure_plan.selected_stack,
                            structure_plan.custom_manifest,
                            remaining,
                        )
                        preview = ai.apply_custom_file_overrides(preview, generated_custom_files)
                        preview["assumptions"] = ai.dedupe_list(
                            preview["assumptions"]
                            + ["Deep Mode enriched custom business logic with a second scoped AI pass."]
                        )
                    except Exception as exc:
                        preview["assumptions"] = ai.dedupe_list(
                            preview["assumptions"]
                            + [f"Deep Mode custom enrichment was skipped, so template custom files were kept: {exc}"]
                        )
                else:
                    preview["assumptions"] = ai.dedupe_list(
                        preview["assumptions"]
                        + ["Deep Mode used the fast template custom files because the 70-second preview budget was nearly exhausted."]
                    )

            preview = self.validate_project(preview)
            total_duration = time.perf_counter() - preview_started_at
            logger.info(
                "project_preview_complete mode=%s planner_duration=%.2fs total_duration=%.2fs fallback_used=%s",
                context.generation_mode,
                planner_duration,
                total_duration,
                False,
            )
            return GeneratedProjectResult(preview=preview).preview
        except Exception as exc:
            if planner_started_at is not None and planner_duration == 0.0:
                planner_duration = time.perf_counter() - planner_started_at
            preview = self._build_fallback_preview(context, str(exc))
            preview = self.validate_project(preview)
            total_duration = time.perf_counter() - preview_started_at
            logger.warning(
                "project_preview_fallback mode=%s planner_duration=%.2fs total_duration=%.2fs fallback_used=%s reason=%s",
                context.generation_mode,
                planner_duration,
                total_duration,
                True,
                str(exc),
            )
            return GeneratedProjectResult(
                preview=preview,
                fallback_used=True,
                fallback_reason=str(exc),
            ).preview

    def validate_project(self, preview: dict[str, Any]) -> dict[str, Any]:
        return ai.prepare_preview_for_output(dict(preview))

    def _build_idea_context(
        self,
        idea: str,
        *,
        selected_stack: Mapping[str, Any] | None = None,
        generation_mode: str = "fast",
        final_requirements: str = "",
    ) -> IdeaContext:
        requested_stack = ai.normalize_stack_selection(selected_stack)
        normalized_mode = ai.normalize_generation_mode(generation_mode)
        generation_context = ai.build_generation_context(
            idea,
            final_requirements,
            normalized_mode,
        )
        detected_user_choices = ai.detect_user_choices(idea)
        declared_project_type = ai.infer_declared_project_type(idea)
        context = IdeaContext(
            idea=idea,
            requested_stack=requested_stack,
            generation_mode=normalized_mode,
            final_requirements=final_requirements,
            generation_context=generation_context,
            detected_user_choices=detected_user_choices,
            declared_project_type=declared_project_type,
        )
        context.selected_stack = self.decide_stack(context)
        context.project_kind = ai.determine_project_kind(
            context.selected_stack,
            declared_project_type,
        )
        return context

    def _build_fallback_preview(self, context: IdeaContext, reason: str) -> dict[str, Any]:
        structure_plan = self.plan_project_structure(context, {})
        preview = structure_plan.to_preview_dict()
        fallback_note = (
            "Deep Mode AI enrichment was unavailable, so the 100% runnable starter project uses the safe template-generated fallback."
            if context.generation_mode == "deep"
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


agent_controller = AgentController()
