from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import httpx
from dotenv import load_dotenv

from .file_service import (
    GENERATED_VERSION_LABEL,
    assemble_complete_preview_files,
    build_preview_file_tree,
    finalize_preview_files,
    local_url_for_stack,
    main_file_for_stack,
    main_run_target_for_stack,
    primary_run_command,
    required_preview_paths as _required_preview_paths,
)


load_dotenv()

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder"
FAST_PLANNER_TIMEOUT_SECONDS = 4.0
DEEP_PREVIEW_TIMEOUT_SECONDS = 70.0
MIN_CUSTOM_PASS_SECONDS = 8.0
MAX_CUSTOM_FILES = 8
MAX_CUSTOM_FILE_LINES = 300
FAST_PLANNER_RESPONSE_BYTES_LIMIT = 48 * 1024
REQUIRED_PLANNER_KEYS = {
    "projectName",
    "projectType",
    "selectedStack",
    "modules",
    "packageRequirements",
    "installCommands",
    "runCommands",
    "requiredInputs",
    "envVariables",
    "customFiles",
}

logger = logging.getLogger(__name__)

STACK_FIELDS = (
    "language",
    "frontend",
    "backend",
    "database",
    "aiTools",
    "deployment",
)
STACK_DEFAULTS = {
    "language": "Auto",
    "frontend": "Auto",
    "backend": "Auto",
    "database": "Auto",
    "aiTools": "Auto",
    "deployment": "Auto",
}
NONE_LIKE = {"", "Auto", "None"}
YES_ANSWERS = {"yes", "y", "true", "1", "required", "needed"}
NO_ANSWERS = {"no", "n", "false", "0", "none", "not needed"}
BOOLEAN_QUESTION_IDS = {"authentication", "admin_dashboard", "email_smtp", "payment_system"}
SUPPORTED_SCOPE_VALUES = {"full-stack", "backend-only", "frontend-only"}
SUPPORTED_LANGUAGE_VALUES = {"Python", "JavaScript", "TypeScript", "Java"}
SUPPORTED_FRONTEND_VALUES = {"React", "Next.js", "Vue", "HTML/CSS/JavaScript", "None"}
SUPPORTED_BACKEND_VALUES = {"FastAPI", "Flask", "Express", "NestJS", "Spring Boot"}
SUPPORTED_DATABASE_VALUES = {"SQLite", "PostgreSQL", "MySQL", "MongoDB", "None"}
SUPPORTED_AI_VALUES = {"None", "Ollama", "OpenAI API", "LangChain"}
SUPPORTED_DEPLOYMENT_VALUES = {"Render", "Railway", "Vercel", "Docker", "None"}
SUPPORTED_COMPLEXITY_VALUES = {"Simple", "Standard", "Advanced"}
SUPPORTED_ROLE_VALUES = {
    "Single user / no roles",
    "Basic roles (admin + user)",
    "Custom roles needed",
}
CANONICAL_ANSWER_ALIASES = {
    "project_scope": {
        "full stack": "full-stack",
        "full-stack": "full-stack",
        "fullstack": "full-stack",
        "frontend and backend": "full-stack",
        "backend only": "backend-only",
        "backend-only": "backend-only",
        "api only": "backend-only",
        "service only": "backend-only",
        "frontend only": "frontend-only",
        "frontend-only": "frontend-only",
        "ui only": "frontend-only",
    },
    "language": {
        "python": "Python",
        "py": "Python",
        "javascript": "JavaScript",
        "js": "JavaScript",
        "typescript": "TypeScript",
        "ts": "TypeScript",
        "java": "Java",
    },
    "frontend_framework": {
        "react": "React",
        "next": "Next.js",
        "nextjs": "Next.js",
        "next.js": "Next.js",
        "vue": "Vue",
        "vanilla": "HTML/CSS/JavaScript",
        "html": "HTML/CSS/JavaScript",
        "html/css/javascript": "HTML/CSS/JavaScript",
        "plain html": "HTML/CSS/JavaScript",
        "none": "None",
        "no frontend": "None",
    },
    "backend_framework": {
        "fastapi": "FastAPI",
        "flask": "Flask",
        "express": "Express",
        "node": "Express",
        "node.js": "Express",
        "nestjs": "NestJS",
        "nest": "NestJS",
        "spring": "Spring Boot",
        "spring boot": "Spring Boot",
        "none": "None",
        "no backend": "None",
    },
    "database": {
        "sqlite": "SQLite",
        "postgres": "PostgreSQL",
        "postgresql": "PostgreSQL",
        "postgre sql": "PostgreSQL",
        "mysql": "MySQL",
        "mongo": "MongoDB",
        "mongodb": "MongoDB",
        "none": "None",
        "no database": "None",
    },
    "ai_integration": {
        "none": "None",
        "no": "None",
        "ollama": "Ollama",
        "openai": "OpenAI API",
        "openai api": "OpenAI API",
        "langchain": "LangChain",
    },
    "deployment_target": {
        "render": "Render",
        "railway": "Railway",
        "vercel": "Vercel",
        "docker": "Docker",
        "container": "Docker",
        "none": "None",
    },
    "complexity_level": {
        "simple": "Simple",
        "basic": "Simple",
        "beginner": "Simple",
        "standard": "Standard",
        "normal": "Standard",
        "default": "Standard",
        "advanced": "Advanced",
        "complex": "Advanced",
    },
    "user_roles": {
        "single": "Single user / no roles",
        "single user": "Single user / no roles",
        "no roles": "Single user / no roles",
        "admin and user": "Basic roles (admin + user)",
        "admin + user": "Basic roles (admin + user)",
        "basic roles": "Basic roles (admin + user)",
        "custom roles": "Custom roles needed",
        "custom": "Custom roles needed",
        "manager roles": "Custom roles needed",
    },
}

KEYWORD_MAP = {
    "language": {
        "Python": ("python", "fastapi", "flask", "django"),
        "JavaScript": ("javascript", "node", "express"),
        "TypeScript": ("typescript", "next.js", "nextjs", "nest", "nestjs"),
        "Java": ("java", "spring", "spring boot"),
    },
    "frontend": {
        "React": ("react",),
        "Next.js": ("next.js", "nextjs"),
        "Vue": ("vue",),
        "HTML/CSS/JavaScript": ("html", "css", "javascript", "vanilla js", "frontend"),
        "None": ("api only", "backend only", "cli", "script"),
    },
    "backend": {
        "FastAPI": ("fastapi",),
        "Flask": ("flask",),
        "Express": ("express", "node api"),
        "NestJS": ("nestjs", "nest js"),
        "Spring Boot": ("spring boot", "spring"),
        "None": ("static site", "frontend only"),
    },
    "database": {
        "SQLite": ("sqlite",),
        "PostgreSQL": ("postgres", "postgresql"),
        "MySQL": ("mysql",),
        "MongoDB": ("mongodb", "mongo"),
        "None": ("no database", "without database", "in memory"),
    },
    "aiTools": {
        "Ollama": ("ollama", "local llm", "qwen", "llama"),
        "OpenAI API": ("openai", "gpt"),
        "LangChain": ("langchain",),
        "None": ("no ai", "without ai"),
    },
    "deployment": {
        "Render": ("render",),
        "Railway": ("railway",),
        "Vercel": ("vercel",),
        "Docker": ("docker", "container"),
        "None": ("no deployment",),
    },
}

PROJECT_CATEGORY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("game", ("puzzle", "sliding puzzle", "memory", "tic tac toe", "quiz", "game")),
    ("todo", ("todo", "to-do", "task tracker", "tasks")),
    ("inventory", ("inventory", "stock", "warehouse")),
    ("dashboard", ("dashboard", "analytics", "admin dashboard")),
    ("chat", ("chat", "messaging", "messenger")),
    ("ecommerce", ("ecommerce", "e-commerce", "store", "shop", "checkout")),
    ("blog", ("blog", "cms", "posts")),
    ("portfolio", ("portfolio", "personal site", "resume site")),
    ("api-backend", ("api backend", "api", "backend service", "service api")),
    ("full-stack-crud", ("crud",)),
]

PROJECT_CATEGORY_DEFAULT_STACKS: dict[str, dict[str, str]] = {
    "game": {
        "language": "JavaScript",
        "frontend": "HTML/CSS/JavaScript",
        "backend": "None",
        "database": "None",
        "aiTools": "None",
        "deployment": "None",
    },
    "todo": {
        "language": "Python",
        "frontend": "React",
        "backend": "FastAPI",
        "database": "SQLite",
        "aiTools": "None",
        "deployment": "Render",
    },
    "inventory": {
        "language": "Python",
        "frontend": "React",
        "backend": "FastAPI",
        "database": "SQLite",
        "aiTools": "None",
        "deployment": "Render",
    },
    "dashboard": {
        "language": "Python",
        "frontend": "React",
        "backend": "FastAPI",
        "database": "SQLite",
        "aiTools": "None",
        "deployment": "Render",
    },
    "chat": {
        "language": "Python",
        "frontend": "React",
        "backend": "FastAPI",
        "database": "SQLite",
        "aiTools": "OpenAI API",
        "deployment": "Render",
    },
    "ecommerce": {
        "language": "Python",
        "frontend": "React",
        "backend": "FastAPI",
        "database": "SQLite",
        "aiTools": "None",
        "deployment": "Render",
    },
    "blog": {
        "language": "Python",
        "frontend": "React",
        "backend": "FastAPI",
        "database": "SQLite",
        "aiTools": "None",
        "deployment": "Render",
    },
    "portfolio": {
        "language": "JavaScript",
        "frontend": "React",
        "backend": "None",
        "database": "None",
        "aiTools": "None",
        "deployment": "Vercel",
    },
    "api-backend": {
        "language": "Python",
        "frontend": "None",
        "backend": "FastAPI",
        "database": "SQLite",
        "aiTools": "None",
        "deployment": "Render",
    },
    "full-stack-crud": {
        "language": "Python",
        "frontend": "React",
        "backend": "FastAPI",
        "database": "SQLite",
        "aiTools": "None",
        "deployment": "Render",
    },
}


async def generate_project_preview(
    idea: str,
    selected_stack: dict[str, str] | None = None,
    generation_mode: str = "fast",
    final_requirements: str = "",
) -> dict[str, Any]:
    from .agent_controller import agent_controller

    return await agent_controller.generate_files(
        idea,
        selected_stack,
        generation_mode,
        final_requirements,
    )


def prepare_preview_for_output(preview: dict[str, Any]) -> dict[str, Any]:
    base_idea = (
        str(preview.get("problemStatement") or "").strip()
        or str(preview.get("summary") or "").strip()
        or str(preview.get("projectName") or "").strip()
        or "Generated project"
    )
    requested_stack = normalize_stack_selection(preview.get("selectedStack"))
    return normalize_preview(preview, base_idea, requested_stack, "fast")


async def generate_project_plan(
    idea: str,
    requested_stack: dict[str, str],
    generation_mode: str,
    deadline: float,
) -> dict[str, Any]:
    timeout_seconds = remaining_time(deadline)
    if timeout_seconds <= 0:
        raise TimeoutError("Preview time budget was exhausted before generation started.")

    prompt = build_planning_prompt(idea, requested_stack, generation_mode)
    planner_payload = await call_ollama_json(
        prompt,
        timeout_seconds,
        enforce_compact_output=(generation_mode == "fast"),
        response_kind="planner",
    )
    return validate_planner_payload(planner_payload)


async def generate_deep_custom_files(
    idea: str,
    project_name: str,
    selected_stack: dict[str, str],
    custom_manifest: list[dict[str, str]],
    timeout_seconds: float,
) -> list[dict[str, str]]:
    prompt = build_custom_files_prompt(idea, project_name, selected_stack, custom_manifest)
    payload = await call_ollama_json(
        prompt,
        timeout_seconds,
        enforce_compact_output=False,
        response_kind="custom",
    )
    files = normalize_files(payload.get("files"))

    allowed_paths = {item["path"] for item in custom_manifest}
    trimmed: list[dict[str, str]] = []
    for file_entry in files:
        if file_entry["path"] not in allowed_paths:
            continue
        content = trim_content_lines(file_entry["content"])
        trimmed.append({"path": file_entry["path"], "content": content})
    return trimmed


async def call_ollama_json(
    prompt: str,
    timeout_seconds: float,
    *,
    enforce_compact_output: bool,
    response_kind: str,
) -> dict[str, Any]:
    configured_base_url = str(os.getenv("OLLAMA_BASE_URL") or "").strip()
    if not configured_base_url:
        raise RuntimeError(
            "AI generation is unavailable because OLLAMA_BASE_URL is not configured."
        )

    base_url = configured_base_url.rstrip("/")
    model = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL).strip() or DEFAULT_OLLAMA_MODEL
    safe_timeout = max(1.0, timeout_seconds)
    if enforce_compact_output:
        safe_timeout = min(safe_timeout, 3.0)
    request_timeout = httpx.Timeout(
        connect=min(1.0 if enforce_compact_output else 3.5, safe_timeout),
        read=safe_timeout,
        write=min(2.0 if enforce_compact_output else 5.0, safe_timeout),
        pool=min(2.0 if enforce_compact_output else 5.0, safe_timeout),
    )

    try:
        async with httpx.AsyncClient(timeout=request_timeout) as client:
            response = await client.post(
                f"{base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"AI generation is unavailable because Ollama could not be reached at {base_url}."
        ) from exc

    if response.status_code >= 400:
        detail = response.text.strip() or f"HTTP {response.status_code}"
        raise RuntimeError(f"Ollama returned an error: {detail}")

    payload = response.json()
    raw_text = str(payload.get("response") or "").strip()
    if not raw_text:
        raise RuntimeError("Ollama returned an empty response.")
    if enforce_compact_output and len(raw_text.encode("utf-8")) > FAST_PLANNER_RESPONSE_BYTES_LIMIT:
        raise ValueError(
            f"{response_kind.capitalize()} response exceeded the compact output limit for Fast Mode."
        )

    return parse_model_json(raw_text)


