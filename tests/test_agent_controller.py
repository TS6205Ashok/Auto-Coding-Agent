from __future__ import annotations

import asyncio
import json
import os
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.agents.orchestrator_agent import orchestrator_agent
from app.main import app
from app.services.agent_controller import agent_controller


def assert_full_runtime_instructions(testcase: unittest.TestCase, content: str) -> None:
    lowered = content.lower()
    for marker in [
        "project overview",
        "recommended ide",
        "step-by-step setup instructions",
        "required inputs",
        "how runtime input works",
        "how to run the project",
        "troubleshooting",
        "reset instructions",
    ]:
        testcase.assertIn(marker, lowered)


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

    def test_orchestrator_agent_runs_end_to_end_for_puzzle_game(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            preview = asyncio.run(
                orchestrator_agent.run(
                    "Build a puzzle game",
                    "fast",
                )
            )

        file_map = {item["path"]: item["content"] for item in preview.get("files", [])}
        self.assertEqual(preview["selectedStack"]["backend"], "None")
        self.assertIn("index.html", file_map)
        self.assertIn("style.css", file_map)
        self.assertIn("script.js", file_map)

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
            "FULL_RUNTIME_INSTRUCTIONS.md",
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
        assert_full_runtime_instructions(self, file_map["FULL_RUNTIME_INSTRUCTIONS.md"])
        self.assertNotIn("uvicorn", file_map["FULL_RUNTIME_INSTRUCTIONS.md"].lower())

    def test_puzzle_game_preview_does_not_include_backend_artifacts(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            response = self.client.post(
                "/api/suggest",
                json={"idea": "Build a puzzle game", "generationMode": "fast"},
            )

        self.assertEqual(response.status_code, 200)
        preview = response.json()
        file_paths = {item["path"] for item in preview.get("files", [])}
        run_commands = [str(item) for item in preview.get("runCommands", [])]

        self.assertNotIn("requirements.txt", file_paths)
        self.assertFalse(any(path.startswith("backend/") for path in file_paths))
        self.assertFalse(any("fastapi" in path.lower() for path in file_paths))
        self.assertFalse(any("uvicorn" in command.lower() for command in run_commands))
        self.assertFalse(any("python app/main.py" in command.lower() for command in run_commands))

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
        self.assertIn("FULL_RUNTIME_INSTRUCTIONS.md", file_map)
        self.assertIn(".env.example", file_map)
        self.assertIn('self.openai_api_key = get_env("OPENAI_API_KEY"', file_map["backend/app/config.py"])
        self.assertIn("input(prompt).strip()", file_map["backend/app/config.py"])
        self.assertIn("python app/main.py", file_map["backend/run.bat"])
        self.assertIn("OPENAI_API_KEY=", file_map[".env.example"])
        assert_full_runtime_instructions(self, file_map["FULL_RUNTIME_INSTRUCTIONS.md"])
        self.assertIn("pip install -r requirements.txt", file_map["FULL_RUNTIME_INSTRUCTIONS.md"])

    def test_suggest_migrates_cpp_project_to_python_with_tooling_and_zip_summary(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            response = self.client.post(
                "/api/suggest",
                json={"idea": "Convert my C++ project to Python", "generationMode": "fast"},
            )

        self.assertEqual(response.status_code, 200)
        preview = response.json()
        file_map = {item["path"]: item["content"] for item in preview.get("files", [])}

        self.assertEqual(preview["selectedStack"]["language"], "Python")
        self.assertEqual(preview["selectedStack"]["backend"], "FastAPI")
        self.assertEqual(preview["recommendedIde"], "VS Code")
        self.assertEqual(preview["alternativeIde"], "PyCharm")
        self.assertEqual(preview["packageManager"], "pip")
        self.assertEqual(preview["stackAnalysis"]["detectedLanguage"], "C++")
        self.assertTrue(preview["migrationSummary"])
        self.assertTrue("app/main.py" in file_map or "backend/app/main.py" in file_map)
        self.assertIn("MIGRATION_SUMMARY.md", file_map)
        self.assertIn("README.md", file_map)
        self.assertIn("FULL_RUNTIME_INSTRUCTIONS.md", file_map)
        self.assertIn("VS Code", file_map["README.md"])
        self.assertIn("migration notes", file_map["FULL_RUNTIME_INSTRUCTIONS.md"].lower())
        self.assertNotIn("pom.xml", file_map)
        self.assertNotIn("server.js", file_map)

        zip_response = self.client.post("/api/zip", json={"preview": preview})
        self.assertEqual(zip_response.status_code, 200)
        zip_payload = zip_response.json()
        zip_path = Path("generated") / zip_payload["filename"]
        self.assertTrue(zip_path.exists())

        with ZipFile(zip_path) as archive:
            names = archive.namelist()

        self.assertTrue(any(name.endswith("/MIGRATION_SUMMARY.md") for name in names))

    def test_suggest_migrates_node_todo_app_to_python_without_node_artifacts(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            response = self.client.post(
                "/api/suggest",
                json={"idea": "I built a todo app in Node with Express, convert it to Python", "generationMode": "fast"},
            )

        self.assertEqual(response.status_code, 200)
        preview = response.json()
        file_paths = {item["path"] for item in preview.get("files", [])}

        self.assertEqual(preview["selectedStack"]["language"], "Python")
        self.assertEqual(preview["selectedStack"]["backend"], "FastAPI")
        self.assertEqual(preview["stackAnalysis"]["detectedFramework"], "Express")
        self.assertEqual(preview["recommendedIde"], "VS Code")
        self.assertFalse(any(path.endswith("server.js") for path in file_paths))
        self.assertFalse(any(path.endswith("pom.xml") for path in file_paths))
        self.assertIn("MIGRATION_SUMMARY.md", file_paths)

    def test_suggest_builds_spring_boot_app_with_intellij_guidance(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            response = self.client.post(
                "/api/suggest",
                json={"idea": "Build a Spring Boot app", "generationMode": "fast"},
            )

        self.assertEqual(response.status_code, 200)
        preview = response.json()
        file_map = {item["path"]: item["content"] for item in preview.get("files", [])}

        self.assertEqual(preview["selectedStack"]["language"], "Java")
        self.assertEqual(preview["selectedStack"]["backend"], "Spring Boot")
        self.assertEqual(preview["recommendedIde"], "IntelliJ IDEA")
        self.assertEqual(preview["packageManager"], "Maven")
        self.assertIn("README.md", file_map)
        self.assertIn("FULL_RUNTIME_INSTRUCTIONS.md", file_map)
        self.assertIn("IntelliJ IDEA", file_map["README.md"])
        self.assertIn("backend/pom.xml", file_map)
        self.assertTrue(any("SpringApplication.run" in content for content in file_map.values()))
        self.assertIn("IntelliJ IDEA", file_map["FULL_RUNTIME_INSTRUCTIONS.md"])
        self.assertIn("Maven", file_map["FULL_RUNTIME_INSTRUCTIONS.md"])

    def test_java_selected_generates_spring_boot_without_python_artifacts(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            preview = asyncio.run(
                agent_controller.generate_files(
                    "create todo app",
                    selected_stack={
                        "language": "Java",
                        "frontend": "Auto",
                        "backend": "Auto",
                        "database": "Auto",
                        "aiTools": "None",
                        "deployment": "Auto",
                    },
                    generation_mode="fast",
                )
            )

        file_map = {item["path"]: item["content"] for item in preview.get("files", [])}
        self.assertEqual(preview["selectedStack"]["language"], "Java")
        self.assertEqual(preview["selectedStack"]["backend"], "Spring Boot")
        self.assertIn("backend/pom.xml", file_map)
        self.assertIn("backend/src/main/java/com/example/app/Application.java", file_map)
        self.assertIn("backend/src/main/java/com/example/app/controller/HealthController.java", file_map)
        self.assertEqual(preview["recommendedIde"], "IntelliJ IDEA")
        self.assertFalse(any(path.endswith("requirements.txt") for path in file_map))
        self.assertFalse(any(path.endswith(".py") for path in file_map))
        self.assertNotIn("FastAPI", "\n".join(file_map.values()))
        self.assertNotIn("Flask", "\n".join(file_map.values()))

    def test_flask_selected_forces_python_flask_without_java_artifacts(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            preview = asyncio.run(
                agent_controller.generate_files(
                    "create todo app",
                    selected_stack={
                        "language": "Auto",
                        "frontend": "Auto",
                        "backend": "Flask",
                        "database": "Auto",
                        "aiTools": "None",
                        "deployment": "Auto",
                    },
                    generation_mode="fast",
                )
            )

        file_map = {item["path"]: item["content"] for item in preview.get("files", [])}
        self.assertEqual(preview["selectedStack"]["language"], "Python")
        self.assertEqual(preview["selectedStack"]["backend"], "Flask")
        self.assertIn("backend/requirements.txt", file_map)
        self.assertIn("flask", file_map["backend/requirements.txt"].lower())
        self.assertIn("from flask import Flask", file_map["backend/app/main.py"])
        self.assertFalse(any(path.endswith("pom.xml") for path in file_map))
        self.assertFalse(any("src/main/java" in path for path in file_map))
        self.assertNotIn("FastAPI", "\n".join(file_map.values()))

    def test_fastapi_selected_forces_python_fastapi_without_java_artifacts(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            preview = asyncio.run(
                agent_controller.generate_files(
                    "create API app",
                    selected_stack={
                        "language": "Auto",
                        "frontend": "Auto",
                        "backend": "FastAPI",
                        "database": "Auto",
                        "aiTools": "None",
                        "deployment": "Auto",
                    },
                    generation_mode="fast",
                )
            )

        file_map = {item["path"]: item["content"] for item in preview.get("files", [])}
        self.assertEqual(preview["selectedStack"]["language"], "Python")
        self.assertEqual(preview["selectedStack"]["backend"], "FastAPI")
        self.assertIn("fastapi", file_map["backend/requirements.txt"].lower())
        self.assertIn("uvicorn", file_map["backend/requirements.txt"].lower())
        self.assertFalse(any(path.endswith("pom.xml") for path in file_map))
        self.assertFalse(any("src/main/java" in path for path in file_map))

    def test_react_only_selected_generates_frontend_without_backend(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            preview = asyncio.run(
                agent_controller.generate_files(
                    "create landing page",
                    selected_stack={
                        "language": "Auto",
                        "frontend": "React",
                        "backend": "None",
                        "database": "None",
                        "aiTools": "None",
                        "deployment": "Auto",
                    },
                    generation_mode="fast",
                )
            )

        file_paths = {item["path"] for item in preview.get("files", [])}
        self.assertEqual(preview["selectedStack"]["frontend"], "React")
        self.assertEqual(preview["selectedStack"]["backend"], "None")
        self.assertIn("frontend/package.json", file_paths)
        self.assertIn("frontend/src/main.jsx", file_paths)
        self.assertFalse(any(path.startswith("backend/") for path in file_paths))
        self.assertNotIn("requirements.txt", file_paths)
        self.assertNotIn("pom.xml", file_paths)

    def test_user_modified_stack_overrides_suggestion_to_java_mysql(self) -> None:
        modified_stack = {
            "language": "Java",
            "frontend": "React",
            "backend": "Spring Boot",
            "database": "MySQL",
            "aiTools": "None",
            "deployment": "Render",
            "source": "user_modified_suggestion",
            "lastModifiedField": "database",
            "lastModifiedAt": 1710000000000,
            "isUserConfirmedStack": True,
            "isDirty": True,
        }
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            preview = asyncio.run(
                agent_controller.generate_files(
                    "create todo app",
                    selected_stack=modified_stack,
                    stack_selection_source="user_modified_suggestion",
                    is_user_confirmed_stack=True,
                    generation_mode="fast",
                )
            )

        file_map = {item["path"]: item["content"] for item in preview.get("files", [])}
        self.assertEqual(preview["selectedStack"]["language"], "Java")
        self.assertEqual(preview["selectedStack"]["backend"], "Spring Boot")
        self.assertEqual(preview["selectedStack"]["database"], "MySQL")
        self.assertEqual(preview["finalArchitecture"]["stack_selection_source"], "user_modified_suggestion")
        self.assertIn("backend/pom.xml", file_map)
        self.assertFalse(any(path.endswith("requirements.txt") for path in file_map))

    def test_user_modified_database_only_preserves_fastapi_stack(self) -> None:
        modified_stack = {
            "language": "Python",
            "frontend": "React",
            "backend": "FastAPI",
            "database": "MySQL",
            "aiTools": "None",
            "deployment": "Render",
            "source": "user_modified_suggestion",
            "lastModifiedField": "database",
            "lastModifiedAt": 1710000000000,
            "isUserConfirmedStack": True,
            "isDirty": True,
        }
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            preview = asyncio.run(
                agent_controller.generate_files(
                    "create todo app",
                    selected_stack=modified_stack,
                    stack_selection_source="user_modified_suggestion",
                    is_user_confirmed_stack=True,
                    generation_mode="fast",
                )
            )

        file_map = {item["path"]: item["content"] for item in preview.get("files", [])}
        self.assertEqual(preview["selectedStack"]["frontend"], "React")
        self.assertEqual(preview["selectedStack"]["backend"], "FastAPI")
        self.assertEqual(preview["selectedStack"]["database"], "MySQL")
        self.assertIn("backend/requirements.txt", file_map)
        self.assertIn("frontend/src/App.jsx", file_map)

    def test_user_modified_backend_to_flask_preserves_last_backend_edit(self) -> None:
        modified_stack = {
            "language": "Java",
            "frontend": "React",
            "backend": "Flask",
            "database": "SQLite",
            "aiTools": "None",
            "deployment": "Render",
            "source": "user_modified_suggestion",
            "lastModifiedField": "backend",
            "lastModifiedAt": 1710000000000,
            "isUserConfirmedStack": True,
            "isDirty": True,
        }
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            preview = asyncio.run(
                agent_controller.generate_files(
                    "create todo app",
                    selected_stack=modified_stack,
                    stack_selection_source="user_modified_suggestion",
                    is_user_confirmed_stack=True,
                    generation_mode="fast",
                )
            )

        file_map = {item["path"]: item["content"] for item in preview.get("files", [])}
        self.assertEqual(preview["selectedStack"]["language"], "Python")
        self.assertEqual(preview["selectedStack"]["backend"], "Flask")
        self.assertIn("from flask import Flask", file_map["backend/app/main.py"])
        self.assertFalse(any("src/main/java" in path for path in file_map))

    def test_user_modified_language_to_java_preserves_last_language_edit(self) -> None:
        modified_stack = {
            "language": "Java",
            "frontend": "React",
            "backend": "FastAPI",
            "database": "SQLite",
            "aiTools": "None",
            "deployment": "Render",
            "source": "user_modified_suggestion",
            "lastModifiedField": "language",
            "lastModifiedAt": 1710000000000,
            "isUserConfirmedStack": True,
            "isDirty": True,
        }
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            preview = asyncio.run(
                agent_controller.generate_files(
                    "create todo app",
                    selected_stack=modified_stack,
                    stack_selection_source="user_modified_suggestion",
                    is_user_confirmed_stack=True,
                    generation_mode="fast",
                )
            )

        self.assertEqual(preview["selectedStack"]["language"], "Java")
        self.assertEqual(preview["selectedStack"]["backend"], "Spring Boot")
        self.assertIn(
            "backend/src/main/java/com/example/app/Application.java",
            {item["path"] for item in preview.get("files", [])},
        )

    def test_confirmed_backend_edit_overrides_sudoku_static_default(self) -> None:
        modified_stack = {
            "language": "Auto",
            "frontend": "Auto",
            "backend": "Spring Boot",
            "database": "MySQL",
            "aiTools": "None",
            "deployment": "Render",
            "source": "user_modified_suggestion",
            "lastModifiedField": "backend",
            "lastModifiedAt": 1710000000000,
            "isUserConfirmedStack": True,
            "isDirty": True,
        }
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            preview = asyncio.run(
                agent_controller.generate_files(
                    "create sudoku web",
                    selected_stack=modified_stack,
                    stack_selection_source="user_modified_suggestion",
                    is_user_confirmed_stack=True,
                    generation_mode="fast",
                )
            )

        file_paths = {item["path"] for item in preview.get("files", [])}
        self.assertEqual(preview["selectedStack"]["language"], "Java")
        self.assertEqual(preview["selectedStack"]["backend"], "Spring Boot")
        self.assertEqual(preview["selectedStack"]["database"], "MySQL")
        self.assertIn("backend/pom.xml", file_paths)
        self.assertNotIn("script.js", file_paths)

    def test_suggest_detects_pasted_fastapi_code_and_keeps_python_stack(self) -> None:
        prompt = (
            "Here is my current backend:\\n"
            "from fastapi import FastAPI\\n"
            "app = FastAPI()\\n"
            "@app.get('/health')\\n"
            "def health():\\n"
            "    return {'ok': True}\\n"
        )
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            response = self.client.post(
                "/api/suggest",
                json={"idea": prompt, "generationMode": "fast"},
            )

        self.assertEqual(response.status_code, 200)
        preview = response.json()

        self.assertEqual(preview["stackAnalysis"]["detectedLanguage"], "Python")
        self.assertEqual(preview["stackAnalysis"]["detectedFramework"], "FastAPI")
        self.assertEqual(preview["selectedStack"]["language"], "Python")
        self.assertEqual(preview["selectedStack"]["backend"], "FastAPI")
        self.assertEqual(preview["recommendedIde"], "VS Code")

    def test_suggest_builds_generic_starter_from_unknown_prompt(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            response = self.client.post(
                "/api/suggest",
                json={"idea": "Build something", "generationMode": "fast"},
            )

        self.assertEqual(response.status_code, 200)
        preview = response.json()
        file_map = {item["path"]: item["content"] for item in preview.get("files", [])}

        self.assertGreaterEqual(len(preview.get("files", [])), 10)
        self.assertIn("backend/app/main.py", file_map)
        self.assertIn("frontend/src/App.jsx", file_map)
        self.assertIn("README.md", file_map)
        self.assertIn("run.bat", file_map)
        self.assertTrue(all(str(content).strip() for content in file_map.values()))

    def test_fast_mode_unreachable_ollama_falls_back_under_five_seconds(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://127.0.0.1:11434"}, clear=False):
            started_at = time.perf_counter()
            preview = asyncio.run(
                agent_controller.generate_files(
                    "Build something",
                    generation_mode="fast",
                )
            )
            elapsed = time.perf_counter() - started_at

        self.assertLess(elapsed, 5.0)
        self.assertTrue(preview["files"])
        self.assertTrue(
            any("fallback" in item.lower() or "template" in item.lower() for item in preview["assumptions"])
        )

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
            "FULL_RUNTIME_INSTRUCTIONS.md",
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
        assert_full_runtime_instructions(self, file_map["FULL_RUNTIME_INSTRUCTIONS.md"])

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
        self.assertIn("FULL_RUNTIME_INSTRUCTIONS.md", file_map)
        self.assertIn("backend/setup.bat", file_map)
        self.assertIn("frontend/run.bat", file_map)
        assert_full_runtime_instructions(self, file_map["FULL_RUNTIME_INSTRUCTIONS.md"])

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
            "FULL_RUNTIME_INSTRUCTIONS.md",
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

    def test_zip_file_set_exactly_matches_validated_preview_file_set(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            preview_response = self.client.post(
                "/api/suggest",
                json={"idea": "create sudoku web", "generationMode": "fast"},
            )

        self.assertEqual(preview_response.status_code, 200)
        preview = preview_response.json()
        zip_response = self.client.post("/api/zip", json={"preview": preview})
        self.assertEqual(zip_response.status_code, 200)

        zip_payload = zip_response.json()
        zip_path = Path("generated") / zip_payload["filename"]
        with ZipFile(zip_path) as archive:
            archive_paths = {
                name.split("/", 1)[1]
                for name in archive.namelist()
                if "/" in name and not name.endswith("/")
            }

        preview_paths = {item["path"] for item in preview.get("files", [])}
        self.assertEqual(archive_paths, preview_paths)

    def test_regenerate_request_uses_modified_stack_not_original_preview_stack(self) -> None:
        original_stack = {
            "language": "Python",
            "frontend": "React",
            "backend": "FastAPI",
            "database": "SQLite",
            "aiTools": "None",
            "deployment": "Render",
        }
        modified_stack = {
            **original_stack,
            "language": "Java",
            "backend": "Spring Boot",
            "database": "MySQL",
            "source": "user_modified_suggestion",
            "lastModifiedField": "backend",
            "lastModifiedAt": 1710000000000,
            "isUserConfirmedStack": True,
            "isDirty": True,
        }
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            preview = asyncio.run(
                agent_controller.generate_files(
                    "create todo app",
                    selected_stack=modified_stack,
                    stack_selection_source="user_modified_suggestion",
                    is_user_confirmed_stack=True,
                    generation_mode="fast",
                )
            )

        file_paths = {item["path"] for item in preview.get("files", [])}
        self.assertEqual(preview["selectedStack"]["language"], "Java")
        self.assertEqual(preview["selectedStack"]["backend"], "Spring Boot")
        self.assertEqual(preview["selectedStack"]["database"], "MySQL")
        self.assertIn("backend/pom.xml", file_paths)
        self.assertNotIn("backend/requirements.txt", file_paths)

    def test_zip_after_stack_edit_matches_modified_java_output(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            preview_response = self.client.post(
                "/api/suggest",
                json={
                    "idea": "create todo app",
                    "generationMode": "fast",
                    "selectedStack": {
                        "language": "Java",
                        "frontend": "React",
                        "backend": "Spring Boot",
                        "database": "MySQL",
                        "aiTools": "None",
                        "deployment": "Render",
                        "source": "user_modified_suggestion",
                        "lastModifiedField": "backend",
                        "lastModifiedAt": 1710000000000,
                        "isUserConfirmedStack": True,
                        "isDirty": True,
                    },
                    "stackSelectionSource": "user_modified_suggestion",
                    "isUserConfirmedStack": True,
                },
            )

        self.assertEqual(preview_response.status_code, 200)
        preview = preview_response.json()
        zip_response = self.client.post("/api/zip", json={"preview": preview})
        self.assertEqual(zip_response.status_code, 200)

        zip_payload = zip_response.json()
        zip_path = Path("generated") / zip_payload["filename"]
        with ZipFile(zip_path) as archive:
            names = archive.namelist()

        self.assertEqual(preview["selectedStack"]["language"], "Java")
        self.assertEqual(preview["selectedStack"]["backend"], "Spring Boot")
        self.assertTrue(any(name.endswith("/backend/pom.xml") for name in names))
        self.assertFalse(any(name.endswith("/backend/requirements.txt") for name in names))

    def test_repair_removes_injected_wrong_stack_files_from_java_preview(self) -> None:
        preview = {
            "projectName": "Todo Java",
            "problemStatement": "create todo app",
            "summary": "Spring Boot todo app",
            "selectedStack": {
                "language": "Java",
                "frontend": "None",
                "backend": "Spring Boot",
                "database": "H2",
                "aiTools": "None",
                "deployment": "Render",
            },
            "recommendedIde": "IntelliJ IDEA",
            "alternativeIde": "VS Code",
            "runtimeTools": ["JDK 17+", "Maven"],
            "packageManager": "Maven",
            "files": [
                {"path": "backend/pom.xml", "content": ""},
                {"path": "backend/app/main.py", "content": "from fastapi import FastAPI\napp = FastAPI()\n"},
                {"path": "backend/requirements.txt", "content": "fastapi\nuvicorn\n"},
            ],
            "requiredInputs": [],
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

        repaired = agent_controller.validate_project(preview)
        file_map = {item["path"]: item["content"] for item in repaired.get("files", [])}

        self.assertIn("backend/pom.xml", file_map)
        self.assertIn("backend/src/main/java/com/example/app/Application.java", file_map)
        self.assertNotIn("backend/app/main.py", file_map)
        self.assertNotIn("backend/requirements.txt", file_map)
        self.assertNotIn("FastAPI", "\n".join(file_map.values()))

    def test_zip_revalidates_and_repairs_preview_before_archiving(self) -> None:
        incomplete_preview = {
            "projectName": "Puzzle Game",
            "problemStatement": "Build a puzzle game",
            "summary": "Static puzzle game starter",
            "templateFamily": "puzzle-game",
            "selectedStack": {
                "language": "JavaScript",
                "frontend": "HTML/CSS/JavaScript",
                "backend": "FastAPI",
                "database": "SQLite",
                "aiTools": "None",
                "deployment": "Render",
            },
            "runCommands": ["uvicorn app.main:app --reload"],
            "files": [
                {"path": "index.html", "content": ""},
                {"path": "script.js", "content": ""},
                {"path": "backend/app/main.py", "content": "from fastapi import FastAPI"},
            ],
            "requiredInputs": [],
            "envVariables": [],
            "modules": [],
            "assumptions": [],
            "architecture": [],
            "packageRequirements": ["fastapi"],
            "installCommands": ["pip install -r requirements.txt"],
            "detectedUserChoices": [],
            "chosenStack": [],
        }

        zip_response = self.client.post("/api/zip", json={"preview": incomplete_preview})
        self.assertEqual(zip_response.status_code, 200)

        zip_payload = zip_response.json()
        zip_path = Path("generated") / zip_payload["filename"]
        self.assertTrue(zip_path.exists())

        with ZipFile(zip_path) as archive:
            names = archive.namelist()

        self.assertTrue(any(name.endswith("/index.html") for name in names))
        self.assertTrue(any(name.endswith("/style.css") for name in names))
        self.assertTrue(any(name.endswith("/script.js") for name in names))
        self.assertTrue(any(name.endswith("/FULL_RUNTIME_INSTRUCTIONS.md") for name in names))
        self.assertFalse(any("/backend/" in name for name in names))
        self.assertFalse(any(name.endswith("/requirements.txt") for name in names))

    def test_validate_project_rebuilds_full_runtime_instructions_when_missing(self) -> None:
        incomplete_preview = {
            "projectName": "Chatbot Starter",
            "problemStatement": "Build a chatbot app",
            "summary": "Starter summary",
            "selectedStack": {
                "language": "Python",
                "frontend": "None",
                "backend": "FastAPI",
                "database": "SQLite",
                "aiTools": "OpenAI API",
                "deployment": "Render",
            },
            "recommendedIde": "VS Code",
            "alternativeIde": "PyCharm",
            "runtimeTools": ["Python 3.11+", "pip", "Uvicorn"],
            "packageManager": "pip",
            "files": [
                {"path": "backend/app/main.py", "content": "from fastapi import FastAPI\napp = FastAPI()\n"},
                {"path": "backend/app/config.py", "content": "def get_env(name):\n    return name\n"},
                {"path": "FULL_RUNTIME_INSTRUCTIONS.md", "content": ""},
            ],
            "requiredInputs": [
                {
                    "name": "OPENAI_API_KEY",
                    "required": True,
                    "example": "sk-...",
                    "whereToAdd": ".env",
                    "purpose": "API key for the chatbot provider.",
                }
            ],
            "envVariables": [],
            "modules": [],
            "assumptions": [],
            "architecture": [],
            "packageRequirements": ["fastapi"],
            "installCommands": ["pip install -r requirements.txt"],
            "runCommands": ["python app/main.py"],
            "detectedUserChoices": [],
            "chosenStack": [],
        }

        validated = agent_controller.validate_project(incomplete_preview)
        file_map = {item["path"]: item["content"] for item in validated["files"]}

        self.assertIn("FULL_RUNTIME_INSTRUCTIONS.md", file_map)
        self.assertTrue(file_map["FULL_RUNTIME_INSTRUCTIONS.md"].strip())
        assert_full_runtime_instructions(self, file_map["FULL_RUNTIME_INSTRUCTIONS.md"])

    def test_generated_projects_include_version_identity_metadata_and_output(self) -> None:
        cases = [
            (
                "build sudoku game",
                None,
                "index.html",
                "Open index.html directly in a browser",
                ["index.html", "script.js"],
            ),
            (
                "build API app",
                {
                    "language": "Auto",
                    "frontend": "None",
                    "backend": "FastAPI",
                    "database": "SQLite",
                    "aiTools": "None",
                    "deployment": "Render",
                },
                "backend/app/main.py",
                "cd backend && python -m uvicorn app.main:app --reload",
                ["backend/app/main.py", "backend/app/routers/health.py"],
            ),
            (
                "build Flask API app",
                {
                    "language": "Auto",
                    "frontend": "None",
                    "backend": "Flask",
                    "database": "SQLite",
                    "aiTools": "None",
                    "deployment": "Render",
                },
                "backend/app/main.py",
                "cd backend && python app/main.py",
                ["backend/app/main.py"],
            ),
            (
                "build React landing page",
                {
                    "language": "Auto",
                    "frontend": "React",
                    "backend": "None",
                    "database": "None",
                    "aiTools": "None",
                    "deployment": "Vercel",
                },
                "frontend/src/main.jsx",
                "cd frontend && npm run dev",
                ["frontend/src/App.jsx", "frontend/src/components/AppShell.jsx"],
            ),
            (
                "build Spring Boot app",
                {
                    "language": "Java",
                    "frontend": "None",
                    "backend": "Spring Boot",
                    "database": "H2",
                    "aiTools": "None",
                    "deployment": "Render",
                },
                "backend/src/main/java/com/example/app/Application.java",
                "cd backend && mvn spring-boot:run",
                ["backend/src/main/java/com/example/app/controller/HealthController.java"],
            ),
            (
                "build native starter",
                {
                    "language": "C++",
                    "frontend": "None",
                    "backend": "None",
                    "database": "None",
                    "aiTools": "None",
                    "deployment": "None",
                },
                "main.cpp",
                "g++ main.cpp -o app && ./app",
                ["main.cpp"],
            ),
        ]

        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            for prompt, selected_stack, main_file, run_command, source_paths in cases:
                with self.subTest(prompt=prompt):
                    preview = asyncio.run(
                        agent_controller.generate_files(
                            prompt,
                            selected_stack=selected_stack,
                            generation_mode="fast",
                        )
                    )

                    file_map = {item["path"]: item["content"] for item in preview.get("files", [])}
                    self.assertEqual(preview["generatedVersion"], "Project Agent Generated Starter v1")
                    self.assertEqual(preview["mainFile"], main_file)
                    self.assertEqual(preview["primaryRunCommand"], run_command)

                    for doc_path in ["README.md", "FULL_RUNTIME_INSTRUCTIONS.md", "PROJECT_EXPLANATION.md"]:
                        self.assertIn("Project Agent Generated Starter v1", file_map[doc_path])
                        self.assertIn(main_file, file_map[doc_path])
                        self.assertIn(run_command, file_map[doc_path])
                        self.assertIn("Selected Stack", file_map[doc_path])

                    self.assertTrue(
                        any(
                            "Project Agent Generated Starter v1" in file_map.get(path, "")
                            for path in source_paths
                        ),
                        source_paths,
                    )

    def test_generated_projects_include_vscode_run_support(self) -> None:
        cases = [
            ("build sudoku game", None),
            (
                "build API app",
                {
                    "language": "Auto",
                    "frontend": "None",
                    "backend": "FastAPI",
                    "database": "SQLite",
                    "aiTools": "None",
                    "deployment": "Render",
                },
            ),
            (
                "build React landing page",
                {
                    "language": "Auto",
                    "frontend": "React",
                    "backend": "None",
                    "database": "None",
                    "aiTools": "None",
                    "deployment": "Vercel",
                },
            ),
            (
                "build Spring Boot app",
                {
                    "language": "Java",
                    "frontend": "None",
                    "backend": "Spring Boot",
                    "database": "H2",
                    "aiTools": "None",
                    "deployment": "Render",
                },
            ),
        ]

        with patch.dict(os.environ, {"OLLAMA_BASE_URL": ""}, clear=False):
            for prompt, selected_stack in cases:
                with self.subTest(prompt=prompt):
                    preview = asyncio.run(
                        agent_controller.generate_files(
                            prompt,
                            selected_stack=selected_stack,
                            generation_mode="fast",
                        )
                    )

                    file_map = {item["path"]: item["content"] for item in preview.get("files", [])}
                    self.assertIn(".vscode/launch.json", file_map)
                    self.assertIn(".vscode/tasks.json", file_map)
                    launch = json.loads(file_map[".vscode/launch.json"])
                    tasks = json.loads(file_map[".vscode/tasks.json"])
                    self.assertTrue(launch["configurations"])
                    task_labels = {task["label"] for task in tasks["tasks"]}
                    self.assertIn("Install Dependencies", task_labels)
                    self.assertIn("Run Project", task_labels)
                    self.assertIn("Project Agent Generated Starter v1", file_map[".vscode/tasks.json"])


if __name__ == "__main__":
    unittest.main()
