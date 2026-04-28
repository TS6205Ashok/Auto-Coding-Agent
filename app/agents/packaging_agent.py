from __future__ import annotations

import logging
from pathlib import Path

from app.agents.context import AgentWorkflowContext
from app.agents.repair_agent import RepairAgent
from app.agents.validation_agent import ValidationAgent
from app.services import ai_service as ai
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
        context = self.validation_agent.run(context)
        if context.validation_findings:
            context = self.repair_agent.run(context)
            context = self.validation_agent.run(context)
            if context.validation_findings:
                context = self.repair_agent.run(context)
                context = self.validation_agent.run(context)
        context.preview["recommendedIde"] = context.recommended_ide or context.preview.get("recommendedIde", "")
        context.preview["alternativeIde"] = context.alternative_ide or context.preview.get("alternativeIde", "")
        context.preview["runtimeTools"] = context.runtime_tools or context.preview.get("runtimeTools", [])
        context.preview["packageManager"] = context.package_manager or context.preview.get("packageManager", "")
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
        if context.validation_findings:
            context = self.repair_agent.run(context)
            context.preview = ai.prepare_preview_for_output(context.preview)
            context = self.validation_agent.run(context)
        logger.info(
            "PackagingAgent prepared preview template=%s file_count=%s findings=%s",
            context.template_family or "generic",
            len(context.preview.get("files", [])),
            len(context.validation_findings),
        )
        return context

    def build_zip(self, preview: dict, generated_dir: Path) -> dict[str, str]:
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
        )
        context = self.prepare_preview(context)
        logger.info(
            "PackagingAgent prepared preview/ZIP template=%s file_count=%s",
            context.template_family or "generic",
            len(context.preview.get("files", [])),
        )
        return create_project_zip(context.preview, generated_dir)