def build_planning_prompt(
    idea: str,
    selected_stack: dict[str, str],
    generation_mode: str,
) -> str:
    stack_summary = "\n".join(
        f"- {field}: {selected_stack.get(field, 'Auto')}" for field in STACK_FIELDS
    )

    return f"""
You are Project Agent.

Return compact JSON only. No markdown. No commentary.

Goal:
- Plan a 100% runnable starter project.
- Do not generate the entire project.
- The backend will create standard files from templates.

Rules:
1. Preserve user-specified language, frameworks, tools, and deployment choices.
2. Respect any non-Auto selectedStack values exactly.
3. Choose beginner-friendly defaults only for missing stack categories.
4. For full-stack output, plan both frontend and backend.
5. Do not include README, dependency manifests, setup scripts, run scripts, env files, config boilerplate, or installed libraries in customFiles.
6. customFiles must contain only project-specific business logic files, max {MAX_CUSTOM_FILES}.
7. Each custom file should be worth generating because it contains app-specific logic or UI, not generic boilerplate.
8. Detect required external inputs and return them in requiredInputs.
9. If the project uses auth, database, email, payments, AI providers, or OAuth, include the needed keys in requiredInputs.
10. Do not claim this is a production-finished application. It is a 100% runnable starter project.

Return this exact top-level shape:
{{
  "projectName": "string",
  "projectType": "frontend-only | backend-only | full-stack",
  "selectedStack": {{
    "language": "string",
    "frontend": "string",
    "backend": "string",
    "database": "string",
    "aiTools": "string",
    "deployment": "string"
  }},
  "modules": [
    {{
      "name": "string",
      "purpose": "string",
      "keyFiles": ["string"]
    }}
  ],
  "packageRequirements": ["string"],
  "installCommands": ["string"],
  "runCommands": ["string"],
  "requiredInputs": [
    {{
      "name": "string",
      "required": true,
      "example": "string",
      "whereToAdd": ".env",
      "purpose": "string"
    }}
  ],
  "envVariables": [
    {{
      "name": "string",
      "value": "string",
      "description": "string"
    }}
  ],
  "customFiles": [
    {{
      "path": "relative/path",
      "purpose": "why this file is needed"
    }}
  ]
}}

Mode:
- generationMode: {generation_mode}
- Fast Mode should keep customFiles compact and rely on backend templates for standard files.
- Deep Mode may propose richer custom business files, but still max {MAX_CUSTOM_FILES}.

Selected stack:
{stack_summary}

Project idea:
{idea}
""".strip()


def build_custom_files_prompt(
    idea: str,
    project_name: str,
    selected_stack: dict[str, str],
    custom_manifest: list[dict[str, str]],
) -> str:
    manifest_json = json.dumps(custom_manifest, indent=2)
    stack_json = json.dumps(selected_stack, indent=2)
    return f"""
You are Project Agent.

Generate only the custom business-logic files listed below.
Return JSON only in this shape:
{{
  "files": [
    {{
      "path": "relative/path",
      "content": "file content"
    }}
  ]
}}

Rules:
1. Generate only the listed files.
2. Do not generate standard boilerplate, dependency manifests, docs, setup scripts, or env files.
3. Keep each file under {MAX_CUSTOM_FILE_LINES} lines.
4. Use the selected stack exactly.
5. Produce runnable starter logic, not empty placeholders.

Project name: {project_name}
Project idea: {idea}
Selected stack:
{stack_json}

Requested custom files:
{manifest_json}
""".strip()


def parse_model_json(raw_text: str) -> dict[str, Any]:
    text = strip_markdown_fences(raw_text)
    candidate = extract_json_object(text)
    if not candidate:
        raise ValueError("Could not recover a JSON object from the AI response.")

    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ValueError("AI response JSON was not an object.")
    return parsed


def strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def extract_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        return ""

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return ""


def build_fallback_preview(
    idea: str,
    requested_stack: dict[str, str],
    generation_mode: str,
    reason: str,
    generation_context: str | None = None,
) -> dict[str, Any]:
    preview = normalize_preview(
        {},
        idea,
        requested_stack,
        generation_mode,
        requirements_context=generation_context or idea,
    )
    fallback_note = (
        "Fast Mode returned a complete template-based preview because AI generation was unavailable."
        if generation_mode == "fast"
        else "Deep Mode AI enrichment was unavailable, so a complete template-based preview was returned."
    )
    preview["assumptions"] = dedupe_list(
        [
            fallback_note,
            f"Template fallback preview was generated because the AI planner could not complete in time or returned invalid output: {reason}",
            *preview.get("assumptions", []),
        ]
    )
    return preview


def build_generation_context(
    idea: str,
    final_requirements: str = "",
    generation_mode: str = "fast",
) -> str:
    cleaned_idea = idea.strip()
    cleaned_requirements = final_requirements.strip()
    if not cleaned_requirements:
        return cleaned_idea
    if generation_mode == "fast":
        return (
            f"Idea: {cleaned_idea}\n"
            "Final requirements:\n"
            f"{cleaned_requirements}"
        ).strip()
    return (
        f"Original idea:\n{cleaned_idea}\n\n"
        "Finalized requirements from the agent conversation:\n"
        f"{cleaned_requirements}"
    ).strip()


def analyze_project_idea(idea: str) -> dict[str, Any]:
    detected_choices = detect_user_choices(idea)
    suggested_stack = resolve_selected_stack(
        idea,
        normalize_stack_selection({}),
        None,
        detected_choices,
    )
    project_kind = determine_project_kind(suggested_stack, infer_declared_project_type(idea))
    questions = build_agent_questions(idea, suggested_stack, project_kind)
    return {
        "understanding": build_agent_understanding(idea, suggested_stack, project_kind),
        "assumptions": build_agent_analysis_assumptions(suggested_stack, project_kind, questions),
        "suggestedStack": suggested_stack,
        "stackReasons": build_stack_reasons(suggested_stack, project_kind),
        "questions": questions,
        "detectedProjectType": project_kind["label"],
        "confidence": compute_agent_confidence(idea, detected_choices, questions, project_kind),
    }


def finalize_agent_requirements(
    idea: str,
    answers: Mapping[str, Any] | None,
    suggested_stack: Mapping[str, Any] | None,
) -> dict[str, Any]:
    normalized_answers = normalize_agent_answers(answers)
    selected_stack = normalize_stack_selection(suggested_stack)
    selected_stack = apply_agent_answers_to_stack(idea, selected_stack, normalized_answers)
    project_kind = determine_project_kind(selected_stack, normalized_answers.get("project_scope"))
    final_requirements = build_final_requirements_summary(
        idea,
        normalized_answers,
        selected_stack,
        project_kind,
    )
    assumptions = build_agent_finalize_assumptions(
        normalized_answers,
        selected_stack,
        project_kind,
    )
    return {
        "finalRequirements": final_requirements,
        "selectedStack": selected_stack,
        "assumptions": assumptions,
    }


def infer_declared_project_type(idea: str) -> str:
    lowered = idea.lower()
    if any(token in lowered for token in ("full stack", "full-stack", "frontend and backend")):
        return "full-stack"
    if any(token in lowered for token in ("backend only", "api only", "service only")):
        return "backend-only"
    if any(token in lowered for token in ("frontend only", "landing page only", "static site")):
        return "frontend-only"
    return ""


def detect_project_category(idea: str) -> str:
    lowered = idea.lower()
    for category, keywords in PROJECT_CATEGORY_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return category
    return ""


def category_stack_defaults(category: str) -> dict[str, str]:
    return dict(PROJECT_CATEGORY_DEFAULT_STACKS.get(category, {}))


def category_template_family(category: str) -> str:
    if category == "game":
        return "puzzle-game"
    return ""


def is_single_sentence_auto_mode(
    idea: str,
    requested_stack: Mapping[str, Any] | None = None,
) -> bool:
    del requested_stack
    cleaned = idea.strip()
    if not cleaned or "\n" in cleaned:
        return False
    words = re.findall(r"[A-Za-z0-9]+", cleaned)
    return len(words) <= 14


def category_allows_direct_generation(category: str) -> bool:
    return category in PROJECT_CATEGORY_DEFAULT_STACKS


def build_agent_understanding(
    idea: str,
    suggested_stack: dict[str, str],
    project_kind: dict[str, Any],
) -> str:
    description = idea.strip().rstrip(".")
    if len(description) > 180:
        description = description[:177].rstrip() + "..."
    stack_bits: list[str] = []
    if project_kind["hasFrontend"]:
        stack_bits.append(suggested_stack["frontend"])
    if project_kind["hasBackend"]:
        stack_bits.append(suggested_stack["backend"])
    stack_text = " + ".join(bit for bit in stack_bits if bit not in NONE_LIKE) or suggested_stack["language"]
    return (
        f"I understood your idea as a {project_kind['label']} project focused on {description}. "
        f"My starting recommendation is {stack_text} with template-generated runtime structure so you can get to a runnable starter quickly."
    )


def build_agent_analysis_assumptions(
    suggested_stack: dict[str, str],
    project_kind: dict[str, Any],
    questions: list[dict[str, Any]],
) -> list[str]:
    assumptions = [
        "Questions are limited to decisions that change architecture, dependencies, or required files.",
        "If you skip the questions, the suggested stack and defaults will be used to generate the project.",
    ]
    if project_kind["isFullStack"]:
        assumptions.append("The app currently looks like a full-stack build, so both frontend and backend are planned by default.")
    elif project_kind["hasBackend"]:
        assumptions.append("The current recommendation leans backend-first and will keep the frontend optional unless you add it.")
    else:
        assumptions.append("The current recommendation treats this as a frontend-focused starter unless you add backend needs.")
    if questions:
        assumptions.append("Each question starts with your own input first. If you leave it blank, the agent will suggest a default and explain the benefit.")
    else:
        assumptions.append("This idea is short enough for single-sentence auto mode, so the agent can generate a runnable starter immediately with safe defaults.")
    if suggested_stack.get("deployment") == "Render":
        assumptions.append("Render is used as a deployment default when no target is mentioned explicitly.")
    return dedupe_list(assumptions)


