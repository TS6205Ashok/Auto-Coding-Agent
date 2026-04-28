from __future__ import annotations

import logging

from app.agents.context import AgentWorkflowContext


logger = logging.getLogger(__name__)


class ToolRecommendationAgent:
    def run(self, context: AgentWorkflowContext) -> AgentWorkflowContext:
        language = str(context.selected_stack.get("language") or "")
        frontend = str(context.selected_stack.get("frontend") or "")
        backend = str(context.selected_stack.get("backend") or "")

        if backend == "Spring Boot" or language == "Java":
            context.recommended_ide = "IntelliJ IDEA"
            context.alternative_ide = "VS Code"
            context.runtime_tools = ["JDK 17+", "Maven"]
            context.package_manager = "Maven"
        elif language == "Python":
            context.recommended_ide = "VS Code"
            context.alternative_ide = "PyCharm"
            context.runtime_tools = ["Python 3.11+", "pip"]
            if backend == "FastAPI":
                context.runtime_tools.append("Uvicorn")
            context.package_manager = "pip"
        elif language == "JavaScript" and frontend == "React":
            context.recommended_ide = "VS Code"
            context.alternative_ide = "WebStorm"
            context.runtime_tools = ["Node.js 20+", "npm"]
            context.package_manager = "npm"
        elif language == "JavaScript" and backend == "Express":
            context.recommended_ide = "VS Code"
            context.alternative_ide = "WebStorm"
            context.runtime_tools = ["Node.js 20+", "npm"]
            context.package_manager = "npm"
        elif language == "C++":
            context.recommended_ide = "CLion"
            context.alternative_ide = "Visual Studio"
            context.runtime_tools = ["CMake", "g++ or MSVC"]
            context.package_manager = "CMake"
        else:
            context.recommended_ide = "VS Code"
            context.alternative_ide = "IntelliJ IDEA"
            context.runtime_tools = ["Git", "Terminal"]
            context.package_manager = "Project-specific"

        logger.info(
            "ToolRecommendationAgent selected ide=%s alternative=%s package_manager=%s",
            context.recommended_ide,
            context.alternative_ide,
            context.package_manager,
        )
        return context
