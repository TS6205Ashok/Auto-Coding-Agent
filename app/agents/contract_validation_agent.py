from __future__ import annotations

import logging

from app.agents.context import AgentWorkflowContext
from app.services import ai_service as ai
from app.services.architecture_registry import forbidden_path


logger = logging.getLogger(__name__)


class ContractValidationAgent:
    def run(self, context: AgentWorkflowContext) -> AgentWorkflowContext:
        if context.project_contract is None:
            raise RuntimeError("ContractValidationAgent requires CompleteProjectContract.")

        self._repair_contract(context)
        findings = self._validate_contract(context)
        context.contract_validation_findings = findings
        logger.info("ContractValidationAgent checked contract findings=%s", len(findings))
        if findings:
            raise RuntimeError("CompleteProjectContract is incomplete: " + "; ".join(findings))
        return context

    def _repair_contract(self, context: AgentWorkflowContext) -> None:
        contract = context.project_contract
        if contract is None:
            return

        removed_paths = set(context.files_to_remove)
        required_paths = set(contract.required_files)
        if context.final_architecture:
            required_paths.update(context.final_architecture.required_files)
        required_paths.update(
            str(item.get("path"))
            for item in [*context.custom_manifest, *context.domain_required_files]
            if item.get("path") and item.get("path") not in removed_paths
        )

        protected_paths = set(context.final_architecture.required_files if context.final_architecture else [])
        required_paths = {
            path
            for path in required_paths
            if path and (path not in removed_paths or path in protected_paths)
        }
        forbidden_files = list(contract.forbidden_files)
        required_paths = {
            path
            for path in required_paths
            if not any(forbidden_path(path, [pattern]) for pattern in forbidden_files)
        }

        main_file = contract.main_file or ai.main_file_for_stack(contract.selected_stack)
        if main_file:
            required_paths.add(main_file)

        contract.required_files = sorted(required_paths)
        contract.docs = [path for path in contract.required_files if path.endswith(".md") or path == ".env.example"]
        contract.setup_scripts = [
            path for path in contract.required_files if path.endswith("setup.bat") or path.endswith("setup.sh")
        ]
        contract.run_scripts = [
            path for path in contract.required_files if path.endswith("run.bat") or path.endswith("run.sh")
        ]
        contract.vscode_files = [path for path in contract.required_files if path.startswith(".vscode/")]
        contract.pages = _paths_matching(contract.required_files, ("/pages/", "src/pages/", ".html"))
        contract.backend_routes = _paths_matching(contract.required_files, ("/routers/", "/routes/", "/controller/"))
        contract.services = _paths_matching(contract.required_files, ("/services/", "/service/"))
        contract.models = _paths_matching(contract.required_files, ("/models/", "/model/"))
        contract.files_to_remove = sorted(removed_paths)

    def _validate_contract(self, context: AgentWorkflowContext) -> list[str]:
        contract = context.project_contract
        if contract is None:
            return ["CompleteProjectContract is missing."]

        findings: list[str] = []
        required_files = set(contract.required_files)
        if not required_files:
            findings.append("required_files is empty")
        if contract.main_file and contract.main_file not in required_files:
            findings.append(f"main_file is not required: {contract.main_file}")

        for label, values in {
            "docs": contract.docs,
            "setup scripts": contract.setup_scripts,
            "run scripts": contract.run_scripts,
        }.items():
            if not values:
                findings.append(f"{label} are missing")

        if context.final_architecture:
            missing_stack_files = sorted(set(context.final_architecture.required_files) - required_files)
            if missing_stack_files:
                findings.append("stack-required files missing: " + ", ".join(missing_stack_files))

        requested_paths = {
            str(item.get("path"))
            for item in [*context.custom_manifest, *context.domain_required_files]
            if item.get("path") and item.get("path") not in context.files_to_remove
        }
        missing_requested = sorted(requested_paths - required_files)
        if missing_requested:
            findings.append("domain/requested files missing: " + ", ".join(missing_requested))

        protected_paths = set(context.final_architecture.required_files if context.final_architecture else [])
        for removed_path in context.files_to_remove:
            if removed_path in required_files and removed_path not in protected_paths:
                findings.append(f"removed optional file is still required: {removed_path}")

        for required_path in required_files:
            if any(forbidden_path(required_path, [pattern]) for pattern in contract.forbidden_files):
                findings.append(f"forbidden file is required: {required_path}")

        return findings


def _paths_matching(paths: list[str], markers: tuple[str, ...]) -> list[str]:
    return sorted(path for path in paths if any(marker in path for marker in markers))