def build_stack_reasons(
    suggested_stack: dict[str, str],
    project_kind: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    backend = suggested_stack.get("backend", "Auto")
    frontend = suggested_stack.get("frontend", "Auto")
    database = suggested_stack.get("database", "Auto")
    deployment = suggested_stack.get("deployment", "Auto")
    ai_tools = suggested_stack.get("aiTools", "Auto")

    if backend == "FastAPI":
        reasons.append("FastAPI is a beginner-friendly Python API framework that pairs well with the current runnable starter templates.")
    elif backend == "Express":
        reasons.append("Express keeps a Node-based backend lightweight and easy to extend for API-first projects.")
    elif backend == "Spring Boot":
        reasons.append("Spring Boot was chosen because the idea strongly suggests a Java-based backend stack.")

    if frontend == "React":
        reasons.append("React with Vite gives a fast local frontend starter and aligns with the existing component templates.")
    elif frontend == "HTML/CSS/JavaScript":
        reasons.append("A lightweight HTML/CSS/JavaScript frontend keeps the starter simple when a framework was not clearly required.")
    elif frontend == "None":
        reasons.append("No frontend was selected because the current idea reads like an API, worker, or backend-only service.")

    if database == "SQLite":
        reasons.append("SQLite keeps local setup simple for a runnable starter when the app does not need heavier infrastructure yet.")
    elif database == "PostgreSQL":
        reasons.append("PostgreSQL is a strong default when the app looks multi-user, relational, or production-oriented.")
    elif database == "None":
        reasons.append("No database was selected because the current idea can start without persistent storage.")

    if ai_tools == "Ollama":
        reasons.append("Ollama stays the local-first AI default when the idea explicitly suggests AI features.")
    elif ai_tools == "None":
        reasons.append("No AI tool was added because the current idea does not require model integration.")

    if deployment == "Render":
        reasons.append("Render is the default deployment target because it is simple for web apps and matches the current starter flow.")
    elif deployment == "Docker":
        reasons.append("Docker is selected because the idea or deployment preference points toward containerized delivery.")

    if project_kind["isFullStack"]:
        reasons.append("Both frontend and backend are included because the idea appears to need a user interface and a service layer.")
    return dedupe_list(reasons)


def build_agent_questions(
    idea: str,
    suggested_stack: dict[str, str],
    project_kind: dict[str, Any],
) -> list[dict[str, Any]]:
    category = detect_project_category(idea)
    if is_single_sentence_auto_mode(idea) and category_allows_direct_generation(category):
        return []

    lowered = idea.lower()
    questions: list[dict[str, Any]] = []

    def add_question(
        question_id: str,
        question: str,
        question_type: str,
        default: str,
        reason: str,
        options: Sequence[str] | None = None,
    ) -> None:
        questions.append(
            {
                "id": question_id,
                "question": question,
                "type": question_type,
                "options": list(options or []),
                "default": default,
                "reason": reason,
            }
        )

    has_explicit_frontend = bool(match_keyword("frontend", lowered))
    has_explicit_backend = bool(match_keyword("backend", lowered))

    if not infer_declared_project_type(idea) and not (has_explicit_frontend and has_explicit_backend):
        add_question(
            "project_scope",
            "Do you need both a frontend and a backend for this project?",
            "choice",
            project_kind["label"],
            "If you leave this blank, I will suggest the current project scope because it keeps the runnable starter aligned with the folders and runtime scripts your idea appears to need.",
            ["full-stack", "backend-only", "frontend-only"],
        )

    if not match_keyword("backend", lowered) and project_kind["hasBackend"]:
        add_question(
            "backend_framework",
            "Which backend framework do you prefer?",
            "choice",
            suggested_stack["backend"],
            f"If you leave this blank, I will suggest {suggested_stack['backend']} because it matches the current starter templates and keeps backend setup straightforward.",
            ["FastAPI", "Flask", "Express", "NestJS", "Spring Boot"],
        )

    if not match_keyword("frontend", lowered) and project_kind["hasFrontend"]:
        add_question(
            "frontend_framework",
            "Which frontend framework should the starter use?",
            "choice",
            suggested_stack["frontend"],
            f"If you leave this blank, I will suggest {suggested_stack['frontend']} because it gives the cleanest starter structure for the current UI needs.",
            ["React", "Next.js", "Vue", "HTML/CSS/JavaScript", "None"],
        )

    if not match_keyword("language", lowered) and not match_keyword("backend", lowered):
        add_question(
            "language",
            "Do you want to lock in a preferred programming language?",
            "choice",
            suggested_stack["language"],
            f"If you leave this blank, I will suggest {suggested_stack['language']} because it fits the recommended stack and keeps the starter consistent.",
            ["Python", "JavaScript", "TypeScript", "Java"],
        )

    if project_kind["hasBackend"] and not match_keyword("database", lowered):
        add_question(
            "database",
            "Which database should the starter prepare for?",
            "choice",
            suggested_stack["database"],
            f"If you leave this blank, I will suggest {suggested_stack['database']} because it gives the best balance of simple setup and starter reliability for this project.",
            ["SQLite", "PostgreSQL", "MySQL", "MongoDB", "None"],
        )

    if project_kind["hasBackend"] and not _context_mentions_any(lowered, ("auth", "authentication", "login", "signup", "jwt")):
        add_question(
            "authentication",
            "Do you need authentication in the starter?",
            "boolean",
            "No",
            "If you leave this blank, I will suggest No so the starter stays simpler unless your app clearly needs protected user flows.",
            ["Yes", "No"],
        )

    if project_kind["hasBackend"] and not _context_mentions_any(lowered, ("role", "roles", "permissions", "admin", "staff", "manager")):
        add_question(
            "user_roles",
            "Do you need multiple user roles?",
            "choice",
            "Single user / no roles",
            "If you leave this blank, I will suggest a single-user or no-roles setup so the starter stays easy to run before you add permissions logic.",
            ["Single user / no roles", "Basic roles (admin + user)", "Custom roles needed"],
        )

    if project_kind["hasFrontend"] and not _context_mentions_any(lowered, ("admin dashboard", "admin panel", "back office")):
        add_question(
            "admin_dashboard",
            "Should the starter include an admin dashboard path?",
            "boolean",
            "No",
            "If you leave this blank, I will suggest No so the starter focuses on the main product flow before adding admin-specific pages.",
            ["Yes", "No"],
        )

    if project_kind["hasBackend"] and not _context_mentions_any(lowered, ("email", "smtp", "mail", "newsletter", "verification email", "contact form")):
        add_question(
            "email_smtp",
            "Will the project need email or SMTP support?",
            "boolean",
            "No",
            "If you leave this blank, I will suggest No so the starter avoids extra SMTP setup unless email is part of the core workflow.",
            ["Yes", "No"],
        )

    if project_kind["hasBackend"] and not _context_mentions_any(lowered, ("payment", "payments", "stripe", "checkout", "subscription", "billing")):
        add_question(
            "payment_system",
            "Will the project need payment processing?",
            "boolean",
            "No",
            "If you leave this blank, I will suggest No so the starter avoids payment keys and billing setup unless your app clearly needs them.",
            ["Yes", "No"],
        )

    if project_kind["hasBackend"] and not _context_mentions_any(lowered, ("api", "integration", "webhook", "third-party", "external service")):
        add_question(
            "external_apis",
            "Do you already know any external APIs or third-party services this project must connect to?",
            "text",
            "None",
            "If you leave this blank, I will assume no required external APIs so the starter stays self-contained and quicker to run locally.",
        )

    if (
        not match_keyword("aiTools", lowered)
        and _context_mentions_any(
            lowered,
            ("ai", "assistant", "agent", "chatbot", "llm", "openai", "ollama", "summar", "recommendation"),
        )
    ):
        add_question(
            "ai_integration",
            "Do you want AI integration in the starter?",
            "choice",
            "None",
            "If you leave this blank, I will suggest no AI integration unless the idea clearly needs model tooling and provider keys.",
            ["None", "Ollama", "OpenAI API", "LangChain"],
        )

    if not match_keyword("deployment", lowered):
        add_question(
            "deployment_target",
            "Where do you expect to deploy this project first?",
            "choice",
            suggested_stack["deployment"],
            f"If you leave this blank, I will suggest {suggested_stack['deployment']} because it matches the current deployment defaults and generated starter files.",
            ["Render", "Railway", "Vercel", "Docker", "None"],
        )

    if len(re.findall(r"[A-Za-z0-9]+", idea)) < 18:
        add_question(
            "complexity_level",
            "How ambitious should the first starter be?",
            "choice",
            "Standard",
            "If you leave this blank, I will suggest Standard so the starter includes useful structure without becoming heavy too early.",
            ["Simple", "Standard", "Advanced"],
        )

    return questions


def compute_agent_confidence(
    idea: str,
    detected_choices: list[str],
    questions: list[dict[str, Any]],
    project_kind: dict[str, Any],
) -> int:
    score = 35
    word_count = len(re.findall(r"[A-Za-z0-9]+", idea))
    if word_count >= 12:
        score += 15
    elif word_count >= 6:
        score += 8

    score += min(len(detected_choices) * 8, 32)
    if infer_declared_project_type(idea):
        score += 8
    if project_kind["isFullStack"]:
        score += 4
    score -= min(len(questions) * 3, 24)
    return max(20, min(95, score))


def normalize_agent_answers(answers: Mapping[str, Any] | None) -> dict[str, str]:
    if not isinstance(answers, Mapping):
        return {}
    normalized: dict[str, str] = {}
    for key, value in answers.items():
        question_id = str(key).strip()
        normalized[question_id] = normalize_agent_answer_value(question_id, value)
    return normalized


def apply_agent_answers_to_stack(
    idea: str,
    selected_stack: dict[str, str],
    answers: Mapping[str, str],
) -> dict[str, str]:
    resolved = normalize_stack_selection(selected_stack)
    scope = normalize_project_scope(
        answers.get("project_scope", infer_declared_project_type(idea) or determine_project_kind(resolved)["label"])
    )
    scope_value = scope.strip().lower()

    frontend_choice = supported_answer(answers.get("frontend_framework"), SUPPORTED_FRONTEND_VALUES)
    backend_choice = supported_answer(answers.get("backend_framework"), SUPPORTED_BACKEND_VALUES)
    language_choice = supported_answer(answers.get("language"), SUPPORTED_LANGUAGE_VALUES)
    database_choice = supported_answer(answers.get("database"), SUPPORTED_DATABASE_VALUES)
    deployment_choice = supported_answer(answers.get("deployment_target"), SUPPORTED_DEPLOYMENT_VALUES)
    ai_choice = supported_answer(answers.get("ai_integration"), SUPPORTED_AI_VALUES)

    if frontend_choice:
        resolved["frontend"] = frontend_choice
    if backend_choice:
        resolved["backend"] = backend_choice
    if language_choice:
        resolved["language"] = language_choice
    if database_choice:
        resolved["database"] = database_choice
    if deployment_choice:
        resolved["deployment"] = deployment_choice
    if ai_choice:
        resolved["aiTools"] = ai_choice

    if scope_value == "backend-only":
        resolved["frontend"] = "None"
        if resolved["backend"] in NONE_LIKE:
            resolved["backend"] = infer_backend(idea.lower())
    elif scope_value == "frontend-only":
        resolved["backend"] = "None"
        resolved["database"] = "None"
        if resolved["frontend"] in NONE_LIKE:
            resolved["frontend"] = infer_frontend(idea.lower(), "None")
    else:
        if resolved["frontend"] in NONE_LIKE:
            resolved["frontend"] = "React"
        if resolved["backend"] in NONE_LIKE:
            resolved["backend"] = "FastAPI"
        if resolved["database"] in {"Auto", ""}:
            resolved["database"] = infer_database(idea.lower(), resolved["backend"])

    if resolved["language"] in {"Auto", ""}:
        resolved["language"] = infer_language(idea.lower(), resolved["frontend"], resolved["backend"])
    return resolved


def build_final_requirements_summary(
    idea: str,
    answers: Mapping[str, str],
    selected_stack: dict[str, str],
    project_kind: dict[str, Any],
) -> str:
    lines = [
        f"Original idea: {idea.strip()}",
        f"Project scope: {project_kind['label']}",
        "Selected stack:",
        f"- Language: {selected_stack['language']}",
        f"- Frontend: {selected_stack['frontend']}",
        f"- Backend: {selected_stack['backend']}",
        f"- Database: {selected_stack['database']}",
        f"- AI / Tools: {selected_stack['aiTools']}",
        f"- Deployment: {selected_stack['deployment']}",
    ]

    details: list[str] = []
    if _is_yes_answer(answers.get("authentication")):
        details.append("Include authentication-ready structure and required secrets.")
    if _is_yes_answer(answers.get("admin_dashboard")):
        details.append("Include admin-oriented navigation or management surface in the starter.")
    if _is_yes_answer(answers.get("email_smtp")):
        details.append("Prepare SMTP/email configuration and service wiring.")
    if _is_yes_answer(answers.get("payment_system")):
        details.append("Prepare payment provider integration points and required keys.")
    if answers.get("user_roles") and answers.get("user_roles") != "Single user / no roles":
        details.append(f"Support user access model: {answers['user_roles']}.")
    external_apis = str(answers.get("external_apis") or "").strip()
    if external_apis.lower() not in {"", "none", "no"}:
        details.append(f"Prepare integration boundaries for: {external_apis}.")
    if answers.get("complexity_level"):
        details.append(f"Target complexity level: {answers['complexity_level']}.")
    if answers.get("ai_integration") and answers.get("ai_integration") not in {"", "None"}:
        details.append(f"Prepare AI integration around: {answers['ai_integration']}.")
    details.extend(build_unmapped_preference_notes(answers, selected_stack))

    if details:
        lines.append("Architectural requirements:")
        lines.extend(f"- {item}" for item in details)
    else:
        lines.append("Architectural requirements:")
        lines.append("- Use the suggested defaults for unspecified decisions and keep the starter runnable-first.")

    return "\n".join(lines).strip()


def build_agent_finalize_assumptions(
    answers: Mapping[str, str],
    selected_stack: dict[str, str],
    project_kind: dict[str, Any],
) -> list[str]:
    assumptions = [
        "Final requirements were synthesized from the original idea, your answers, and the selected stack.",
        "Suggested defaults were used only where you left a question blank, so generation can continue without extra back-and-forth.",
    ]
    if project_kind["isFullStack"]:
        assumptions.append("Frontend and backend will both be generated in separate folders.")
    if _is_yes_answer(answers.get("authentication")):
        assumptions.append("Authentication-related secrets and starter environment variables will be included where needed.")
    if selected_stack.get("deployment") == "Docker":
        assumptions.append("Docker-oriented deployment files will be included where the starter templates support them.")
    return dedupe_list(assumptions)


def _is_yes_answer(value: str | None) -> bool:
    return str(value or "").strip().lower() in YES_ANSWERS


def normalize_agent_answer_value(question_id: str, value: Any) -> str:
    text = coerce_text_value(value)
    if not text:
        return ""

    lowered = text.lower()
    if question_id in BOOLEAN_QUESTION_IDS:
        if lowered in YES_ANSWERS:
            return "Yes"
        if lowered in NO_ANSWERS:
            return "No"

    if question_id == "project_scope":
        return normalize_project_scope(text)

    alias_map = CANONICAL_ANSWER_ALIASES.get(question_id, {})
    if lowered in alias_map:
        return alias_map[lowered]

    if question_id == "user_roles":
        if "admin" in lowered and "user" in lowered:
            return "Basic roles (admin + user)"
        if "custom" in lowered or "manager" in lowered or "permission" in lowered:
            return "Custom roles needed"
        if "single" in lowered or "no role" in lowered:
            return "Single user / no roles"

    if question_id == "external_apis" and lowered in NO_ANSWERS:
        return "None"

    return text


def normalize_project_scope(value: Any) -> str:
    text = coerce_text_value(value)
    if not text:
        return ""
    lowered = text.lower()
    return CANONICAL_ANSWER_ALIASES["project_scope"].get(lowered, text)


def supported_answer(value: str | None, supported_values: set[str]) -> str:
    text = str(value or "").strip()
    return text if text in supported_values else ""


def build_unmapped_preference_notes(
    answers: Mapping[str, str],
    selected_stack: Mapping[str, str],
) -> list[str]:
    notes: list[str] = []
    mappings = [
        ("language", "Language", SUPPORTED_LANGUAGE_VALUES, "language"),
        ("frontend_framework", "Frontend framework", SUPPORTED_FRONTEND_VALUES, "frontend"),
        ("backend_framework", "Backend framework", SUPPORTED_BACKEND_VALUES, "backend"),
        ("database", "Database", SUPPORTED_DATABASE_VALUES, "database"),
        ("ai_integration", "AI integration", SUPPORTED_AI_VALUES, "aiTools"),
        ("deployment_target", "Deployment target", SUPPORTED_DEPLOYMENT_VALUES, "deployment"),
    ]

    for answer_key, label, supported_values, stack_key in mappings:
        raw_value = str(answers.get(answer_key, "")).strip()
        if not raw_value or raw_value in supported_values:
            continue
        notes.append(
            f"{label} preference noted: {raw_value}. The runnable starter keeps {selected_stack.get(stack_key, 'the suggested default')} as the safe template-backed default for now."
        )
    return notes


def preview_budget_seconds(generation_mode: str) -> float:
    return FAST_PLANNER_TIMEOUT_SECONDS if generation_mode == "fast" else DEEP_PREVIEW_TIMEOUT_SECONDS


def validate_planner_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("Planner response was not a JSON object.")

    missing_keys = sorted(REQUIRED_PLANNER_KEYS.difference(payload.keys()))
    if missing_keys:
        raise ValueError(f"Planner response was partial and missed required keys: {', '.join(missing_keys)}")

    if not isinstance(payload.get("selectedStack"), Mapping):
        raise ValueError("Planner response did not include a valid selectedStack object.")
    if not isinstance(payload.get("modules"), Sequence) or isinstance(payload.get("modules"), (str, bytes, bytearray)):
        raise ValueError("Planner response did not include a valid modules list.")
    if not isinstance(payload.get("packageRequirements"), Sequence) or isinstance(payload.get("packageRequirements"), (str, bytes, bytearray)):
        raise ValueError("Planner response did not include a valid packageRequirements list.")
    if not isinstance(payload.get("installCommands"), Sequence) or isinstance(payload.get("installCommands"), (str, bytes, bytearray)):
        raise ValueError("Planner response did not include a valid installCommands list.")
    if not isinstance(payload.get("runCommands"), Sequence) or isinstance(payload.get("runCommands"), (str, bytes, bytearray)):
        raise ValueError("Planner response did not include a valid runCommands list.")
    if not isinstance(payload.get("requiredInputs"), Sequence) or isinstance(payload.get("requiredInputs"), (str, bytes, bytearray)):
        raise ValueError("Planner response did not include a valid requiredInputs list.")
    if not isinstance(payload.get("envVariables"), Sequence) or isinstance(payload.get("envVariables"), (str, bytes, bytearray)):
        raise ValueError("Planner response did not include a valid envVariables list.")
    if not isinstance(payload.get("customFiles"), Sequence) or isinstance(payload.get("customFiles"), (str, bytes, bytearray)):
        raise ValueError("Planner response did not include a valid customFiles list.")

    normalized_payload = dict(payload)
    normalized_payload["customFiles"] = list(payload.get("customFiles", []))[:MAX_CUSTOM_FILES]
    return normalized_payload


def build_template_preview_metadata(
    template_family: str,
    project_name: str,
    generation_mode: str,
) -> dict[str, Any]:
    if template_family != "puzzle-game":
        return {}

    mode_label = "Fast Mode" if generation_mode == "fast" else "Deep Mode"
    return {
        "summary": (
            f"{project_name} is a fully playable sliding puzzle starter built with plain HTML, CSS, and JavaScript. "
            f"{mode_label} keeps the project dependency-free so it can run immediately by opening index.html or using the provided run scripts."
        ),
        "architecture": [
            "A single static frontend delivers the puzzle board, buttons, instructions, and win state without a backend dependency.",
            "Vanilla JavaScript owns tile shuffling, move validation, move counting, reset behavior, and win detection in one self-contained script.",
            "Run scripts open the project directly or serve it locally without any package installation.",
        ],
        "modules": [
            {
                "name": "Puzzle Interface",
                "purpose": "Renders the puzzle board, action buttons, and instructions in a single static page.",
                "keyFiles": ["index.html", "style.css"],
            },
            {
                "name": "Game Logic",
                "purpose": "Handles shuffle/start, movement rules, move counting, reset behavior, and win detection.",
                "keyFiles": ["script.js"],
            },
        ],
        "packageRequirements": [],
        "installCommands": ["setup.bat", "./setup.sh"],
        "runCommands": ["run.bat", "./run.sh", "Open index.html directly in a browser"],
        "requiredInputs": [],
        "envVariables": [],
        "assumptions": [
            "Single-sentence auto mode detected a puzzle game and selected the dependency-free static template.",
            "No backend, database, or package installation is required for the first runnable version.",
        ],
    }


def normalize_preview(
    raw_preview: Mapping[str, Any] | None,
    idea: str,
    requested_stack: dict[str, str] | None = None,
    generation_mode: str = "fast",
    requirements_context: str | None = None,
) -> dict[str, Any]:
    raw = dict(raw_preview or {})
    mode = normalize_generation_mode(generation_mode)
    requested = normalize_stack_selection(requested_stack)
    planning_context = requirements_context or idea
    template_family = str(raw.get("templateFamily") or "").strip()
    template_metadata = build_template_preview_metadata(
        template_family,
        clean_project_name(raw.get("projectName"), idea),
        mode,
    )
    detected_choices = dedupe_list(
        normalize_string_list(raw.get("detectedUserChoices")) or detect_user_choices(idea)
    )
    final_architecture = raw.get("finalArchitecture") if isinstance(raw.get("finalArchitecture"), Mapping) else {}
    selected_stack = resolve_selected_stack(
        idea=idea,
        requested_stack=requested,
        model_stack=raw.get("selectedStack"),
        detected_choices=detected_choices,
    )
    if final_architecture:
        selected_stack = normalize_stack_selection(
            {
                "language": final_architecture.get("language"),
                "frontend": final_architecture.get("frontend"),
                "backend": final_architecture.get("backend"),
                "database": final_architecture.get("database"),
                "aiTools": final_architecture.get("ai_tools") or final_architecture.get("aiTools"),
                "deployment": final_architecture.get("deployment"),
            }
        )
    project_kind = determine_project_kind(selected_stack, raw.get("projectType"))
    project_name = clean_project_name(raw.get("projectName"), idea)

    if template_family == "puzzle-game":
        modules = normalize_modules(raw.get("modules")) or template_metadata.get("modules", [])
        required_inputs = normalize_required_inputs(raw.get("requiredInputs")) or template_metadata.get("requiredInputs", [])
        env_variables = normalize_env_variables(raw.get("envVariables")) or template_metadata.get("envVariables", [])
        package_requirements = dedupe_list(
            normalize_string_list(raw.get("packageRequirements"))
            or list(template_metadata.get("packageRequirements", []))
        )
        install_commands = dedupe_list(
            normalize_string_list(raw.get("installCommands"))
            or list(template_metadata.get("installCommands", []))
        )
        run_commands = dedupe_list(
            normalize_string_list(raw.get("runCommands"))
            or list(template_metadata.get("runCommands", []))
        )
    else:
        modules = merge_modules(
            normalize_modules(raw.get("modules")),
            build_default_modules(selected_stack, project_kind),
        )
        required_inputs = merge_required_inputs(
            normalize_required_inputs(raw.get("requiredInputs")),
            build_required_inputs(planning_context, selected_stack, project_kind, modules),
        )
        env_variables = merge_env_variables(
            normalize_env_variables(raw.get("envVariables")),
            required_inputs_to_env_variables(required_inputs),
        )
        if final_architecture:
            package_requirements = normalize_string_list(final_architecture.get("package_requirements"))
            install_commands = normalize_string_list(final_architecture.get("install_commands"))
            run_commands = normalize_string_list(final_architecture.get("run_commands"))
        else:
            package_requirements = dedupe_list(
                normalize_string_list(raw.get("packageRequirements"))
                + build_package_requirements(selected_stack, project_kind)
            )
            install_commands = dedupe_list(
                normalize_string_list(raw.get("installCommands"))
                + build_install_commands(selected_stack, project_kind)
            )
            run_commands = dedupe_list(
                normalize_string_list(raw.get("runCommands"))
                + build_run_commands(selected_stack, project_kind)
            )

    removed_paths = normalize_removed_paths(raw.get("filesToRemove"))
    protected_paths = _required_preview_paths(selected_stack, project_kind, template_family)
    removable_paths = {path for path in removed_paths if path not in protected_paths}
    custom_manifest = [
        item for item in normalize_custom_manifest(raw.get("customFiles"), selected_stack, project_kind)
        if item.get("path") not in removable_paths
    ]
    validated_files = finalize_preview_files(
        project_name=project_name,
        selected_stack=selected_stack,
        project_kind=project_kind,
        required_inputs=required_inputs,
        template_family=template_family,
        custom_manifest=custom_manifest,
        raw_files=[
            item for item in normalize_files(raw.get("files"))
            if item.get("path") not in removable_paths
        ],
    )
    validated_files = [item for item in validated_files if item.get("path") not in removable_paths]

    summary = (
        str(raw.get("summary") or "").strip()
        or str(template_metadata.get("summary") or "").strip()
        or build_summary(project_name, project_kind, selected_stack, mode)
    )
    problem_statement = (
        str(raw.get("problemStatement") or "").strip()
        or idea.strip()
        or f"Build a starter project for {project_name}."
    )
    assumption_defaults = [] if template_family == "puzzle-game" else build_assumptions(
        selected_stack,
        project_kind,
        requested,
        mode,
        bool(custom_manifest),
    )
    architecture_defaults = [] if template_family == "puzzle-game" else build_architecture(
        selected_stack,
        project_kind,
    )
    assumptions = dedupe_list(
        normalize_string_list(raw.get("assumptions"))
        + normalize_string_list(template_metadata.get("assumptions"))
        + assumption_defaults
    )
    architecture = dedupe_list(
        normalize_string_list(raw.get("architecture"))
        + normalize_string_list(template_metadata.get("architecture"))
        + architecture_defaults
    )
    chosen_stack = build_chosen_stack(selected_stack)
    main_file = str(raw.get("mainFile") or main_file_for_stack(selected_stack)).strip()
    primary_run = str(raw.get("primaryRunCommand") or primary_run_command(selected_stack, run_commands)).strip()
    main_run_target = str(raw.get("mainRunTarget") or main_run_target_for_stack(selected_stack)).strip()
    local_url = str(raw.get("localUrl") or local_url_for_stack(selected_stack)).strip()
    setup_instructions = normalize_string_list(raw.get("setupInstructions")) or install_commands or ["setup.bat", "./setup.sh"]
    run_instructions = normalize_string_list(raw.get("runInstructions")) or [
        main_run_target,
        primary_run,
        "run.bat",
        "./run.sh",
    ]

    preview_payload = {
        "projectName": project_name,
        "projectType": str(raw.get("projectType") or project_kind.get("label", "")),
        "detectedUserChoices": detected_choices,
        "selectedStack": selected_stack,
        "chosenStack": chosen_stack,
        "assumptions": assumptions,
        "summary": summary,
        "problemStatement": problem_statement,
        "architecture": architecture,
        "modules": modules,
        "packageRequirements": package_requirements,
        "installCommands": install_commands,
        "runCommands": run_commands,
        "setupInstructions": setup_instructions,
        "runInstructions": dedupe_list(run_instructions),
        "requiredInputs": required_inputs,
        "envVariables": env_variables,
        "mainFile": main_file,
        "primaryRunCommand": primary_run,
        "mainRunTarget": main_run_target,
        "localUrl": local_url,
        "customFiles": custom_manifest,
        "requestedFiles": custom_manifest,
        "filesToRemove": [{"path": path} for path in removed_paths],
        "chatPendingCorrections": list(raw.get("chatPendingCorrections") or []),
        "files": validated_files,
    }
    for passthrough_key in (
        "recommendedIde",
        "alternativeIde",
        "runtimeTools",
        "packageManager",
        "migrationSummary",
        "stackAnalysis",
        "finalArchitecture",
        "generatedVersion",
        "stackSelectionSource",
        "isUserConfirmedStack",
    ):
        if passthrough_key in raw:
            preview_payload[passthrough_key] = raw.get(passthrough_key)
    complete_files, _ = assemble_complete_preview_files(
        preview_payload,
        selected_stack=selected_stack,
        project_kind=project_kind,
    )
    preview_payload["files"] = [item for item in complete_files if item.get("path") not in removable_paths]
    if template_family:
        preview_payload["templateFamily"] = template_family
    preview_payload["fileTree"] = build_preview_file_tree(
        preview_payload["files"],
        include_env_example=bool(env_variables),
    )
    return preview_payload


def apply_custom_file_overrides(
    preview: dict[str, Any], custom_files: list[dict[str, str]]
) -> dict[str, Any]:
    merged_files = merge_file_entries(preview.get("files", []), custom_files)
    selected_stack = normalize_stack_selection(preview.get("selectedStack"))
    project_kind = determine_project_kind(selected_stack)
    validated_files = finalize_preview_files(
        project_name=str(preview.get("projectName") or "Generated Project"),
        selected_stack=selected_stack,
        project_kind=project_kind,
        required_inputs=normalize_required_inputs(preview.get("requiredInputs")),
        raw_files=merged_files,
    )
    complete_files, _ = assemble_complete_preview_files(
        {**preview, "files": validated_files},
        selected_stack=selected_stack,
        project_kind=project_kind,
    )
    env_variables = normalize_env_variables(preview.get("envVariables"))

    preview["files"] = complete_files
    preview["fileTree"] = build_preview_file_tree(
        complete_files,
        include_env_example=bool(env_variables),
    )
    return preview


def required_preview_paths(
    selected_stack: dict[str, str],
    project_kind: dict[str, Any],
    template_family: str = "",
) -> set[str]:
    return _required_preview_paths(selected_stack, project_kind, template_family)


def normalize_generation_mode(value: Any) -> str:
    return "deep" if str(value or "").strip().lower() == "deep" else "fast"


def remaining_time(deadline: float) -> float:
    return max(0.0, deadline - time.monotonic())


def normalize_stack_selection(selection: Any) -> dict[str, str]:
    data = selection if isinstance(selection, Mapping) else {}
    normalized: dict[str, str] = {}
    for field in STACK_FIELDS:
        value = coerce_text_value(data.get(field)) or STACK_DEFAULTS[field]
        normalized[field] = value or STACK_DEFAULTS[field]
    return normalized


def resolve_selected_stack(
    idea: str,
    requested_stack: dict[str, str],
    model_stack: Any,
    detected_choices: list[str],
) -> dict[str, str]:
    model_selection = normalize_stack_selection(model_stack)
    resolved = normalize_stack_selection(requested_stack)
    lowered_idea = idea.lower()
    category = detect_project_category(idea)

    backend = pick_stack_value(
        requested_stack.get("backend"),
        model_selection.get("backend"),
        infer_backend(lowered_idea),
    )
    frontend = pick_stack_value(
        requested_stack.get("frontend"),
        model_selection.get("frontend"),
        infer_frontend(lowered_idea, backend),
    )
    language = pick_stack_value(
        requested_stack.get("language"),
        model_selection.get("language"),
        infer_language(lowered_idea, frontend, backend),
    )
    database = pick_stack_value(
        requested_stack.get("database"),
        model_selection.get("database"),
        infer_database(lowered_idea, backend),
    )
    ai_tools = pick_stack_value(
        requested_stack.get("aiTools"),
        model_selection.get("aiTools"),
        infer_ai_tools(lowered_idea),
    )
    deployment = pick_stack_value(
        requested_stack.get("deployment"),
        model_selection.get("deployment"),
        infer_deployment(lowered_idea),
    )

    resolved.update(
        {
            "language": language,
            "frontend": frontend,
            "backend": backend,
            "database": database,
            "aiTools": ai_tools,
            "deployment": deployment,
        }
    )

    category_defaults = category_stack_defaults(category)
    if category_defaults:
        for field in STACK_FIELDS:
            requested_value = str(requested_stack.get(field, "") or "").strip()
            model_value = str(model_selection.get(field, "") or "").strip()
            explicit_keyword = match_keyword(field, lowered_idea)
            if requested_value in {"", "Auto"} and model_value in {"", "Auto"} and not explicit_keyword:
                resolved[field] = category_defaults.get(field, resolved[field])

    if not detected_choices and all(value == "Auto" for value in requested_stack.values()):
        resolved["backend"] = resolved["backend"] if resolved["backend"] != "Auto" else category_defaults.get("backend", "FastAPI")
        resolved["frontend"] = resolved["frontend"] if resolved["frontend"] != "Auto" else category_defaults.get("frontend", "React")
        resolved["language"] = resolved["language"] if resolved["language"] != "Auto" else category_defaults.get("language", "Python")
        resolved["database"] = resolved["database"] if resolved["database"] != "Auto" else category_defaults.get("database", "SQLite")
        resolved["aiTools"] = resolved["aiTools"] if resolved["aiTools"] != "Auto" else category_defaults.get("aiTools", "None")
        resolved["deployment"] = resolved["deployment"] if resolved["deployment"] != "Auto" else category_defaults.get("deployment", "Render")

    return resolved


def pick_stack_value(requested: str | None, suggested: str | None, inferred: str) -> str:
    for candidate in (requested, suggested):
        if candidate is not None and str(candidate).strip() not in {"", "Auto"}:
            return str(candidate).strip()
    return inferred


def infer_language(idea: str, frontend: str, backend: str) -> str:
    detected = match_keyword("language", idea)
    if detected:
        return detected
    if backend in {"FastAPI", "Flask"}:
        return "Python"
    if backend == "Express":
        return "JavaScript"
    if backend == "NestJS":
        return "TypeScript"
    if backend == "Spring Boot":
        return "Java"
    if frontend in {"React", "Next.js", "Vue", "HTML/CSS/JavaScript"}:
        return "JavaScript"
    return "Python"


def infer_frontend(idea: str, backend: str) -> str:
    detected = match_keyword("frontend", idea)
    if detected:
        return detected
    if any(token in idea for token in ("api only", "backend only", "worker", "cli", "automation")):
        return "None"
    if any(token in idea for token in ("dashboard", "web app", "portal", "browser", "frontend", "website")):
        return "React"
    if backend in {"FastAPI", "Express", "NestJS", "Spring Boot"}:
        return "React"
    return "None"


def infer_backend(idea: str) -> str:
    detected = match_keyword("backend", idea)
    if detected:
        return detected
    if any(token in idea for token in ("frontend only", "static site", "landing page only")):
        return "None"
    if "spring" in idea or "java" in idea:
        return "Spring Boot"
    if "node" in idea or "express" in idea:
        return "Express"
    return "FastAPI"


def infer_database(idea: str, backend: str) -> str:
    detected = match_keyword("database", idea)
    if detected:
        return detected
    if any(token in idea for token in ("no database", "without database", "in memory")):
        return "None"
    if backend in {"FastAPI", "Flask"}:
        return "SQLite"
    if backend in {"Express", "NestJS", "Spring Boot"}:
        return "PostgreSQL"
    return "None"


def infer_ai_tools(idea: str) -> str:
    detected = match_keyword("aiTools", idea)
    if detected:
        return detected
    if any(token in idea for token in ("ai", "assistant", "agent", "generator", "chatbot", "llm")):
        return "Ollama"
    return "None"


def infer_deployment(idea: str) -> str:
    detected = match_keyword("deployment", idea)
    return detected or "Render"


def match_keyword(category: str, idea: str) -> str:
    for value, keywords in KEYWORD_MAP[category].items():
        if any(keyword in idea for keyword in keywords):
            return value
    return ""


def detect_user_choices(idea: str) -> list[str]:
    lowered = idea.lower()
    detected: list[str] = []
    labels = {
        "language": "Language",
        "frontend": "Frontend",
        "backend": "Backend",
        "database": "Database",
        "aiTools": "AI / Tools",
        "deployment": "Deployment",
    }
    for category, mapping in KEYWORD_MAP.items():
        for value, keywords in mapping.items():
            if any(keyword in lowered for keyword in keywords):
                detected.append(f"{labels[category]}: {value}")
                break
    return dedupe_list(detected)


def determine_project_kind(
    selected_stack: dict[str, str],
    declared_type: Any = None,
) -> dict[str, Any]:
    selected_stack = normalize_stack_selection(selected_stack)
    declared = str(declared_type or "").strip().lower()
    frontend = selected_stack.get("frontend", "None")
    backend = selected_stack.get("backend", "None")
    has_frontend = frontend not in NONE_LIKE
    has_backend = backend not in NONE_LIKE

    if declared == "frontend-only":
        has_backend = False
    elif declared == "backend-only":
        has_frontend = False
    elif declared == "full-stack":
        has_frontend = True
        has_backend = True

    is_full_stack = has_frontend and has_backend
    if is_full_stack:
        label = "full-stack"
        minimum_files = 15
    elif has_backend:
        label = "backend-only"
        minimum_files = 8
    else:
        label = "frontend-only"
        minimum_files = 6

    return {
        "hasFrontend": has_frontend,
        "hasBackend": has_backend,
        "isFullStack": is_full_stack,
        "label": label,
        "minimumFiles": minimum_files,
    }


def clean_project_name(raw_name: Any, idea: str) -> str:
    if isinstance(raw_name, str) and raw_name.strip():
        return raw_name.strip()[:80]

    words = re.findall(r"[A-Za-z0-9]+", idea)
    if not words:
        return "Project Agent Output"
    return " ".join(word.capitalize() for word in words[:4])


def build_summary(
    project_name: str,
    project_kind: dict[str, Any],
    selected_stack: dict[str, str],
    generation_mode: str,
) -> str:
    stack_bits = []
    if project_kind["hasFrontend"]:
        stack_bits.append(selected_stack["frontend"])
    if project_kind["hasBackend"]:
        stack_bits.append(selected_stack["backend"])
    stack_summary = " + ".join(bit for bit in stack_bits if bit not in NONE_LIKE) or selected_stack["language"]
    mode_label = "Fast Mode" if generation_mode == "fast" else "Deep Mode"
    return (
        f"{project_name} is a 100% runnable starter project built around {stack_summary}. "
        f"{mode_label} uses backend templates for all standard project structure so output quality stays complete while generation remains fast."
    )


def build_assumptions(
    selected_stack: dict[str, str],
    project_kind: dict[str, Any],
    requested_stack: dict[str, str],
    generation_mode: str,
    has_custom_manifest: bool,
) -> list[str]:
    assumptions: list[str] = []
    if all(value == "Auto" for value in requested_stack.values()):
        assumptions.append(
            "Some stack choices were inferred automatically to provide a complete beginner-friendly starter."
        )
    if generation_mode == "fast":
        assumptions.append(
            "Fast Mode used backend templates for standard files so project completeness was preserved without waiting for the model to write boilerplate."
        )
    else:
        assumptions.append(
            "Deep Mode keeps the same complete standard structure as Fast Mode and uses extra model time only for project-specific custom files."
        )
    if project_kind["isFullStack"]:
        assumptions.append("The project is split into frontend and backend folders to keep the full-stack boundary explicit.")
    assumptions.append(
        "This output is a 100% runnable starter project after `.env` is filled, setup is run, and the run script is started. Business logic can still be customized afterward."
    )
    if selected_stack.get("database") == "SQLite":
        assumptions.append("SQLite was chosen as a lightweight local-first database default.")
    if has_custom_manifest:
        assumptions.append("Project-specific custom files were layered on top of the standard stack templates.")
    return assumptions


def build_architecture(
    selected_stack: dict[str, str],
    project_kind: dict[str, Any],
) -> list[str]:
    architecture: list[str] = []
    if project_kind["hasFrontend"]:
        architecture.append(
            f"{selected_stack['frontend']} handles the user-facing workflows, starter pages, and client-side integration points."
        )
    if project_kind["hasBackend"]:
        architecture.append(
            f"{selected_stack['backend']} provides the API surface, routing, services, and configuration layer."
        )
    if selected_stack.get("database") not in NONE_LIKE:
        architecture.append(
            f"{selected_stack['database']} is configured as the primary persistence layer through environment-driven settings."
        )
    if selected_stack.get("aiTools") not in NONE_LIKE:
        architecture.append(
            f"{selected_stack['aiTools']} integration is isolated behind service boundaries so model/provider settings can evolve independently."
        )
    architecture.append("Setup, run scripts, and dependency manifests are generated server-side for a consistent starter layout.")
    return architecture


def build_default_modules(
    selected_stack: dict[str, str],
    project_kind: dict[str, Any],
) -> list[dict[str, Any]]:
    modules: list[dict[str, Any]] = []
    if project_kind["hasFrontend"]:
        base = "frontend/" if project_kind["isFullStack"] else ""
        modules.append(
            {
                "name": "Frontend Experience",
                "purpose": "Provides the main user interface, starter pages, and client-side state or API hooks.",
                "keyFiles": [
                    f"{base}src/App.jsx" if selected_stack["frontend"] in {"React", "Next.js", "Vue"} else f"{base}index.html",
                    f"{base}src/pages/HomePage.jsx" if selected_stack["frontend"] in {"React", "Next.js", "Vue"} else f"{base}src/views/home.js",
                    f"{base}src/services/api.js",
                ],
            }
        )
    if project_kind["hasBackend"]:
        base = "backend/" if project_kind["isFullStack"] else ""
        if selected_stack["backend"] in {"FastAPI", "Flask"}:
            key_files = [f"{base}app/main.py", f"{base}app/routers/items.py", f"{base}app/services/item_service.py"]
        elif selected_stack["backend"] in {"Express", "NestJS"}:
            key_files = [f"{base}server.js", f"{base}src/routes/items.js", f"{base}src/services/itemService.js"]
        else:
            key_files = [f"{base}pom.xml", f"{base}src/main/java/com/example/demo/service/AppService.java"]
        modules.append(
            {
                "name": "Backend API",
                "purpose": "Provides the routes, services, and integration-ready backend surface.",
                "keyFiles": key_files,
            }
        )
    if selected_stack.get("database") not in NONE_LIKE:
        base = "backend/" if project_kind["isFullStack"] else ""
        modules.append(
            {
                "name": "Persistence Layer",
                "purpose": "Supplies data models, configuration, and starter persistence wiring.",
                "keyFiles": [
                    f"{base}app/database.py" if selected_stack["backend"] in {"FastAPI", "Flask"} else f"{base}src/models/itemModel.js"
                ],
            }
        )
    return modules


def build_package_requirements(
    selected_stack: dict[str, str],
    project_kind: dict[str, Any],
) -> list[str]:
    packages: list[str] = []
    if project_kind["hasBackend"]:
        backend = selected_stack["backend"]
        database = selected_stack["database"]
        if backend == "FastAPI":
            packages.extend(
                ["fastapi", "uvicorn[standard]", "pydantic", "pydantic-settings", "sqlalchemy", "python-dotenv"]
            )
            if database == "SQLite":
                packages.append("aiosqlite")
            elif database == "PostgreSQL":
                packages.append("psycopg[binary]")
        elif backend == "Flask":
            packages.extend(["flask", "python-dotenv", "sqlalchemy"])
        elif backend in {"Express", "NestJS"}:
            packages.extend(["express", "cors", "dotenv"])
            if database == "PostgreSQL":
                packages.append("pg")
            elif database == "MongoDB":
                packages.append("mongoose")
        elif backend == "Spring Boot":
            packages.extend(
                [
                    "org.springframework.boot:spring-boot-starter-web",
                    "org.springframework.boot:spring-boot-starter-data-jpa",
                ]
            )
    if project_kind["hasFrontend"]:
        frontend = selected_stack["frontend"]
        if frontend in {"React", "Next.js", "Vue"}:
            packages.extend(["react", "react-dom", "vite"])
        elif frontend == "HTML/CSS/JavaScript":
            packages.append("vite")
    ai_tools = selected_stack.get("aiTools", "None")
    if ai_tools == "Ollama":
        packages.append("ollama")
    elif ai_tools == "LangChain":
        packages.append("langchain")
    return dedupe_list(packages)


def build_install_commands(
    selected_stack: dict[str, str],
    project_kind: dict[str, Any],
) -> list[str]:
    if project_kind["isFullStack"]:
        return ["setup.bat", "./setup.sh"]
    if project_kind["hasBackend"] and selected_stack["backend"] == "Spring Boot":
        return ["setup.bat", "./setup.sh", "mvn install"]
    if project_kind["hasFrontend"] and not project_kind["hasBackend"]:
        return ["setup.bat", "./setup.sh", "npm install"]
    return ["setup.bat", "./setup.sh"]


def build_run_commands(
    selected_stack: dict[str, str],
    project_kind: dict[str, Any],
) -> list[str]:
    commands = ["run.bat", "./run.sh"]
    if project_kind["isFullStack"]:
        return commands
    if project_kind["hasBackend"]:
        backend = selected_stack["backend"]
        if backend in {"FastAPI", "Flask"}:
            commands.append("python -m uvicorn app.main:app --reload")
        elif backend in {"Express", "NestJS"}:
            commands.append("npm start")
        elif backend == "Spring Boot":
            commands.append("mvn spring-boot:run")
    elif project_kind["hasFrontend"]:
        commands.append("npm run dev")
    return commands


def build_required_inputs(
    idea: str,
    selected_stack: dict[str, str],
    project_kind: dict[str, Any],
    modules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    context_parts = [idea]
    for module in modules:
        context_parts.append(str(module.get("name") or ""))
        context_parts.append(str(module.get("purpose") or ""))
        context_parts.extend(normalize_string_list(module.get("keyFiles")))
    lowered = " ".join(part.lower() for part in context_parts if part)

    required_inputs: list[dict[str, Any]] = []

    def add_runtime_input(
        name: str,
        *,
        required: bool,
        example: str,
        where: str = "Terminal prompt or .env",
        purpose: str,
    ) -> None:
        required_inputs.append(
            {
                "name": name,
                "required": required,
                "example": example,
                "whereToAdd": ".env",
                "whereToEnter": where,
                "purpose": purpose,
            }
        )

    if project_kind["hasBackend"]:
        add_runtime_input(
            "APP_ENV",
            required=False,
            example="development",
            where=".env",
            purpose="Application environment name.",
        )
        add_runtime_input(
            "PORT",
            required=False,
            example="8000",
            where=".env",
            purpose="Local port used when the backend starts from the generated run scripts.",
        )

    database = selected_stack.get("database")
    if database == "SQLite":
        add_runtime_input(
            "DATABASE_URL",
            required=True,
            example="sqlite:///./app.db",
            where="Terminal prompt or .env",
            purpose="SQLite connection string for local development.",
        )
    elif database in {"PostgreSQL", "MySQL"}:
        example = (
            "postgresql://postgres:postgres@localhost:5432/app_db"
            if database == "PostgreSQL"
            else "mysql://root:password@localhost:3306/app_db"
        )
        add_runtime_input(
            "DATABASE_URL",
            required=True,
            example=example,
            where="Terminal prompt or .env",
            purpose=f"{database} connection string for the backend database.",
        )
    elif database == "MongoDB":
        add_runtime_input(
            "MONGODB_URI",
            required=True,
            example="mongodb://localhost:27017/app_db",
            where="Terminal prompt or .env",
            purpose="MongoDB connection string for the backend database.",
        )

    if project_kind["hasBackend"] and _context_mentions_any(lowered, ("database", "login", "auth", "authentication", "admin", "inventory")):
        add_runtime_input(
            "DATABASE_URL",
            required=True,
            example="sqlite:///./app.db",
            where="Terminal prompt or .env",
            purpose="Database connection string for local data storage.",
        )

    if _context_mentions_any(lowered, ("auth", "authentication", "login", "signup", "jwt", "token", "session")):
        add_runtime_input(
            "JWT_SECRET",
            required=True,
            example="change-me-super-secret",
            where="Terminal prompt or .env",
            purpose="Secret used to sign authentication tokens.",
        )

    if _context_mentions_any(lowered, ("email", "smtp", "mail", "newsletter", "verification email", "contact form")):
        required_inputs.extend(
            [
                {
                    "name": "SMTP_HOST",
                    "required": True,
                    "example": "smtp.gmail.com",
                    "whereToAdd": ".env",
                    "whereToEnter": "Terminal prompt or .env",
                    "purpose": "SMTP email server host.",
                },
                {
                    "name": "SMTP_PORT",
                    "required": True,
                    "example": "587",
                    "whereToAdd": ".env",
                    "whereToEnter": "Terminal prompt or .env",
                    "purpose": "SMTP email server port.",
                },
                {
                    "name": "SMTP_EMAIL",
                    "required": True,
                    "example": "yourmail@gmail.com",
                    "whereToAdd": ".env",
                    "whereToEnter": "Terminal prompt or .env",
                    "purpose": "SMTP email address used for sending emails.",
                },
                {
                    "name": "SMTP_PASSWORD",
                    "required": True,
                    "example": "app-password",
                    "whereToAdd": ".env",
                    "whereToEnter": "Terminal prompt or .env",
                    "purpose": "SMTP account password or app password.",
                },
            ]
        )

    if _context_mentions_any(lowered, ("payment", "payments", "stripe", "checkout", "billing", "subscription")):
        add_runtime_input(
            "STRIPE_SECRET_KEY",
            required=True,
            example="sk_test_1234567890",
            where="Terminal prompt or .env",
            purpose="Secret key for payment provider API requests.",
        )
        add_runtime_input(
            "STRIPE_PUBLIC_KEY",
            required=True,
            example="pk_test_1234567890",
            where=".env",
            purpose="Public key used by the frontend checkout flow.",
        )
        add_runtime_input(
            "PAYMENT_WEBHOOK_SECRET",
            required=True,
            example="whsec_1234567890",
            where=".env",
            purpose="Verifies payment webhook events.",
        )

    ai_tools = selected_stack.get("aiTools")
    if ai_tools == "Ollama" or _context_mentions_any(lowered, ("ollama", "local llm", "qwen", "llama")):
        required_inputs.extend(
            [
                {
                    "name": "OLLAMA_BASE_URL",
                    "required": True,
                    "example": "http://localhost:11434",
                    "whereToAdd": ".env",
                    "whereToEnter": "Terminal prompt or .env",
                    "purpose": "Base URL for the local Ollama server.",
                },
                {
                    "name": "OLLAMA_MODEL",
                    "required": True,
                    "example": "qwen2.5-coder:latest",
                    "whereToAdd": ".env",
                    "whereToEnter": "Terminal prompt or .env",
                    "purpose": "Ollama model name to use for local inference.",
                },
            ]
        )
    if ai_tools == "OpenAI API" or _context_mentions_any(lowered, ("openai", "gpt-4", "gpt", "chatgpt", "chatbot", "ai assistant", "llm")):
        add_runtime_input(
            "OPENAI_API_KEY",
            required=True,
            example="sk-...",
            where="Terminal prompt or .env",
            purpose="Used for AI chatbot responses.",
        )

    if _context_mentions_any(lowered, ("oauth", "google login", "github login", "social login", "openid")):
        required_inputs.extend(
            [
                {
                    "name": "OAUTH_CLIENT_ID",
                    "required": True,
                    "example": "your-client-id",
                    "whereToAdd": ".env",
                    "whereToEnter": "Terminal prompt or .env",
                    "purpose": "OAuth client identifier for external sign-in.",
                },
                {
                    "name": "OAUTH_CLIENT_SECRET",
                    "required": True,
                    "example": "your-client-secret",
                    "whereToAdd": ".env",
                    "whereToEnter": "Terminal prompt or .env",
                    "purpose": "OAuth client secret for external sign-in.",
                },
            ]
        )

    if _context_mentions_any(lowered, ("file upload", "upload file", "cloud storage", "storage bucket", "s3", "gcs", "blob storage")):
        add_runtime_input(
            "STORAGE_BUCKET",
            required=True,
            example="project-agent-uploads",
            where="Terminal prompt or .env",
            purpose="Storage bucket used for uploaded files.",
        )

    if project_kind["isFullStack"]:
        required_inputs.append(
            {
                "name": "VITE_API_BASE_URL",
                "required": False,
                "example": "http://localhost:8000",
                "whereToAdd": ".env",
                "whereToEnter": ".env",
                "purpose": "Frontend base URL for backend API calls.",
            }
        )

    return dedupe_required_inputs(required_inputs)


def required_inputs_to_env_variables(
    required_inputs: list[dict[str, Any]],
) -> list[dict[str, str]]:
    env_vars: list[dict[str, str]] = []
    for item in required_inputs:
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        env_vars.append(
            {
                "name": name,
                "value": str(item.get("example") or "").strip(),
                "description": str(item.get("purpose") or "").strip(),
            }
        )
    return env_vars


def normalize_custom_manifest(
    value: Any,
    selected_stack: dict[str, str],
    project_kind: dict[str, Any],
) -> list[dict[str, str]]:
    manifest: list[dict[str, str]] = []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            if len(manifest) >= MAX_CUSTOM_FILES:
                break
            if isinstance(item, str):
                path = clean_relative_path(item)
                purpose = "Project-specific custom logic."
            elif isinstance(item, Mapping):
                path = clean_relative_path(item.get("path"))
                purpose = str(item.get("purpose") or item.get("description") or "Project-specific custom logic.").strip()
            else:
                continue
            if not path or is_standard_file_path(path):
                continue
            manifest.append({"path": path, "purpose": purpose})

    if manifest:
        return dedupe_manifest(manifest)

    defaults: list[dict[str, str]] = []
    if project_kind["isFullStack"]:
        if selected_stack["frontend"] not in NONE_LIKE:
            defaults.append(
                {
                    "path": "frontend/src/pages/DashboardPage.jsx",
                    "purpose": "Primary project-specific frontend page for the main user workflow.",
                }
            )
        if selected_stack["backend"] in {"FastAPI", "Flask"}:
            defaults.append(
                {
                    "path": "backend/app/services/domain_service.py",
                    "purpose": "Project-specific backend domain service with starter business rules.",
                }
            )
        elif selected_stack["backend"] in {"Express", "NestJS"}:
            defaults.append(
                {
                    "path": "backend/src/services/domainService.js",
                    "purpose": "Project-specific backend domain service with starter business rules.",
                }
            )
    elif project_kind["hasBackend"]:
        if selected_stack["backend"] in {"FastAPI", "Flask"}:
            defaults.append(
                {
                    "path": "app/services/domain_service.py",
                    "purpose": "Project-specific backend domain service with starter business rules.",
                }
            )
        elif selected_stack["backend"] in {"Express", "NestJS"}:
            defaults.append(
                {
                    "path": "src/services/domainService.js",
                    "purpose": "Project-specific backend domain service with starter business rules.",
                }
            )
        elif selected_stack["backend"] == "Spring Boot":
            defaults.append(
                {
                    "path": "src/main/java/com/example/demo/service/DomainService.java",
                    "purpose": "Project-specific backend service with starter business rules.",
                }
            )
    elif project_kind["hasFrontend"]:
        if selected_stack["frontend"] in {"React", "Next.js", "Vue"}:
            defaults.append(
                {
                    "path": "src/pages/DashboardPage.jsx",
                    "purpose": "Primary project-specific frontend page for the main workflow.",
                }
            )
        else:
            defaults.append(
                {
                    "path": "src/views/dashboard.js",
                    "purpose": "Primary project-specific frontend view for the main workflow.",
                }
            )
    return defaults[:MAX_CUSTOM_FILES]


def normalize_removed_paths(value: Any) -> list[str]:
    paths: list[str] = []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            if isinstance(item, Mapping):
                path = clean_relative_path(item.get("path"))
            else:
                path = clean_relative_path(item)
            if path:
                paths.append(path)
    return sorted(set(paths))


def build_standard_files(
    project_name: str,
    selected_stack: dict[str, str],
    project_kind: dict[str, Any],
) -> list[dict[str, str]]:
    files: dict[str, str] = {}
    if project_kind["isFullStack"]:
        if project_kind["hasFrontend"]:
            files.update(build_frontend_files(selected_stack["frontend"], project_name, "frontend"))
        if project_kind["hasBackend"]:
            files.update(build_backend_files(selected_stack, project_name, "backend"))
        files.update(build_root_scripts(selected_stack, project_kind))
    elif project_kind["hasBackend"]:
        files.update(build_backend_files(selected_stack, project_name, ""))
        files.update(build_root_scripts(selected_stack, project_kind))
    else:
        files.update(build_frontend_files(selected_stack["frontend"], project_name, ""))
        files.update(build_root_scripts(selected_stack, project_kind))
    return [{"path": path, "content": content} for path, content in files.items()]


def build_custom_template_files(
    manifest: list[dict[str, str]],
    project_name: str,
    selected_stack: dict[str, str],
    project_kind: dict[str, Any],
) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    for item in manifest[:MAX_CUSTOM_FILES]:
        path = item["path"]
        purpose = item["purpose"]
        content = build_custom_template_content(path, purpose, project_name, selected_stack, project_kind)
        files.append({"path": path, "content": trim_content_lines(content)})
    return files


def build_custom_template_content(
    path: str,
    purpose: str,
    project_name: str,
    _selected_stack: dict[str, str],
    _project_kind: dict[str, Any],
) -> str:
    stem = Path(path).stem
    pretty_name = stem.replace("_", " ").replace("-", " ").title()
    extension = Path(path).suffix.lower()

    if extension in {".jsx", ".tsx"}:
        if "page" in stem.lower() or "/pages/" in path:
            return f"""const cards = [
  {{
    title: "{pretty_name} Overview",
    detail: "{purpose}"
  }},
  {{
    title: "Starter Workflow",
    detail: "Use this page to connect forms, API requests, and user-facing business actions."
  }}
];

export default function {safe_component_name(stem)}() {{
  return (
    <section className="card">
      <h2>{pretty_name}</h2>
      <p>{purpose}</p>
      <ul>
        {{cards.map((card) => (
          <li key={{card.title}}>
            <strong>{{card.title}}</strong>: {{card.detail}}
          </li>
        ))}}
      </ul>
    </section>
  );
}}
"""
        return f"""export default function {safe_component_name(stem)}() {{
  return (
    <section className="card">
      <h3>{pretty_name}</h3>
      <p>{purpose}</p>
    </section>
  );
}}
"""

    if extension == ".py":
        if "router" in path or "/routers/" in path:
            return f"""from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def read_{safe_python_name(stem)}() -> dict[str, str]:
    return {{
        "message": "{purpose}",
        "project": "{project_name}",
    }}
"""
        if "schema" in path or "/schemas/" in path:
            return f"""from pydantic import BaseModel


class {safe_component_name(stem)}(BaseModel):
    name: str
    description: str = "{purpose}"
"""
        if "model" in path or "/models/" in path:
            return f"""from dataclasses import dataclass


@dataclass
class {safe_component_name(stem)}:
    name: str
    status: str = "ready"
"""
        return f"""def {safe_python_name(stem)}_summary() -> dict[str, str]:
    return {{
        "name": "{pretty_name}",
        "purpose": "{purpose}",
        "project": "{project_name}",
    }}
"""

    if extension in {".js", ".mjs"}:
        if "service" in path.lower():
            return f"""export function get{safe_component_name(stem)}Summary() {{
  return {{
    project: "{project_name}",
    purpose: "{purpose}"
  }};
}}
"""
        if "controller" in path.lower():
            return f"""export function {safe_js_name(stem)}(_req, res) {{
  res.json({{
    project: "{project_name}",
    purpose: "{purpose}"
  }});
}}
"""
        return f"""export const {safe_js_name(stem)} = {{
  project: "{project_name}",
  purpose: "{purpose}"
}};
"""

    if extension == ".java":
        class_name = safe_component_name(stem)
        return f"""package com.example.demo.service;

import org.springframework.stereotype.Service;

@Service
public class {class_name} {{
    public String summary() {{
        return "{purpose}";
    }}
}}
"""

    return f"# {pretty_name}\n\n{purpose}\n"


def ensure_minimum_project_files(
    files: list[dict[str, str]],
    selected_stack: dict[str, str],
    project_kind: dict[str, Any],
) -> list[dict[str, str]]:
    merged = {entry["path"]: entry["content"] for entry in files}
    for path, content in build_root_scripts(selected_stack, project_kind).items():
        merged.setdefault(path, content)

    if project_kind["isFullStack"]:
        for path, content in build_frontend_files(selected_stack["frontend"], "App", "frontend").items():
            merged.setdefault(path, content)
        for path, content in build_backend_files(selected_stack, "App", "backend").items():
            merged.setdefault(path, content)
    elif project_kind["hasBackend"]:
        for path, content in build_backend_files(selected_stack, "App", "").items():
            merged.setdefault(path, content)
    else:
        for path, content in build_frontend_files(selected_stack["frontend"], "App", "").items():
            merged.setdefault(path, content)

    filler_index = 1
    while len(merged) < project_kind["minimumFiles"]:
        filler_path = f"notes/starter-note-{filler_index}.md"
        merged.setdefault(
            filler_path,
            f"# Starter Note {filler_index}\n\nThis file preserves the complete minimum project structure while you continue iterating.\n",
        )
        filler_index += 1

    return [{"path": path, "content": content} for path, content in merged.items()]


def build_backend_files(
    selected_stack: dict[str, str],
    project_name: str,
    prefix: str,
) -> dict[str, str]:
    backend = selected_stack.get("backend", "FastAPI")
    if backend in {"FastAPI", "Flask"}:
        return build_fastapi_backend_files(project_name, prefix)
    if backend in {"Express", "NestJS"}:
        return build_express_backend_files(project_name, prefix)
    if backend == "Spring Boot":
        return build_spring_backend_files(project_name, prefix)
    return build_fastapi_backend_files(project_name, prefix)


def build_frontend_files(frontend: str, project_name: str, prefix: str) -> dict[str, str]:
    if frontend in {"React", "Next.js", "Vue"}:
        return build_react_frontend_files(project_name, prefix)
    return build_vanilla_frontend_files(project_name, prefix)


def build_fastapi_backend_files(project_name: str, prefix: str) -> dict[str, str]:
    app_prefix = prefixed(prefix, "app")
    return {
        prefixed(prefix, "requirements.txt"): "\n".join(
            [
                "fastapi",
                "uvicorn[standard]",
                "pydantic",
                "pydantic-settings",
                "sqlalchemy",
                "python-dotenv",
                "aiosqlite",
                "",
            ]
        ),
        prefixed(app_prefix, "__init__.py"): "",
        prefixed(app_prefix, "main.py"): f"""from fastapi import FastAPI

from app.routers import health, items


app = FastAPI(title="{project_name} API")
app.include_router(health.router)
app.include_router(items.router, prefix="/api/items", tags=["items"])


@app.get("/")
def read_root() -> dict[str, str]:
    return {{"message": "{project_name} backend is running."}}
""",
        prefixed(app_prefix, "routers/__init__.py"): "",
        prefixed(app_prefix, "routers/health.py"): """from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok")
""",
        prefixed(app_prefix, "routers/items.py"): """from fastapi import APIRouter

from app.schemas.item import Item
from app.services.item_service import list_items

router = APIRouter()


@router.get("/", response_model=list[Item])
def get_items() -> list[Item]:
    return list_items()
""",
        prefixed(app_prefix, "services/__init__.py"): "",
        prefixed(app_prefix, "services/app_service.py"): f"""def get_app_summary() -> str:
    return "{project_name} includes routes, services, schemas, and configuration for quick iteration."
""",
        prefixed(app_prefix, "services/item_service.py"): """from app.schemas.item import Item


def list_items() -> list[Item]:
    return [
        Item(id=1, name="Starter task", status="ready"),
        Item(id=2, name="Next iteration", status="planned"),
    ]
""",
        prefixed(app_prefix, "models/__init__.py"): "",
        prefixed(app_prefix, "models/base.py"): """from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
""",
        prefixed(app_prefix, "models/item.py"): """from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ItemModel(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40), default="ready")
""",
        prefixed(app_prefix, "schemas/__init__.py"): "",
        prefixed(app_prefix, "schemas/health.py"): """from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
""",
        prefixed(app_prefix, "schemas/item.py"): """from pydantic import BaseModel


class Item(BaseModel):
    id: int
    name: str
    status: str
""",
        prefixed(app_prefix, "database.py"): """from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
""",
        prefixed(app_prefix, "config.py"): """from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    app_env: str = "development"
    database_url: str = "sqlite:///./app.db"


settings = Settings()
""",
    }


def build_express_backend_files(project_name: str, prefix: str) -> dict[str, str]:
    return {
        prefixed(prefix, "package.json"): json.dumps(
            {
                "name": project_name.lower().replace(" ", "-"),
                "version": "0.1.0",
                "private": True,
                "type": "module",
                "scripts": {"dev": "node --watch server.js", "start": "node server.js"},
                "dependencies": {"cors": "^2.8.5", "dotenv": "^16.4.5", "express": "^4.19.2"},
            },
            indent=2,
        )
        + "\n",
        prefixed(prefix, "server.js"): f"""import cors from "cors";
import dotenv from "dotenv";
import express from "express";
import indexRouter from "./src/routes/index.js";
import itemsRouter from "./src/routes/items.js";

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());
app.use("/", indexRouter);
app.use("/api/items", itemsRouter);

const port = process.env.PORT || 8000;
app.listen(port, () => {{
  console.log("{project_name} API listening on port", port);
}});
""",
        prefixed(prefix, "src/routes/index.js"): """import { Router } from "express";
import { getStatus } from "../controllers/appController.js";

const router = Router();
router.get("/", getStatus);

export default router;
""",
        prefixed(prefix, "src/routes/items.js"): """import { Router } from "express";
import { listItems } from "../controllers/itemController.js";

const router = Router();
router.get("/", listItems);

export default router;
""",
        prefixed(prefix, "src/controllers/appController.js"): """export function getStatus(_req, res) {
  res.json({ status: "ok" });
}
""",
        prefixed(prefix, "src/controllers/itemController.js"): """import { getItems } from "../services/itemService.js";

export function listItems(_req, res) {
  res.json(getItems());
}
""",
        prefixed(prefix, "src/services/appService.js"): f"""export function getAppSummary() {{
  return "{project_name} includes routes, controllers, services, and starter configuration.";
}}
""",
        prefixed(prefix, "src/services/itemService.js"): """export function getItems() {
  return [
    { id: 1, name: "Starter task", status: "ready" },
    { id: 2, name: "Next iteration", status: "planned" }
  ];
}
""",
        prefixed(prefix, "src/models/itemModel.js"): """export const itemShape = {
  id: "number",
  name: "string",
  status: "string"
};
""",
    }


def build_react_frontend_files(project_name: str, prefix: str) -> dict[str, str]:
    return {
        prefixed(prefix, "package.json"): json.dumps(
            {
                "name": project_name.lower().replace(" ", "-") + "-frontend",
                "private": True,
                "version": "0.1.0",
                "type": "module",
                "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
                "dependencies": {"react": "^18.3.1", "react-dom": "^18.3.1"},
                "devDependencies": {"vite": "^5.4.0", "@vitejs/plugin-react": "^4.3.1"},
            },
            indent=2,
        )
        + "\n",
        prefixed(prefix, "index.html"): """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Project Starter</title>
    <script type="module" src="/src/main.jsx"></script>
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
""",
        prefixed(prefix, "vite.config.js"): """import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173
  }
});
""",
        prefixed(prefix, "src/main.jsx"): """import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
""",
        prefixed(prefix, "src/App.jsx"): f"""import AppShell from "./components/AppShell";
import HomePage from "./pages/HomePage";

export default function App() {{
  return (
    <AppShell title="{project_name}">
      <HomePage />
    </AppShell>
  );
}}
""",
        prefixed(prefix, "src/components/AppShell.jsx"): """export default function AppShell({ title, children }) {
  return (
    <div className="app-shell">
      <header className="hero">
        <p className="eyebrow">Generated by Project Agent</p>
        <h1>{title}</h1>
      </header>
      <main>{children}</main>
    </div>
  );
}
""",
        prefixed(prefix, "src/pages/HomePage.jsx"): """import { getProjectHealth } from "../services/api";

export default function HomePage() {
  const projectHealth = getProjectHealth();

  return (
    <section className="card">
      <h2>Starter Overview</h2>
      <p>This frontend is ready for your first feature slice.</p>
      <p>API health source: {projectHealth}</p>
    </section>
  );
}
""",
        prefixed(prefix, "src/services/api.js"): """export function getProjectHealth() {
  return import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
}
""",
        prefixed(prefix, "src/styles.css"): """:root {
  color-scheme: light;
  font-family: "Segoe UI", Arial, sans-serif;
  background: #f5f7fb;
  color: #132238;
}

body {
  margin: 0;
}

.app-shell {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 20px 56px;
}

.hero {
  margin-bottom: 24px;
}

.eyebrow {
  font-size: 0.75rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #57657d;
}

.card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 18px 40px rgba(19, 34, 56, 0.08);
}
""",
    }


def build_vanilla_frontend_files(project_name: str, prefix: str) -> dict[str, str]:
    return {
        prefixed(prefix, "package.json"): json.dumps(
            {
                "name": project_name.lower().replace(" ", "-") + "-frontend",
                "private": True,
                "version": "0.1.0",
                "type": "module",
                "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
                "devDependencies": {"vite": "^5.4.0"},
            },
            indent=2,
        )
        + "\n",
        prefixed(prefix, "index.html"): """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Project Starter</title>
    <script type="module" src="/src/main.js"></script>
  </head>
  <body>
    <div id="app"></div>
  </body>
</html>
""",
        prefixed(prefix, "vite.config.js"): """import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173
  }
});
""",
        prefixed(prefix, "src/main.js"): f"""import {{ renderHomePage }} from "./views/home.js";
import "./styles.css";

document.querySelector("#app").innerHTML = renderHomePage("{project_name}");
""",
        prefixed(prefix, "src/views/home.js"): """export function renderHomePage(title) {
  return `
    <main class="app-shell">
      <section class="card">
        <p class="eyebrow">Generated by Project Agent</p>
        <h1>${title}</h1>
        <p>This starter is ready for your first feature slice.</p>
      </section>
    </main>
  `;
}
""",
        prefixed(prefix, "src/services/api.js"): """export function getApiBaseUrl() {
  return import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
}
""",
        prefixed(prefix, "src/styles.css"): """body {
  margin: 0;
  font-family: "Segoe UI", Arial, sans-serif;
  background: #f5f7fb;
  color: #132238;
}

.app-shell {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 20px 56px;
}

.card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 18px 40px rgba(19, 34, 56, 0.08);
}

.eyebrow {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: #57657d;
}
""",
    }


def build_spring_backend_files(project_name: str, prefix: str) -> dict[str, str]:
    java_base = prefixed(prefix, "src/main/java/com/example/demo")
    resources_base = prefixed(prefix, "src/main/resources")
    return {
        prefixed(prefix, "pom.xml"): """<project xmlns="http://maven.apache.org/POM/4.0.0"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>demo</artifactId>
  <version>0.0.1-SNAPSHOT</version>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.2</version>
  </parent>
  <properties>
    <java.version>17</java.version>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>
""",
        prefixed(java_base, "Application.java"): """package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
""",
        prefixed(java_base, "controller/AppController.java"): """package com.example.demo.controller;

import com.example.demo.service.AppService;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class AppController {
    private final AppService appService;

    public AppController(AppService appService) {
        this.appService = appService;
    }

    @GetMapping("/")
    public Map<String, String> status() {
        return Map.of("message", appService.status());
    }
}
""",
        prefixed(java_base, "service/AppService.java"): f"""package com.example.demo.service;

import org.springframework.stereotype.Service;

@Service
public class AppService {{
    public String status() {{
        return "{project_name} backend is running.";
    }}
}}
""",
        prefixed(java_base, "model/AppModel.java"): """package com.example.demo.model;

public class AppModel {
    private Long id;
    private String name;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
}
""",
        prefixed(java_base, "repository/AppRepository.java"): """package com.example.demo.repository;

import com.example.demo.model.AppModel;
import java.util.List;
import org.springframework.stereotype.Repository;

@Repository
public class AppRepository {
    public List<AppModel> findAll() {
        return List.of();
    }
}
""",
        prefixed(resources_base, "application.properties"): """spring.application.name=demo
server.port=8080
""",
    }


def build_root_scripts(
    selected_stack: dict[str, str],
    project_kind: dict[str, Any],
) -> dict[str, str]:
    if project_kind["isFullStack"]:
        return build_fullstack_scripts(selected_stack)
    if project_kind["hasBackend"]:
        backend = selected_stack["backend"]
        if backend in {"FastAPI", "Flask"}:
            return build_python_scripts(".")
        if backend in {"Express", "NestJS"}:
            return build_node_scripts(".")
        if backend == "Spring Boot":
            return build_java_scripts(".")
    return build_node_scripts(".")


def build_fullstack_scripts(selected_stack: dict[str, str]) -> dict[str, str]:
    backend_setup = ""
    backend_run_windows = "echo No backend runtime configured.\n"
    backend_run_unix = 'echo "No backend runtime configured."\n'

    if selected_stack["backend"] in {"FastAPI", "Flask"}:
        backend_setup = (
            "if exist backend\\requirements.txt (\n"
            "  python -m pip install -r backend\\requirements.txt\n"
            ")\n"
        )
        backend_run_windows = (
            'start "Backend" cmd /k "cd backend && python -m uvicorn app.main:app --reload"\n'
        )
        backend_run_unix = (
            '(cd backend && python -m uvicorn app.main:app --reload) &\n'
        )
    elif selected_stack["backend"] in {"Express", "NestJS"}:
        backend_setup = 'if exist backend\\package.json (\n  pushd backend\n  call npm install\n  popd\n)\n'
        backend_run_windows = 'start "Backend" cmd /k "cd backend && npm run dev"\n'
        backend_run_unix = '(cd backend && npm run dev) &\n'
    elif selected_stack["backend"] == "Spring Boot":
        backend_setup = (
            'where mvn >nul 2>nul && (\n'
            '  pushd backend\n'
            '  call mvn install\n'
            '  popd\n'
            ') || echo Maven not found. Skipping backend install.\n'
        )
        backend_run_windows = 'start "Backend" cmd /k "cd backend && mvn spring-boot:run"\n'
        backend_run_unix = '(cd backend && mvn spring-boot:run) &\n'

    return {
        "setup.bat": f"""@echo off
setlocal
{backend_setup}if exist frontend\\package.json (
  pushd frontend
  call npm install
  popd
)
echo Setup complete.
""",
        "setup.sh": """#!/usr/bin/env bash
set -e
if [ -f backend/requirements.txt ]; then
  python -m pip install -r backend/requirements.txt
fi
if [ -f backend/package.json ]; then
  (cd backend && npm install)
fi
if [ -f backend/pom.xml ]; then
  if command -v mvn >/dev/null 2>&1; then
    (cd backend && mvn install)
  else
    echo "Maven not found. Skipping backend install."
  fi
fi
if [ -f frontend/package.json ]; then
  (cd frontend && npm install)
fi
echo "Setup complete."
""",
        "run.bat": f"""@echo off
setlocal
{backend_run_windows}start "Frontend" cmd /k "cd frontend && npm run dev"
""",
        "run.sh": f"""#!/usr/bin/env bash
set -e
{backend_run_unix}(cd frontend && npm run dev) &
wait
""",
    }


def build_python_scripts(target_dir: str) -> dict[str, str]:
    directory_prefix = "" if target_dir in {"", "."} else f"{target_dir}/"
    windows_prefix = "" if target_dir in {"", "."} else f"{target_dir}\\"
    return {
        "setup.bat": f"""@echo off
setlocal
python -m pip install -r {windows_prefix}requirements.txt
echo Setup complete.
""",
        "setup.sh": f"""#!/usr/bin/env bash
set -e
python -m pip install -r {directory_prefix}requirements.txt
echo "Setup complete."
""",
        "run.bat": f"""@echo off
setlocal
python -m uvicorn app.main:app --reload
""",
        "run.sh": f"""#!/usr/bin/env bash
set -e
python -m uvicorn app.main:app --reload
""",
    }


def build_node_scripts(target_dir: str) -> dict[str, str]:
    directory_prefix = "" if target_dir in {"", "."} else f"{target_dir}/"
    windows_prefix = "" if target_dir in {"", "."} else f"{target_dir}\\"
    return {
        "setup.bat": f"""@echo off
setlocal
pushd {windows_prefix or "."}
call npm install
popd
echo Setup complete.
""",
        "setup.sh": f"""#!/usr/bin/env bash
set -e
(cd {directory_prefix or "."} && npm install)
echo "Setup complete."
""",
        "run.bat": f"""@echo off
setlocal
pushd {windows_prefix or "."}
call npm run dev
popd
""",
        "run.sh": f"""#!/usr/bin/env bash
set -e
(cd {directory_prefix or "."} && npm run dev)
""",
    }


def build_java_scripts(target_dir: str) -> dict[str, str]:
    directory_prefix = "" if target_dir in {"", "."} else f"{target_dir}/"
    windows_prefix = "" if target_dir in {"", "."} else f"{target_dir}\\"
    return {
        "setup.bat": f"""@echo off
setlocal
where mvn >nul 2>nul && (
  pushd {windows_prefix or "."}
  call mvn install
  popd
) || (
  echo Maven not found. Skipping install.
)
""",
        "setup.sh": f"""#!/usr/bin/env bash
set -e
if command -v mvn >/dev/null 2>&1; then
  (cd {directory_prefix or "."} && mvn install)
else
  echo "Maven not found. Skipping install."
fi
""",
        "run.bat": f"""@echo off
setlocal
pushd {windows_prefix or "."}
call mvn spring-boot:run
popd
""",
        "run.sh": f"""#!/usr/bin/env bash
set -e
(cd {directory_prefix or "."} && mvn spring-boot:run)
""",
    }


def normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        lines = [item.strip(" -*\t") for item in value.splitlines()]
        return [line for line in lines if line]
    if isinstance(value, Mapping):
        return [f"{key}: {str(item).strip()}" for key, item in value.items() if str(item).strip()]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def normalize_modules(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    modules: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        modules.append(
            {
                "name": name,
                "purpose": str(item.get("purpose") or "").strip(),
                "keyFiles": normalize_string_list(item.get("keyFiles")),
            }
        )
    return modules


def merge_modules(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for collection in (secondary, primary):
        for module in collection:
            key = module["name"].strip().lower()
            current = merged.setdefault(
                key,
                {"name": module["name"], "purpose": "", "keyFiles": []},
            )
            if module.get("purpose"):
                current["purpose"] = module["purpose"]
            current["keyFiles"] = dedupe_list(current["keyFiles"] + normalize_string_list(module.get("keyFiles")))
    return list(merged.values())


def normalize_env_variables(value: Any) -> list[dict[str, str]]:
    if isinstance(value, Mapping):
        value = [{"name": key, "value": str(item), "description": ""} for key, item in value.items()]
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    env_vars: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        env_vars.append(
            {
                "name": name,
                "value": str(item.get("value") or "").strip(),
                "description": str(item.get("description") or "").strip(),
            }
        )
    return env_vars


def normalize_required_inputs(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, Mapping):
        value = [value]
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []

    required_inputs: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        required_flag = item.get("required")
        required_inputs.append(
            {
                "name": name,
                "required": _coerce_required_flag(required_flag),
                "example": str(item.get("example") or item.get("value") or "").strip(),
                "whereToAdd": str(item.get("whereToAdd") or ".env").strip() or ".env",
                "whereToEnter": str(item.get("whereToEnter") or item.get("whereToAdd") or ".env").strip() or ".env",
                "purpose": str(item.get("purpose") or item.get("description") or "").strip(),
            }
        )
    return dedupe_required_inputs(required_inputs)


def merge_required_inputs(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for collection in (secondary, primary):
        for item in collection:
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            merged[name] = {
                "name": name,
                "required": _coerce_required_flag(item.get("required", True)),
                "example": str(item.get("example") or "").strip(),
                "whereToAdd": str(item.get("whereToAdd") or ".env").strip() or ".env",
                "whereToEnter": str(item.get("whereToEnter") or item.get("whereToAdd") or ".env").strip() or ".env",
                "purpose": str(item.get("purpose") or "").strip(),
            }
    return list(merged.values())


def merge_env_variables(
    primary: list[dict[str, str]],
    secondary: list[dict[str, str]],
) -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for collection in (secondary, primary):
        for item in collection:
            merged[item["name"]] = {
                "name": item["name"],
                "value": item.get("value", ""),
                "description": item.get("description", ""),
            }
    return list(merged.values())


def normalize_files(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    files: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        path = clean_relative_path(item.get("path"))
        if not path:
            continue
        files.append({"path": path, "content": trim_content_lines(str(item.get("content") or ""), allow_long=True)})
    return files


def merge_file_entries(
    primary: list[dict[str, str]],
    secondary: list[dict[str, str]],
) -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for file_entry in primary:
        merged[file_entry["path"]] = file_entry
    for file_entry in secondary:
        merged[file_entry["path"]] = file_entry
    return list(merged.values())


def build_chosen_stack(selected_stack: dict[str, str]) -> list[str]:
    safe_stack = normalize_stack_selection(selected_stack)
    labels = {
        "language": "Language",
        "frontend": "Frontend",
        "backend": "Backend",
        "database": "Database",
        "aiTools": "AI / Tools",
        "deployment": "Deployment",
    }
    return [
        f"{labels[field]}: {safe_stack[field]}"
        for field in STACK_FIELDS
        if safe_stack.get(field) not in {"", "Auto"}
    ]


def coerce_text_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        for key in ("value", "label", "name", "id"):
            nested = value.get(key)
            if nested is not None:
                coerced = coerce_text_value(nested)
                if coerced:
                    return coerced
        flattened = [coerce_text_value(item) for item in value.values()]
        return ", ".join(item for item in flattened if item).strip()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        flattened = [coerce_text_value(item) for item in value]
        return ", ".join(item for item in flattened if item).strip()
    return str(value).strip()


def clean_relative_path(value: Any) -> str:
    path = str(value or "").replace("\\", "/").strip().strip("/")
    if not path or path.startswith(".") or ".." in path.split("/"):
        return ""
    return path


def is_standard_file_path(path: str) -> bool:
    standard_names = {
        "readme.md",
        "requirements.txt",
        "package.json",
        "pom.xml",
        ".env.example",
        "setup.bat",
        "setup.sh",
        "run.bat",
        "run.sh",
        "vite.config.js",
        "server.js",
        "index.html",
        "main.py",
        "main.jsx",
        "main.js",
        "app.jsx",
        "application.java",
    }
    return Path(path).name.lower() in standard_names


def dedupe_manifest(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for item in items:
        path = item["path"]
        if path in seen:
            continue
        seen.add(path)
        result.append(item)
    return result


def dedupe_required_inputs(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(
            {
                "name": name,
                "required": _coerce_required_flag(item.get("required", True)),
                "example": str(item.get("example") or "").strip(),
                "whereToAdd": str(item.get("whereToAdd") or ".env").strip() or ".env",
                "whereToEnter": str(item.get("whereToEnter") or item.get("whereToAdd") or ".env").strip() or ".env",
                "purpose": str(item.get("purpose") or "").strip(),
            }
        )
    return result


def trim_content_lines(content: str, allow_long: bool = False) -> str:
    if allow_long:
        return content
    lines = content.splitlines()
    if len(lines) <= MAX_CUSTOM_FILE_LINES:
        return content
    return "\n".join(lines[:MAX_CUSTOM_FILE_LINES]).rstrip() + "\n"


def safe_component_name(value: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", value)
    return "".join(part.capitalize() for part in parts) or "GeneratedComponent"


def safe_python_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()
    return cleaned or "generated_item"


def safe_js_name(value: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", value)
    if not parts:
        return "generatedItem"
    head = parts[0].lower()
    tail = "".join(part.capitalize() for part in parts[1:])
    return head + tail


def prefixed(prefix: str, path: str) -> str:
    base = Path(prefix) if prefix else Path()
    return (base / path).as_posix()


def dedupe_list(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = str(item).strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _context_mentions_any(lowered_text: str, keywords: Sequence[str]) -> bool:
    return any(keyword in lowered_text for keyword in keywords)


def _coerce_required_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() not in {"false", "0", "no", "optional"}
    return bool(value)
