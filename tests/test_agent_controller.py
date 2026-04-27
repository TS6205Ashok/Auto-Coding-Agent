from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import patch

from app.services.agent_controller import agent_controller


class AgentControllerTests(unittest.TestCase):
    def test_analyze_idea_returns_stack_and_questions(self) -> None:
        result = agent_controller.analyze_idea("Build a dashboard for a small team")

        self.assertIn("understanding", result)
        self.assertIn("suggestedStack", result)
        self.assertIn("questions", result)
        self.assertIsInstance(result["questions"], list)
        self.assertTrue(result["suggestedStack"]["backend"])

    def test_finalize_requirements_normalizes_partial_answers(self) -> None:
        result = agent_controller.finalize_requirements(
            "Build a starter app",
            {"database": "postgres", "backend_framework": "node", "authentication": "yes"},
            {
                "language": "Auto",
                "frontend": "React",
                "backend": "FastAPI",
                "database": "SQLite",
                "aiTools": "Auto",
                "deployment": "Render",
            },
        )

        self.assertEqual(result["selectedStack"]["database"], "PostgreSQL")
        self.assertEqual(result["selectedStack"]["backend"], "Express")
        self.assertIn("authentication-ready", result["finalRequirements"])

    def test_finalize_requirements_handles_nested_answer_values(self) -> None:
        result = agent_controller.finalize_requirements(
            "Build a starter app",
            {
                "database": {"value": "postgres"},
                "backend_framework": {"label": "node"},
                "deployment_target": ["docker"],
            },
            {
                "language": "Python",
                "frontend": "React",
                "backend": "FastAPI",
                "database": "SQLite",
                "aiTools": "None",
                "deployment": "Render",
            },
        )

        self.assertEqual(result["selectedStack"]["database"], "PostgreSQL")
        self.assertEqual(result["selectedStack"]["backend"], "Express")
        self.assertEqual(result["selectedStack"]["deployment"], "Docker")

    def test_plan_project_structure_covers_full_stack(self) -> None:
        context = agent_controller._build_idea_context(
            "Build a customer portal",
            selected_stack={
                "language": "Python",
                "frontend": "React",
                "backend": "FastAPI",
                "database": "SQLite",
                "aiTools": "None",
                "deployment": "Render",
            },
            final_requirements="Include a simple dashboard.",
        )
        plan = agent_controller.plan_project_structure(context, {})

        self.assertEqual(plan.selected_stack["frontend"], "React")
        self.assertEqual(plan.selected_stack["backend"], "FastAPI")
        self.assertTrue(any(file["path"].startswith("frontend/") for file in plan.files))
        self.assertTrue(any(file["path"].startswith("backend/") for file in plan.files))

    def test_generate_files_falls_back_without_ollama(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            preview = asyncio.run(
                agent_controller.generate_files(
                    "Build a task tracker",
                    generation_mode="fast",
                )
            )

        self.assertIn("projectName", preview)
        self.assertTrue(any("fallback" in item.lower() for item in preview["assumptions"]))
        self.assertTrue(preview["files"])


if __name__ == "__main__":
    unittest.main()
