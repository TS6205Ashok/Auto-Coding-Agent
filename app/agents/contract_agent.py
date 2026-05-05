from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from app.agents.context import AgentWorkflowContext
from app.services import ai_service as ai
from app.services.architecture_registry import FinalArchitectureDecision


@dataclass(slots=True)
class CompleteProjectContract:
    project_name: str
    project_type: str
    final_requirements: str
    selected_stack: dict[str, str]
    main_file: str
    run_method: str
    local_url: str
    required_files: list[str]
    optional_files: list[str] = field(default_factory=list)
    forbidden_files: list[str] = field(default_factory=list)
    required_inputs: list[dict[str, Any]] = field(default_factory=list)
    modules: list[dict[str, Any]] = field(default_factory=list)
    pages: list[str] = field(default_factory=list)
    backend_routes: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    docs: list[str] = field(default_factory=list)
    setup_scripts: list[str] = field(default_factory=list)
    run_scripts: list[str] = field(default_factory=list)
    vscode_files: list[str] = field(default_factory=list)
    custom_requested_files: list[dict[str, Any]] = field(default_factory=list)
    files_to_remove: list[str] = field(default_factory=list)
    validation_rules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ContractAgent:
    def run(self, context: AgentWorkflowContext) -> AgentWorkflowContext:
        architecture = context.final_architecture
        if architecture is None:
            raise RuntimeError("CompleteProjectContract cannot be built before final architecture is selected.")

        removed_paths = set(context.files_to_remove)
        protected_paths = set(architecture.required_files)
        custom_requested = [
            dict(item)
            for item in context.custom_manifest
            if item.get("path") and item.get("path") not in removed_paths
        ]
        custom_paths = {str(item.get("path")) for item in custom_requested if item.get("path")}
        required_files = sorted((protected_paths | custom_paths) - (removed_paths - protected_paths))

        context.project_contract = CompleteProjectContract(
            project_name=context.project_name or ai.clean_project_name(None, context.prompt),
            project_type=context.domain_project_type or architecture.project_type or context.project_kind.get("label", ""),
            final_requirements=context.final_requirements or context.problem_statement or context.generation_context or context.prompt,
            selected_stack=dict(architecture.selected_stack),
            main_file=architecture.main_file or ai.main_file_for_stack(architecture.selected_stack),
            run_method=architecture.main_run_target or ai.main_run_target_for_stack(architecture.selected_stack),
            local_url=architecture.local_url or ai.local_url_for_stack(architecture.selected_stack),
            required_files=required_files,
            optional_files=[],
            forbidden_files=list(architecture.forbidden_files),
            required_inputs=ai.normalize_required_inputs(context.required_inputs or architecture.required_inputs),
            modules=[dict(item) for item in ai.merge_modules(context.domain_modules, context.modules)],
            pages=_paths_matching(required_files, ("/pages/", "src/pages/", ".html")),
            backend_routes=_paths_matching(required_files, ("/routers/", "/routes/", "/controller/")),
            services=_paths_matching(required_files, ("/services/", "/service/")),
            models=_paths_matching(required_files, ("/models/", "/model/")),
            docs=[path for path in required_files if path.endswith(".md") or path == ".env.example"],
            setup_scripts=[path for path in required_files if path.endswith("setup.bat") or path.endswith("setup.sh")],
            run_scripts=[path for path in required_files if path.endswith("run.bat") or path.endswith("run.sh")],
            vscode_files=[path for path in required_files if path.startswith(".vscode/")],
            custom_requested_files=custom_requested,
            files_to_remove=sorted(removed_paths),
            validation_rules=[
                "all_required_files_exist",
                "files_are_non_empty",
                "source_files_are_not_placeholder_only",
                "main_file_is_runnable",
                "requested_chat_files_exist",
                "removed_optional_files_absent",
                "required_inputs_documented_and_prompted",
                "zip_matches_validated_preview",
            ],
        )
        return context


def _paths_matching(paths: list[str], markers: tuple[str, ...]) -> list[str]:
    return sorted(path for path in paths if any(marker in path for marker in markers))
