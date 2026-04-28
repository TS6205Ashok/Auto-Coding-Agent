from __future__ import annotations

import logging
import re

from app.agents.context import AgentWorkflowContext


logger = logging.getLogger(__name__)


class StackAnalysisAgent:
    def run(self, context: AgentWorkflowContext) -> AgentWorkflowContext:
        text = context.prompt or ""
        lowered = text.lower()

        context.migration_requested = any(
            phrase in lowered
            for phrase in ("convert", "migrate", "rewrite", "port ", "move from", "translate ")
        )

        source_language = self._detect_source_language(lowered)
        source_framework = self._detect_source_framework(lowered)
        source_project_type = self._detect_project_type(lowered, source_framework)
        architecture_pattern = self._detect_architecture_pattern(lowered, source_framework, source_project_type)

        context.source_language = source_language
        context.source_framework = source_framework
        context.source_project_type = source_project_type
        context.source_architecture_pattern = architecture_pattern
        context.migration_active = bool(
            context.migration_requested
            or source_language
            or source_framework
            or self._looks_like_code(text)
        )

        logger.info(
            "StackAnalysisAgent detected source language=%s framework=%s project_type=%s architecture=%s migration_active=%s",
            source_language or "unknown",
            source_framework or "unknown",
            source_project_type or "unknown",
            architecture_pattern or "unknown",
            context.migration_active,
        )
        return context

    def _detect_source_language(self, lowered: str) -> str:
        mapping = [
            ("C++", ("main.cpp", "std::", "#include <", "using namespace std", "cout <<", "c++")),
            ("Java", ("spring boot", "pom.xml", "@springbootapplication", "public static void main", "java")),
            ("Python", ("fastapi", "flask", "requirements.txt", "def ", "import os", "python")),
            ("JavaScript", ("package.json", "server.js", "express", "react", "const ", "function ", "javascript", "node")),
            ("TypeScript", ("tsconfig.json", "typescript", "interface ", ": string", "next.js", "nestjs")),
        ]
        for language, tokens in mapping:
            if any(token in lowered for token in tokens):
                return language
        return ""

    def _detect_source_framework(self, lowered: str) -> str:
        mapping = [
            ("Spring Boot", ("spring boot", "@springbootapplication", "pom.xml")),
            ("FastAPI", ("fastapi", "from fastapi import", "uvicorn")),
            ("Flask", ("flask", "from flask import")),
            ("React", ("react", "reactdom", "src/app.jsx", "src/main.jsx")),
            ("Express", ("express", "server.js", "app.listen(", "router = express.router")),
            ("Node CLI", ("node ", "package.json", "process.argv")),
            ("C++ CLI", ("main.cpp", "std::", "#include <iostream>")),
        ]
        for framework, tokens in mapping:
            if any(token in lowered for token in tokens):
                return framework
        return ""

    def _detect_project_type(self, lowered: str, framework: str) -> str:
        if framework in {"Spring Boot", "FastAPI", "Flask", "Express"}:
            if any(token in lowered for token in ("react", "frontend", "vite", "ui", "dashboard", "todo app")):
                return "full-stack"
            return "backend"
        if framework == "React":
            return "frontend"
        if framework in {"Node CLI", "C++ CLI"}:
            return "cli"
        if any(token in lowered for token in ("full-stack", "full stack")):
            return "full-stack"
        if any(token in lowered for token in ("backend", "api")):
            return "backend"
        if any(token in lowered for token in ("frontend", "website", "portfolio", "landing page")):
            return "frontend"
        return ""

    def _detect_architecture_pattern(self, lowered: str, framework: str, project_type: str) -> str:
        if framework in {"Spring Boot", "FastAPI", "Flask", "Express"} and project_type == "backend":
            return "api_service"
        if framework == "React":
            return "spa"
        if framework in {"Node CLI", "C++ CLI"}:
            return "cli_tool"
        if project_type == "full-stack":
            return "web_app"
        if "microservice" in lowered:
            return "microservice"
        return ""

    def _looks_like_code(self, text: str) -> bool:
        if not text:
            return False
        if "\n" in text and any(marker in text for marker in ("{", "}", ";", "def ", "class ", "#include", "public class")):
            return True
        return bool(re.search(r"\b(import|class|def|public|#include|function)\b", text))
