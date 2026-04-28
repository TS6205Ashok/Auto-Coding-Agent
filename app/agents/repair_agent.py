from __future__ import annotations

import logging
from typing import Any, Mapping

from app.agents.context import AgentWorkflowContext
from app.services import ai_service as ai


logger = logging.getLogger(__name__)


class RepairAgent:
    def run(self, context: AgentWorkflowContext) -> AgentWorkflowContext:
        repaired_preview = dict(context.preview)
        repaired_preview = self._repair_by_template(repaired_preview, context)
        repaired_preview = ai.prepare_preview_for_output(repaired_preview)
        repaired_preview = self._repair_by_template(repaired_preview, context)

        original_paths = {
            str(item.get("path") or "").strip()
            for item in context.preview.get("files", [])
            if isinstance(item, Mapping)
        }
        repaired_paths = {
            str(item.get("path") or "").strip()
            for item in repaired_preview.get("files", [])
            if isinstance(item, Mapping)
        }
        context.repaired_files = sorted(original_paths.symmetric_difference(repaired_paths))
        context.preview = repaired_preview
        logger.info(
            "RepairAgent repaired issues template=%s repaired_paths=%s",
            context.template_family or "generic",
            ", ".join(context.repaired_files) or "none",
        )
        return context

    def _repair_by_template(
        self,
        preview: dict[str, Any],
        context: AgentWorkflowContext,
    ) -> dict[str, Any]:
        if context.template_family == "puzzle-game":
            allowed_paths = ai.required_preview_paths(
                {
                    "language": "JavaScript",
                    "frontend": "HTML/CSS/JavaScript",
                    "backend": "None",
                    "database": "None",
                    "aiTools": "None",
                    "deployment": "None",
                },
                ai.determine_project_kind(
                    {
                        "language": "JavaScript",
                        "frontend": "HTML/CSS/JavaScript",
                        "backend": "None",
                        "database": "None",
                        "aiTools": "None",
                        "deployment": "None",
                    }
                ),
                "puzzle-game",
            )
            preview["selectedStack"] = {
                "language": "JavaScript",
                "frontend": "HTML/CSS/JavaScript",
                "backend": "None",
                "database": "None",
                "aiTools": "None",
                "deployment": "None",
            }
            preview["templateFamily"] = "puzzle-game"
            preview["packageRequirements"] = []
            preview["installCommands"] = ["setup.bat", "./setup.sh"]
            preview["runCommands"] = ["run.bat", "./run.sh", "Open index.html directly in a browser"]
            preview["requiredInputs"] = []
            preview["envVariables"] = []
            preview["architecture"] = [
                "Static frontend application",
                "Single-page browser game",
                "No backend or database required",
            ]
            preview["files"] = [
                file_entry
                for file_entry in preview.get("files", [])
                if isinstance(file_entry, Mapping)
                and str(file_entry.get("path") or "").strip() in allowed_paths
            ]
            return preview

        target_backend = str(context.selected_stack.get("backend") or "")
        target_language = str(context.selected_stack.get("language") or "")
        filtered_files: list[dict[str, Any]] = []
        for file_entry in preview.get("files", []):
            if not isinstance(file_entry, Mapping):
                continue
            path = str(file_entry.get("path") or "").strip()
            lower = path.lower()
            if target_language == "Python" or target_backend in {"FastAPI", "Flask"}:
                if lower.endswith("pom.xml") or "src/main/java/" in lower or lower.endswith("server.js"):
                    continue
            if target_backend == "Express":
                if lower.endswith("pom.xml") or "src/main/java/" in lower:
                    continue
            if target_backend == "Spring Boot":
                if lower.endswith("server.js"):
                    continue
            filtered_files.append(dict(file_entry))
        preview["files"] = filtered_files
        return preview
