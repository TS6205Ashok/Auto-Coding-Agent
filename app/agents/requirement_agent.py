from __future__ import annotations

import logging

from app.agents.context import AgentWorkflowContext
from app.services import ai_service as ai


logger = logging.getLogger(__name__)


class RequirementAgent:
    def run(self, context: AgentWorkflowContext) -> AgentWorkflowContext:
        context.generation_mode = ai.normalize_generation_mode(context.generation_mode)
        context.generation_context = ai.build_generation_context(
            context.prompt,
            context.final_requirements,
            context.generation_mode,
        )
        context.detected_user_choices = ai.detect_user_choices(context.prompt)
        context.declared_project_type = ai.infer_declared_project_type(context.prompt)
        context.project_category = ai.detect_project_category(context.prompt) or "generic"
        context.direct_generation_allowed = ai.is_single_sentence_auto_mode(
            context.prompt,
            context.requested_stack,
        ) and ai.category_allows_direct_generation(context.project_category)
        logger.info(
            "RequirementAgent extracted requirements category=%s direct_generation=%s detected_choices=%s",
            context.project_category,
            context.direct_generation_allowed,
            len(context.detected_user_choices),
        )
        return context
