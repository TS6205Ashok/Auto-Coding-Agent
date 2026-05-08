from __future__ import annotations

import logging
from pathlib import Path

from app.agents.context import AgentWorkflowContext
from app.agents.repair_agent import RepairAgent
from app.agents.validation_agent import ValidationAgent
from app.services import ai_service as ai
from app.services.architecture_registry import final_architecture_from_preview
from app.services.file_service import (
    MAX_GENERATED_FILES,
    build_deferred_modules_doc,
    build_generation_size_metadata,
    contract_required_paths,
    missing_contract_files,
    validate_generated_files,
)
from app.services.zip_service import create_project_zip


logger = logging.getLogger(__name__)


class PackagingAgent:
    def __init__(
        self,
        validation_agent: ValidationAgent,
        repair_agent: RepairAgent,
    ) -> None:
        self.validation_agent = validation_agent
        self.repair_agent = repair_agent

    def prepare_preview(self, context: AgentWorkflowContext) -> AgentWorkflowContext:
        repair_attempts = 0
        repaired_files: set[str] = set(context.repaired_files)
        initial_files = [
            item
            for item in context.preview.get("files", [])
            if isinstance(item, dict) and str(item.get("path") or "").strip()
        ]
        context = self.validation_agent.run(context)
        max_repair_attempts = 3
        if context.validation_findings:
            repair_attempts += 1
            context = self.repair_agent.run(context)
            repaired_files.update(context.repaired_files)
            context = self.validation_agent.run(context)
            if context.validation_findings:
                repair_attempts += 1
                context = self.repair_agent.run(context)
                repaired_files.update(context.repaired_files)
                context = self.validation_agent.run(context)
        context.preview["recommendedIde"] = context.recommended_ide or context.preview.get("recommendedIde", "")
        context.preview["alternativeIde"] = context.alternative_ide or context.preview.get("alternativeIde", "")
        context.preview["runtimeTools"] = context.runtime_tools or context.preview.get("runtimeTools", [])
        context.preview["packageManager"] = context.package_manager or context.preview.get("packageManager", "")
        if context.final_architecture:
            context.preview["finalArchitecture"] = context.final_architecture.to_dict()
            context.preview["stackSelectionSource"] = context.final_architecture.stack_selection_source
            context.preview["isUserConfirmedStack"] = context.is_user_confirmed_stack
            context.recommended_ide = context.recommended_ide or context.final_architecture.recommended_ide
            context.alternative_ide = context.alternative_ide or context.final_architecture.alternative_ide
            context.runtime_tools = context.runtime_tools or list(context.final_architecture.runtime_tools)
            context.package_manager = context.package_manager or context.final_architecture.package_manager
        if context.migration_summary:
            context.preview["migrationSummary"] = context.migration_summary
        if context.source_language or context.source_framework or context.source_project_type:
            context.preview["stackAnalysis"] = {
                "detectedLanguage": context.source_language or "Unknown",
                "detectedFramework": context.source_framework or "Unknown",
                "projectType": context.source_project_type or "Unknown",
                "architecturePattern": context.source_architecture_pattern or "Unknown",
            }
        context.preview = ai.prepare_preview_for_output(context.preview)
        context = self.validation_agent.run(context)
        while context.validation_findings and repair_attempts < max_repair_attempts:
            repair_attempts += 1
            context = self.repair_agent.run(context)
            repaired_files.update(context.repaired_files)
            context.preview = ai.prepare_preview_for_output(context.preview)
            context = self.validation_agent.run(context)
        if context.validation_findings:
            context.preview = ai.normalize_preview(
                {
                    "projectName": context.preview.get("projectName"),
                    "projectType": context.preview.get("projectType"),
                    "selectedStack": context.selected_stack or context.preview.get("selectedStack"),
                    "requiredInputs": context.preview.get("requiredInputs", []),
                    "customFiles": context.preview.get("customFiles", []),
                    "filesToRemove": context.preview.get("filesToRemove", []),
                    "chatPendingCorrections": context.preview.get("chatPendingCorrections", []),
                    "finalArchitecture": context.final_architecture.to_dict() if context.final_architecture else context.preview.get("finalArchitecture"),
                    "projectContract": context.preview.get("projectContract", {}),
                    "templateFamily": context.template_family or context.preview.get("templateFamily", ""),
                    "generatedVersion": context.preview.get("generatedVersion"),
                    "recommendedIde": context.preview.get("recommendedIde"),
                    "alternativeIde": context.preview.get("alternativeIde"),
                    "runtimeTools": context.preview.get("runtimeTools", []),
                    "packageManager": context.preview.get("packageManager", ""),
                    "stackSelectionSource": context.preview.get("stackSelectionSource", ""),
                    "isUserConfirmedStack": context.preview.get("isUserConfirmedStack", False),
                    "migrationSummary": context.preview.get("migrationSummary", {}),
                    "stackAnalysis": context.preview.get("stackAnalysis", {}),
                    "assumptions": [
                        *context.preview.get("assumptions", []),
                        "Validation fallback rebuilt the project from deterministic safe templates after repair attempts.",
                    ],
                },
                context.prompt,
                context.selected_stack or context.preview.get("selectedStack"),
                context.generation_mode,
                context.final_requirements or context.prompt,
            )
            context = self.validation_agent.run(context)
        self._preserve_deferred_large_project_files(context, initial_files)
        context.preview["validationStatus"] = self._build_validation_status(
            context,
            repair_attempts=repair_attempts,
            repaired_files=sorted(repaired_files),
        )
        logger.info(
            "PackagingAgent prepared preview template=%s file_count=%s findings=%s",
            context.template_family or "generic",
            len(context.preview.get("files", [])),
            len(context.validation_findings),
        )
        return context

    def _preserve_deferred_large_project_files(
        self,
        context: AgentWorkflowContext,
        initial_files: list[dict],
    ) -> None:
        if len(initial_files) <= MAX_GENERATED_FILES or context.preview.get("deferredFiles"):
            return
        current_paths = {
            str(item.get("path") or "")
            for item in context.preview.get("files", [])
            if isinstance(item, dict)
        }
        deferred_files = [
            {"path": str(item.get("path") or ""), "reason": "Deferred from optimized very large project output."}
            for item in initial_files
            if str(item.get("path") or "") and str(item.get("path") or "") not in current_paths
        ]
        if not deferred_files:
            return
        merged_files = [
            *context.preview.get("files", []),
            {"path": "DEFERRED_MODULES.md", "content": build_deferred_modules_doc(deferred_files)},
        ]
        context.preview["files"] = validate_generated_files(merged_files)
        context.preview.update(build_generation_size_metadata(context.preview["files"], deferred_files=deferred_files))

    def build_zip(self, preview: dict, generated_dir: Path) -> dict[str, str]:
        final_architecture = final_architecture_from_preview(preview)
        context = AgentWorkflowContext(
            prompt=str(preview.get("problemStatement") or preview.get("summary") or preview.get("projectName") or ""),
            generation_mode="fast",
            requested_stack=ai.normalize_stack_selection(preview.get("selectedStack")),
            selected_stack=ai.normalize_stack_selection(preview.get("selectedStack")),
            declared_project_type=str(preview.get("projectType") or ""),
            project_category=ai.detect_project_category(
                str(preview.get("problemStatement") or preview.get("summary") or preview.get("projectName") or "")
            )
            or "generic",
            project_kind=ai.determine_project_kind(ai.normalize_stack_selection(preview.get("selectedStack")), preview.get("projectType")),
            template_family=str(preview.get("templateFamily") or "").strip(),
            preview=dict(preview),
            final_architecture=final_architecture,
        )
        context.generation_quality = str(preview.get("generationQuality") or "complete")
        context.selected_stack = final_architecture.selected_stack
        context.project_kind = ai.determine_project_kind(final_architecture.selected_stack, final_architecture.project_type)
        context.recommended_ide = final_architecture.recommended_ide
        context.alternative_ide = final_architecture.alternative_ide
        context.runtime_tools = list(final_architecture.runtime_tools)
        context.package_manager = final_architecture.package_manager
        if final_architecture.stack_family == "static_frontend" and final_architecture.project_type == "game_or_puzzle":
            context.template_family = "puzzle-game"
        context = self.prepare_preview(context)
        validation_status = context.preview.get("validationStatus") or {}
        if not validation_status.get("valid"):
            findings = "; ".join(validation_status.get("findings") or [])
            raise ValueError(f"Cannot create ZIP because preview validation failed: {findings}")
        if validation_status.get("missingFiles"):
            raise ValueError(
                "Cannot create ZIP because required files are missing: "
                + ", ".join(validation_status.get("missingFiles") or [])
            )
        logger.info(
            "PackagingAgent prepared preview/ZIP template=%s file_count=%s",
            context.template_family or "generic",
            len(context.preview.get("files", [])),
        )
        return create_project_zip(context.preview, generated_dir, generated_dir.parent / "generated_projects")

    def _build_validation_status(
        self,
        context: AgentWorkflowContext,
        *,
        repair_attempts: int,
        repaired_files: list[str],
    ) -> dict[str, object]:
        project_contract = (
            context.project_contract.to_dict()
            if context.project_contract
            else context.preview.get("projectContract")
        )
        missing_files = missing_contract_files(context.preview.get("files", []), project_contract)
        generated_file_count = len(context.preview.get("files", []))
        required_file_count = len(contract_required_paths(project_contract))
        findings = list(context.validation_findings)
        for missing_path in missing_files:
            finding = f"Missing contract-required file: {missing_path}"
            if finding not in findings:
                findings.append(finding)
        return {
            "valid": not findings and not missing_files,
            "findings": findings,
            "missingFiles": missing_files,
            "repairAttempts": repair_attempts,
            "repairedFiles": repaired_files,
            "contractRequiredFileCount": required_file_count,
            "generatedFileCount": generated_file_count,
            "projectSizeTier": context.preview.get("projectSizeTier", "small"),
            "generationWarnings": context.preview.get("generationWarnings", []),
            "partialPackaging": bool(context.preview.get("partialPackaging")),
            "chunkSize": context.preview.get("chunkSize", 100),
            "chunkCount": context.preview.get("chunkCount", 1),
            "processedFileCount": context.preview.get("processedFileCount", generated_file_count),
        }
