from __future__ import annotations

import logging

from app.agents.context import AgentWorkflowContext
from app.services.file_service import collect_preview_validation_findings


logger = logging.getLogger(__name__)


class ValidationAgent:
    def run(self, context: AgentWorkflowContext) -> AgentWorkflowContext:
        context.validation_findings = collect_preview_validation_findings(
            context.preview,
            selected_stack=context.selected_stack,
            project_kind=context.project_kind,
            template_family=context.template_family,
        )
        logger.info(
            "ValidationAgent validated project template=%s findings=%s",
            context.template_family or "generic",
            len(context.validation_findings),
        )
        return context
