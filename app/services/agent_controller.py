from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from app.agents.architecture_agent import ArchitectureAgent
from app.agents.context import AgentWorkflowContext
from app.agents.file_planning_agent import FilePlanningAgent
from app.agents.orchestrator_agent import orchestrator_agent
from app.agents.repair_agent import RepairAgent
from app.agents.requirement_agent import RequirementAgent
from app.services import ai_service as ai
from app.services.architecture_registry import final_architecture_from_preview


@dataclass(slots=True)
class IdeaContext:
    idea: str
    requested_stack: dict[str, str]
    generation_mode: str
    final_requirements: str = ""
    generation_context: str = ""
    detected_user_choices: list[str] = field(default_factory=list)
    declared_project_type: str = ""
    project_category: str = ""
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
    def __init__(self) -> None:
        self.orchestrator = orchestrator_agent
        self.requirement_agent = RequirementAgent()
        self.architecture_agent = ArchitectureAgent()
        self.file_planning_agent = FilePlanningAgent()
        self.repair_agent = RepairAgent()

    def understand_prompt(self, prompt: str) -> dict[str, Any]:
        workflow = self._build_workflow_context(prompt)
        return {
            "understanding": workflow.understanding,
            "detectedUserChoices": workflow.detected_user_choices,
            "projectCategory": workflow.project_category or "generic",
            "projectKind": workflow.project_kind.get("label", ""),
        }

    def detect_project_type(self, prompt: str) -> dict[str, str]:
        workflow = self._build_workflow_context(prompt)
        return {
            "projectType": workflow.project_category or "generic",
            "projectKind": workflow.project_kind.get("label", ""),
        }

    def analyze_idea(self, idea: str) -> dict[str, Any]:
        context = self._build_idea_context(idea)
        questions = self.ask_questions(context)
        result = AgentAnalysisResult(
            understanding=self.understand_prompt(idea)["understanding"],
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

    def decide_architecture(self, context: IdeaContext) -> list[str]:
        workflow = self._workflow_from_idea_context(context)
        workflow = self.architecture_agent.run(workflow)
        return workflow.architecture

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

    def plan_files(self, context: IdeaContext) -> dict[str, Any]:
        workflow = self._workflow_from_idea_context(context)
        workflow = self.file_planning_agent.run(workflow)
        return {
            "templateFamily": workflow.template_family or "generic",
            "requiredPaths": list(workflow.file_manifest),
        }

    def plan_project_structure(
        self,
        context: IdeaContext,
        raw_plan: Mapping[str, Any] | None = None,
    ) -> ProjectStructurePlan:
        workflow = self._workflow_from_idea_context(context)
        workflow = self.file_planning_agent.run(workflow, raw_plan)
        preview_files = ai.finalize_preview_files(
            project_name=workflow.project_name,
            selected_stack=workflow.selected_stack,
            project_kind=workflow.project_kind,
            required_inputs=workflow.required_inputs,
            custom_manifest=workflow.custom_manifest,
            template_family=workflow.template_family,
            raw_files=workflow.files,
        )
        file_tree = ai.build_preview_file_tree(
            preview_files,
            include_env_example=bool(workflow.env_variables),
        )
        return ProjectStructurePlan(
            project_name=workflow.project_name,
            detected_user_choices=workflow.detected_user_choices,
            selected_stack=workflow.selected_stack,
            chosen_stack=ai.build_chosen_stack(workflow.selected_stack),
            assumptions=workflow.assumptions,
            summary=workflow.summary,
            problem_statement=workflow.problem_statement,
            architecture=workflow.architecture,
            modules=workflow.modules,
            package_requirements=workflow.package_requirements,
            install_commands=workflow.install_commands,
            run_commands=workflow.run_commands,
            required_inputs=workflow.required_inputs,
            env_variables=workflow.env_variables,
            custom_manifest=workflow.custom_manifest,
            files=preview_files,
            file_tree=file_tree,
            project_kind=workflow.project_kind,
        )

    async def build_preview(
        self,
        prompt: str,
        generation_mode: str = "fast",
        selected_stack: Mapping[str, Any] | None = None,
        stack_selection_source: str = "",
        is_user_confirmed_stack: bool = False,
        final_requirements: str = "",
    ) -> dict[str, Any]:
        return await self.orchestrator.run(
            prompt,
            generation_mode,
            selected_stack=selected_stack,
            stack_selection_source=stack_selection_source,
            is_user_confirmed_stack=is_user_confirmed_stack,
            final_requirements=final_requirements,
        )

    async def generate_files(
        self,
        idea: str,
        selected_stack: dict[str, str] | None = None,
        generation_mode: str = "fast",
        stack_selection_source: str = "",
        is_user_confirmed_stack: bool = False,
        final_requirements: str = "",
    ) -> dict[str, Any]:
        return await self.build_preview(
            idea,
            generation_mode=generation_mode,
            selected_stack=selected_stack,
            stack_selection_source=stack_selection_source,
            is_user_confirmed_stack=is_user_confirmed_stack,
            final_requirements=final_requirements,
        )

    def validate_project(self, preview: dict[str, Any]) -> dict[str, Any]:
        return self.orchestrator.prepare_preview(preview)

    def repair_project(self, preview: dict[str, Any]) -> dict[str, Any]:
        workflow = self._workflow_from_preview(preview)
        workflow = self.repair_agent.run(workflow)
        return workflow.preview

    def package_zip(self, preview: dict[str, Any], generated_dir: Path) -> dict[str, str]:
        return self.orchestrator.build_zip(preview, generated_dir)

    def _build_idea_context(
        self,
        idea: str,
        *,
        selected_stack: Mapping[str, Any] | None = None,
        generation_mode: str = "fast",
        final_requirements: str = "",
    ) -> IdeaContext:
        workflow = self._build_workflow_context(
            idea,
            selected_stack=selected_stack,
            generation_mode=generation_mode,
            final_requirements=final_requirements,
        )
        return IdeaContext(
            idea=idea,
            requested_stack=workflow.requested_stack,
            generation_mode=workflow.generation_mode,
            final_requirements=final_requirements,
            generation_context=workflow.generation_context,
            detected_user_choices=workflow.detected_user_choices,
            declared_project_type=workflow.declared_project_type,
            project_category=workflow.project_category,
            selected_stack=workflow.selected_stack,
            project_kind=workflow.project_kind,
        )

    def _build_workflow_context(
        self,
        prompt: str,
        *,
        selected_stack: Mapping[str, Any] | None = None,
        generation_mode: str = "fast",
        stack_selection_source: str = "",
        is_user_confirmed_stack: bool = False,
        final_requirements: str = "",
    ) -> AgentWorkflowContext:
        normalized_stack = ai.normalize_stack_selection(selected_stack)
        source = stack_selection_source or str((selected_stack or {}).get("source") or "")
        confirmed = bool(
            is_user_confirmed_stack
            or (selected_stack or {}).get("isUserConfirmedStack")
            or (selected_stack or {}).get("is_user_confirmed")
            or (selected_stack or {}).get("isDirty")
            or (selected_stack or {}).get("is_dirty")
        )
        workflow = AgentWorkflowContext(
            prompt=prompt,
            generation_mode=generation_mode,
            requested_stack=normalized_stack,
            stack_selection_source=source,
            is_user_confirmed_stack=confirmed,
            last_modified_field=str((selected_stack or {}).get("lastModifiedField") or (selected_stack or {}).get("last_modified_field") or ""),
            last_modified_at=(selected_stack or {}).get("lastModifiedAt") or (selected_stack or {}).get("last_modified_at"),
            final_requirements=final_requirements,
        )
        workflow = self.requirement_agent.run(workflow)
        workflow = self.architecture_agent.run(workflow)
        return workflow

    def _workflow_from_idea_context(self, context: IdeaContext) -> AgentWorkflowContext:
        workflow = AgentWorkflowContext(
            prompt=context.idea,
            generation_mode=context.generation_mode,
            requested_stack=context.requested_stack,
            final_requirements=context.final_requirements,
            generation_context=context.generation_context,
            detected_user_choices=list(context.detected_user_choices),
            declared_project_type=context.declared_project_type,
            project_category=context.project_category or "generic",
            selected_stack=dict(context.selected_stack),
            project_kind=dict(context.project_kind),
        )
        workflow = self.architecture_agent.run(workflow)
        return workflow

    def _workflow_from_preview(self, preview: dict[str, Any]) -> AgentWorkflowContext:
        final_architecture = final_architecture_from_preview(preview)
        selected_stack = final_architecture.selected_stack
        project_kind = ai.determine_project_kind(selected_stack, preview.get("projectType"))
        return AgentWorkflowContext(
            prompt=str(preview.get("problemStatement") or preview.get("summary") or preview.get("projectName") or ""),
            generation_mode="fast",
            requested_stack=selected_stack,
            generation_context=str(preview.get("problemStatement") or preview.get("summary") or ""),
            declared_project_type=str(preview.get("projectType") or ""),
            project_category=ai.detect_project_category(
                str(preview.get("problemStatement") or preview.get("summary") or preview.get("projectName") or "")
            )
            or "generic",
            selected_stack=selected_stack,
            project_kind=project_kind,
            template_family=str(preview.get("templateFamily") or "").strip(),
            preview=dict(preview),
            final_architecture=final_architecture,
        )


agent_controller = AgentController()
