from __future__ import annotations

import asyncio
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.main import app
from app.services.agent_controller import agent_controller


class AgentControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_analyze_idea_returns_stack_and_questions(self) -> None:
        result = agent_controller.analyze_idea("Build a dashboard for a small team")

        self.assertIn("understanding", result)
        self.assertIn("suggestedStack", result)
        self.assertIn("questions", result)
        self.assertIsInstance(result["questions"], list)
        self.assertTrue(result["suggestedStack"]["backend"])

    def test_analyze_idea_uses_single_sentence_auto_mode_for_puzzle_game(self) -> None:
        result = agent_controller.analyze_idea("Build a puzzle game")

        self.assertEqual(result["suggestedStack"]["frontend"], "HTML/CSS/JavaScript")
        self.assertEqual(result["suggestedStack"]["backend"], "None")
        self.assertEqual(result["detectedProjectType"], "frontend-only")
        self.assertEqual(result["questions"], [])

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
                    "Build a multi-tenant customer success workspace with approval routing, analytics, and onboarding workflows",
                    generation_mode="fast",
                )
            )

        self.assertIn("projectName", preview)
        self.assertTrue(
            any(
                "fallback" in item.lower()
                or "template-backed defaults" in item.lower()
                or "backend templates" in item.lower()
                for item in preview["assumptions"]
            )
        )
        self.assertTrue(preview["files"])

    def test_suggest_builds_playable_puzzle_game_from_single_sentence(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            response = self.client.post(
                "/api/suggest",
                json={"idea": "Build a puzzle game", "generationMode": "fast"},
            )

        self.assertEqual(response.status_code, 200)
        preview = response.json()
        self.assertEqual(preview["selectedStack"]["frontend"], "HTML/CSS/JavaScript")
        self.assertEqual(preview["selectedStack"]["backend"], "None")

        file_map = {item["path"]: item["content"] for item in preview.get("files", [])}
        for required_path in [
            "index.html",
            "style.css",
            "script.js",
            "README.md",
            "SETUP_INSTRUCTIONS.md",
            "REQUIRED_INPUTS.md",
            "FILE_STRUCTURE.md",
            "PACKAGE_REQUIREMENTS.md",
            ".env.example",
            "setup.bat",
            "run.bat",
            "setup.sh",
            "run.sh",
        ]:
            self.assertIn(required_path, file_map)
            self.assertTrue(file_map[required_path].strip(), required_path)

        self.assertIn('id="puzzleBoard"', file_map["index.html"])
        self.assertIn("function startGame()", file_map["script.js"])
        self.assertIn("function attemptMove(index)", file_map["script.js"])

    def test_suggest_builds_todo_app_immediately_from_single_sentence(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            response = self.client.post(
                "/api/suggest",
                json={"idea": "Build a todo app", "generationMode": "fast"},
            )

        self.assertEqual(response.status_code, 200)
        preview = response.json()
        files = preview.get("files", [])
        file_map = {item["path"]: item["content"] for item in files}

        self.assertEqual(preview["selectedStack"]["frontend"], "React")
        self.assertEqual(preview["selectedStack"]["backend"], "FastAPI")
        self.assertGreaterEqual(len(files), 10)
        self.assertIn("backend/app/main.py", file_map)
        self.assertIn("backend/app/config.py", file_map)
        self.assertIn("backend/run.bat", file_map)
        self.assertIn("frontend/src/App.jsx", file_map)
        self.assertTrue(file_map["backend/app/main.py"].strip())
        self.assertTrue(file_map["frontend/src/App.jsx"].strip())
        self.assertIn("def get_env(", file_map["backend/app/config.py"])
        self.assertIn('self.database_url = get_env("DATABASE_URL"', file_map["backend/app/config.py"])
        self.assertIn("python app/main.py", file_map["backend/run.bat"])

    def test_suggest_builds_chatbot_app_with_runtime_input_prompting(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            response = self.client.post(
                "/api/suggest",
                json={"idea": "Build a chatbot app", "generationMode": "fast"},
            )

        self.assertEqual(response.status_code, 200)
        preview = response.json()
        file_map = {item["path"]: item["content"] for item in preview.get("files", [])}
        required_inputs = preview.get("requiredInputs", [])
        required_input_names = {item["name"] for item in required_inputs}

        self.assertEqual(preview["selectedStack"]["backend"], "FastAPI")
        self.assertIn("OPENAI_API_KEY", required_input_names)
        self.assertIn("backend/app/config.py", file_map)
        self.assertIn("backend/app/main.py", file_map)
        self.assertIn("backend/run.bat", file_map)
        self.assertIn("REQUIRED_INPUTS.md", file_map)
        self.assertIn(".env.example", file_map)
        self.assertIn('self.openai_api_key = get_env("OPENAI_API_KEY"', file_map["backend/app/config.py"])
        self.assertIn("input(prompt).strip()", file_map["backend/app/config.py"])
        self.assertIn("python app/main.py", file_map["backend/run.bat"])
        self.assertIn("OPENAI_API_KEY=", file_map[".env.example"])

    def test_suggest_returns_complete_buildable_preview_files(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            response = self.client.post(
                "/api/suggest",
                json={"idea": "Build a task tracker app", "generationMode": "fast"},
            )

        self.assertEqual(response.status_code, 200)
        preview = response.json()
        files = preview.get("files", [])
        self.assertGreaterEqual(len(files), 10)

        file_map = {item["path"]: item["content"] for item in files}
        for required_path in [
            "README.md",
            "SETUP_INSTRUCTIONS.md",
            "REQUIRED_INPUTS.md",
            "FILE_STRUCTURE.md",
            "PACKAGE_REQUIREMENTS.md",
            ".env.example",
            "setup.bat",
            "run.bat",
            "backend/setup.bat",
            "backend/run.bat",
            "frontend/setup.bat",
            "frontend/run.bat",
            "backend/app/main.py",
            "frontend/src/App.jsx",
        ]:
            self.assertIn(required_path, file_map)
            self.assertTrue(file_map[required_path].strip(), required_path)

        self.assertIn("app = FastAPI(", file_map["backend/app/main.py"])
        self.assertIn('@app.get("/")', file_map["backend/app/main.py"])
        self.assertIn("def get_env(", file_map["backend/app/config.py"])
        self.assertIn("export default function App()", file_map["frontend/src/App.jsx"])

    def test_validate_project_reinjects_missing_required_files(self) -> None:
        incomplete_preview = {
            "projectName": "Task Tracker",
            "problemStatement": "Build a task tracker app",
            "summary": "Starter summary",
            "selectedStack": {
                "language": "Python",
                "frontend": "React",
                "backend": "FastAPI",
                "database": "SQLite",
                "aiTools": "None",
                "deployment": "Render",
            },
            "files": [
                {"path": "backend/app/main.py", "content": ""},
                {"path": "backend/app/config.py", "content": ""},
                {"path": "frontend/src/App.jsx", "content": ""},
            ],
            "requiredInputs": [
                {
                    "name": "DATABASE_URL",
                    "required": True,
                    "example": "sqlite:///./app.db",
                    "whereToAdd": ".env",
                    "purpose": "SQLite connection string for local development.",
                }
            ],
            "envVariables": [],
            "modules": [],
            "assumptions": [],
            "architecture": [],
            "packageRequirements": [],
            "installCommands": [],
            "runCommands": [],
            "detectedUserChoices": [],
            "chosenStack": [],
        }

        validated = agent_controller.validate_project(incomplete_preview)
        file_map = {item["path"]: item["content"] for item in validated["files"]}

        self.assertTrue(file_map["backend/app/main.py"].strip())
        self.assertIn("def get_env(", file_map["backend/app/config.py"])
        self.assertTrue(file_map["frontend/src/App.jsx"].strip())
        self.assertIn("README.md", file_map)
        self.assertIn("backend/setup.bat", file_map)
        self.assertIn("frontend/run.bat", file_map)

    def test_zip_contains_same_required_files_as_preview(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            preview_response = self.client.post(
                "/api/suggest",
                json={"idea": "Build a task tracker app", "generationMode": "fast"},
            )

        self.assertEqual(preview_response.status_code, 200)
        preview = preview_response.json()
        zip_response = self.client.post("/api/zip", json={"preview": preview})
        self.assertEqual(zip_response.status_code, 200)

        zip_payload = zip_response.json()
        zip_path = Path("generated") / zip_payload["filename"]
        self.assertTrue(zip_path.exists())

        with ZipFile(zip_path) as archive:
            names = archive.namelist()

        for required_path in [
            "README.md",
            "SETUP_INSTRUCTIONS.md",
            "REQUIRED_INPUTS.md",
            "FILE_STRUCTURE.md",
            "PACKAGE_REQUIREMENTS.md",
            ".env.example",
            "backend/app/main.py",
            "frontend/src/App.jsx",
            "backend/setup.bat",
            "frontend/run.bat",
        ]:
            self.assertTrue(any(name.endswith("/" + required_path) for name in names), required_path)


if __name__ == "__main__":
    unittest.main()
