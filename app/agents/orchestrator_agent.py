from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Mapping

from app.agents.architecture_agent import ArchitectureAgent
from app.agents.code_generation_agent import CodeGenerationAgent
from app.agents.contract_agent import ContractAgent
from app.agents.context import AgentWorkflowContext
from app.agents.domain_module_extraction_agent import DomainModuleExtractionAgent
from app.agents.file_planning_agent import FilePlanningAgent
from app.agents.migration_agent import MigrationAgent
from app.agents.packaging_agent import PackagingAgent
from app.agents.repair_agent import RepairAgent
from app.agents.requirement_agent import RequirementAgent
from app.agents.stack_analysis_agent import StackAnalysisAgent
from app.agents.tool_recommendation_agent import ToolRecommendationAgent
from app.agents.validation_agent import ValidationAgent
from app.services import ai_service as ai


logger = logging.getLogger(__name__)


class OrchestratorAgent:
    def __init__(self) -> None:
        self.requirement_agent = RequirementAgent()
        self.stack_analysis_agent = StackAnalysisAgent()
        self.migration_agent = MigrationAgent()
        self.architecture_agent = ArchitectureAgent()
        self.domain_module_extraction_agent = DomainModuleExtractionAgent()
        self.file_planning_agent = FilePlanningAgent()
        self.tool_recommendation_agent = ToolRecommendationAgent()
        self.contract_agent = ContractAgent()
        self.validation_agent = ValidationAgent()
        self.repair_agent = RepairAgent()
        self.packaging_agent = PackagingAgent(
            validation_agent=self.validation_agent,
            repair_agent=self.repair_agent,
        )
        self.code_generation_agent = CodeGenerationAgent(self.file_planning_agent)

    async def run(
        self,
        prompt: str,
        generation_mode: str,
        selected_stack: Mapping[str, Any] | None = None,
        stack_selection_source: str = "",
        is_user_confirmed_stack: bool = False,
        final_requirements: str = "",
        custom_files: list[dict[str, Any]] | None = None,
        files_to_remove: list[str] | None = None,
        chat_pending_corrections: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        source = stack_selection_source or str((selected_stack or {}).get("source") or "")
        confirmed = bool(
            is_user_confirmed_stack
            or (selected_stack or {}).get("isUserConfirmedStack")
            or (selected_stack or {}).get("is_user_confirmed")
            or (selected_stack or {}).get("isDirty")
            or (selected_stack or {}).get("is_dirty")
        )
        context = AgentWorkflowContext(
            prompt=prompt,
            generation_mode=generation_mode,
            requested_stack=ai.normalize_stack_selection(selected_stack),
            stack_selection_source=source,
            is_user_confirmed_stack=confirmed,
            last_modified_field=str((selected_stack or {}).get("lastModifiedField") or (selected_stack or {}).get("last_modified_field") or ""),
            last_modified_at=(selected_stack or {}).get("lastModifiedAt") or (selected_stack or {}).get("last_modified_at"),
            final_requirements=final_requirements,
            requested_custom_files=list(custom_files or []),
            files_to_remove=list(files_to_remove or []),
            chat_pending_corrections=list(chat_pending_corrections or []),
        )
        context = self.requirement_agent.run(context)
        context = self.stack_analysis_agent.run(context)
        context = self.migration_agent.run(context)
        context = self.architecture_agent.run(context)
        context = self.domain_module_extraction_agent.run(context)
        context = self.file_planning_agent.run(context)
        context = self.contract_agent.run(context)
        context = await self.code_generation_agent.run(context)
        context = self.tool_recommendation_agent.run(context)
        context = self.packaging_agent.prepare_preview(context)
        logger.info(
            "OrchestratorAgent completed workflow category=%s template=%s file_count=%s fallback=%s",
            context.project_category,
            context.template_family or "generic",
            len(context.preview.get("files", [])),
            context.fallback_used,
        )
        return context.preview

    def prepare_preview(self, preview: dict[str, Any]) -> dict[str, Any]:
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
            files_to_remove=[
                str(item.get("path") if isinstance(item, Mapping) else item)
                for item in preview.get("filesToRemove", [])
            ],
            chat_pending_corrections=list(preview.get("chatPendingCorrections") or []),
            preview=dict(preview),
        )
        if isinstance(preview.get("projectContract"), Mapping):
            context.preview["projectContract"] = dict(preview.get("projectContract") or {})
        context = self.packaging_agent.prepare_preview(context)
        return context.preview

    def build_zip(self, preview: dict[str, Any], generated_dir: Path) -> dict[str, str]:
        return self.packaging_agent.build_zip(preview, generated_dir)


orchestrator_agent = OrchestratorAgent()
