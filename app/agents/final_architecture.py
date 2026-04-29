from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


STACK_FIELDS = ("language", "frontend", "backend", "database", "aiTools", "deployment")
AUTO_VALUES = {"", "Auto", None}
NO_VALUES = {"", "Auto", "None", None}


@dataclass(frozen=True, slots=True)
class StackRegistryEntry:
    stack_family: str
    project_type: str
    language: str
    frontend: str
    backend: str
    database: str
    ai_tools: str
    deployment: str
    recommended_ide: str
    alternative_ide: str
    runtime_tools: list[str]
    package_manager: str
    required_files: list[str]
    forbidden_files: list[str]
    forbidden_content: list[str]
    install_commands: list[str]
    run_commands: list[str]
    docs_required: list[str]
    backend_required: bool
    database_required: bool


@dataclass(frozen=True, slots=True)
class FinalArchitectureDecision:
    project_type: str
    stack_family: str
    language: str
    frontend: str
    backend: str
    database: str
    ai_tools: str
    deployment: str
    recommended_ide: str
    alternative_ide: str
    runtime_tools: list[str]
    package_manager: str
    required_files: list[str]
    forbidden_files: list[str]
    forbidden_content: list[str]
    install_commands: list[str]
    run_commands: list[str]
    required_inputs: list[dict[str, Any]]
    docs_required: list[str]
    migration_summary: dict[str, Any] = field(default_factory=dict)
    backend_required: bool = False
    database_required: bool = False
    is_migrated: bool = False

    @property
    def selected_stack(self) -> dict[str, str]:
        return {
            "language": self.language,
            "frontend": self.frontend,
            "backend": self.backend,
            "database": self.database,
            "aiTools": self.ai_tools,
            "deployment": self.deployment,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


BASE_DOCS = [
    "README.md",
    "SETUP_INSTRUCTIONS.md",
    "FULL_RUNTIME_INSTRUCTIONS.md",
    "FILE_STRUCTURE.md",
    "PACKAGE_REQUIREMENTS.md",
]

CONFIG_DOCS = [".env.example", "REQUIRED_INPUTS.md"]


STACK_REGISTRY: dict[str, StackRegistryEntry] = {
    "static_frontend": StackRegistryEntry(
        stack_family="static_frontend",
        project_type="game_or_puzzle",
        language="JavaScript",
        frontend="HTML/CSS/JavaScript",
        backend="None",
        database="None",
        ai_tools="None",
        deployment="None",
        recommended_ide="VS Code",
        alternative_ide="WebStorm",
        runtime_tools=["Browser"],
        package_manager="None",
        required_files=["index.html", "style.css", "script.js", "run.sh", "run.bat", *BASE_DOCS, ".env.example", "REQUIRED_INPUTS.md"],
        forbidden_files=["backend/", "requirements.txt", "pom.xml", "package.json", "src/main/java"],
        forbidden_content=["uvicorn", "FastAPI", "Flask", "Spring Boot", "pip install", "mvn spring-boot:run", "MySQL"],
        install_commands=["No install required"],
        run_commands=["Open index.html directly in a browser"],
        docs_required=[*BASE_DOCS, ".env.example", "REQUIRED_INPUTS.md"],
        backend_required=False,
        database_required=False,
    ),
    "python_fastapi": StackRegistryEntry(
        stack_family="python_fastapi",
        project_type="backend-only",
        language="Python",
        frontend="None",
        backend="FastAPI",
        database="SQLite",
        ai_tools="None",
        deployment="Render",
        recommended_ide="VS Code",
        alternative_ide="PyCharm",
        runtime_tools=["Python 3.10+", "pip", "Uvicorn"],
        package_manager="pip",
        required_files=["backend/app/main.py", "backend/requirements.txt", "backend/run.sh", "backend/run.bat", "backend/setup.sh", "backend/setup.bat", *CONFIG_DOCS, *BASE_DOCS],
        forbidden_files=["pom.xml", "src/main/java", "Application.java"],
        forbidden_content=["SpringApplication", "Spring Boot", "mvn spring-boot:run"],
        install_commands=["pip install -r requirements.txt"],
        run_commands=["uvicorn app.main:app --reload"],
        docs_required=[*CONFIG_DOCS, *BASE_DOCS],
        backend_required=True,
        database_required=True,
    ),
    "python_flask": StackRegistryEntry(
        stack_family="python_flask",
        project_type="backend-only",
        language="Python",
        frontend="None",
        backend="Flask",
        database="SQLite",
        ai_tools="None",
        deployment="Render",
        recommended_ide="VS Code",
        alternative_ide="PyCharm",
        runtime_tools=["Python 3.10+", "pip", "Flask"],
        package_manager="pip",
        required_files=["backend/app/main.py", "backend/requirements.txt", "backend/run.sh", "backend/run.bat", "backend/setup.sh", "backend/setup.bat", *CONFIG_DOCS, *BASE_DOCS],
        forbidden_files=["pom.xml", "src/main/java", "Application.java"],
        forbidden_content=["SpringApplication", "Spring Boot", "mvn spring-boot:run"],
        install_commands=["pip install -r requirements.txt"],
        run_commands=["python app/main.py"],
        docs_required=[*CONFIG_DOCS, *BASE_DOCS],
        backend_required=True,
        database_required=True,
    ),
    "java_spring_boot": StackRegistryEntry(
        stack_family="java_spring_boot",
        project_type="backend-only",
        language="Java",
        frontend="None",
        backend="Spring Boot",
        database="PostgreSQL",
        ai_tools="None",
        deployment="Docker",
        recommended_ide="IntelliJ IDEA",
        alternative_ide="VS Code",
        runtime_tools=["JDK 17+", "Maven"],
        package_manager="Maven",
        required_files=["backend/pom.xml", "backend/src/main/java/com/example/app/Application.java", "backend/src/main/java/com/example/app/controller/HealthController.java", "backend/src/main/resources/application.properties", "backend/run.sh", "backend/run.bat", "backend/setup.sh", "backend/setup.bat", *CONFIG_DOCS, *BASE_DOCS],
        forbidden_files=["requirements.txt", "backend/app/main.py"],
        forbidden_content=["FastAPI", "Flask", "uvicorn", "pip install"],
        install_commands=["mvn install"],
        run_commands=["mvn spring-boot:run"],
        docs_required=[*CONFIG_DOCS, *BASE_DOCS],
        backend_required=True,
        database_required=True,
    ),
    "node_express": StackRegistryEntry(
        stack_family="node_express",
        project_type="backend-only",
        language="JavaScript",
        frontend="None",
        backend="Express",
        database="PostgreSQL",
        ai_tools="None",
        deployment="Render",
        recommended_ide="VS Code",
        alternative_ide="WebStorm",
        runtime_tools=["Node.js 20+", "npm"],
        package_manager="npm",
        required_files=["backend/package.json", "backend/server.js", "backend/run.sh", "backend/run.bat", "backend/setup.sh", "backend/setup.bat", *CONFIG_DOCS, *BASE_DOCS],
        forbidden_files=["requirements.txt", "pom.xml", "backend/app/main.py", "src/main/java"],
        forbidden_content=["FastAPI", "Flask", "SpringApplication", "mvn spring-boot:run"],
        install_commands=["npm install"],
        run_commands=["npm run dev"],
        docs_required=[*CONFIG_DOCS, *BASE_DOCS],
        backend_required=True,
        database_required=True,
    ),
    "react_frontend": StackRegistryEntry(
        stack_family="react_frontend",
        project_type="frontend-only",
        language="JavaScript",
        frontend="React",
        backend="None",
        database="None",
        ai_tools="None",
        deployment="Vercel",
        recommended_ide="VS Code",
        alternative_ide="WebStorm",
        runtime_tools=["Node.js 20+", "npm"],
        package_manager="npm",
        required_files=["frontend/package.json", "frontend/index.html", "frontend/src/main.jsx", "frontend/src/App.jsx", "frontend/src/styles.css", *BASE_DOCS],
        forbidden_files=["backend/", "requirements.txt", "pom.xml"],
        forbidden_content=["FastAPI", "Flask", "Spring Boot", "uvicorn", "mvn spring-boot:run"],
        install_commands=["npm install"],
        run_commands=["npm run dev"],
        docs_required=BASE_DOCS,
        backend_required=False,
        database_required=False,
    ),
    "cpp_project": StackRegistryEntry(
        stack_family="cpp_project",
        project_type="cli",
        language="C++",
        frontend="None",
        backend="None",
        database="None",
        ai_tools="None",
        deployment="None",
        recommended_ide="CLion",
        alternative_ide="Visual Studio",
        runtime_tools=["g++ or MSVC"],
        package_manager="Compiler",
        required_files=["main.cpp", "run.sh", "run.bat", *BASE_DOCS],
        forbidden_files=["requirements.txt", "pom.xml", "backend/app/main.py", "package.json"],
        forbidden_content=["FastAPI", "Flask", "SpringApplication", "npm run dev"],
        install_commands=["No install required"],
        run_commands=["g++ main.cpp -o app", "./app"],
        docs_required=BASE_DOCS,
        backend_required=False,
        database_required=False,
    ),
}


def build_final_architecture(
    *,
    prompt: str,
    requested_stack: Mapping[str, Any],
    project_category: str,
    declared_project_type: str,
    migration_summary: Mapping[str, Any] | None = None,
    required_inputs: Sequence[Mapping[str, Any]] | None = None,
) -> FinalArchitectureDecision:
    requested = _normalize_stack(requested_stack)
    stack_family = _choose_stack_family(prompt, requested, project_category, declared_project_type)
    entry = STACK_REGISTRY[stack_family]
    selected = _selected_stack_for_entry(entry, requested, prompt)
    project_type = _project_type_from_stack(entry, selected, declared_project_type)
    required_inputs_list = [dict(item) for item in (required_inputs or [])]
    migration = dict(migration_summary or {})
    docs_required = list(entry.docs_required)
    if migration and "MIGRATION_SUMMARY.md" not in docs_required:
        docs_required.append("MIGRATION_SUMMARY.md")
    required_files = list(entry.required_files)
    if migration and "MIGRATION_SUMMARY.md" not in required_files:
        required_files.append("MIGRATION_SUMMARY.md")
    return FinalArchitectureDecision(
        project_type=project_type,
        stack_family=stack_family,
        language=selected["language"],
        frontend=selected["frontend"],
        backend=selected["backend"],
        database=selected["database"],
        ai_tools=selected["aiTools"],
        deployment=selected["deployment"],
        recommended_ide=entry.recommended_ide,
        alternative_ide=entry.alternative_ide,
        runtime_tools=list(entry.runtime_tools),
        package_manager=entry.package_manager,
        required_files=required_files,
        forbidden_files=list(entry.forbidden_files),
        forbidden_content=list(entry.forbidden_content),
        install_commands=list(entry.install_commands),
        run_commands=list(entry.run_commands),
        required_inputs=required_inputs_list,
        docs_required=docs_required,
        migration_summary=migration,
        backend_required=entry.backend_required,
        database_required=entry.database_required,
        is_migrated=bool(migration),
    )


def infer_final_architecture_from_preview(preview: Mapping[str, Any]) -> FinalArchitectureDecision:
    selected_stack = preview.get("selectedStack") if isinstance(preview.get("selectedStack"), Mapping) else {}
    return build_final_architecture(
        prompt=str(preview.get("problemStatement") or preview.get("summary") or preview.get("projectName") or ""),
        requested_stack=selected_stack,
        project_category="generic",
        declared_project_type=str(preview.get("projectType") or ""),
        migration_summary=preview.get("migrationSummary") if isinstance(preview.get("migrationSummary"), Mapping) else {},
        required_inputs=preview.get("requiredInputs") if isinstance(preview.get("requiredInputs"), Sequence) else [],
    )


def architecture_from_payload(value: Any) -> FinalArchitectureDecision | None:
    if not isinstance(value, Mapping):
        return None
    stack_family = str(value.get("stack_family") or value.get("stackFamily") or "").strip()
    if stack_family not in STACK_REGISTRY:
        return None
    entry = STACK_REGISTRY[stack_family]
    selected = {
        "language": str(value.get("language") or entry.language),
        "frontend": str(value.get("frontend") or entry.frontend),
        "backend": str(value.get("backend") or entry.backend),
        "database": str(value.get("database") or entry.database),
        "aiTools": str(value.get("ai_tools") or value.get("aiTools") or entry.ai_tools),
        "deployment": str(value.get("deployment") or entry.deployment),
    }
    return FinalArchitectureDecision(
        project_type=str(value.get("project_type") or value.get("projectType") or entry.project_type),
        stack_family=stack_family,
        language=selected["language"],
        frontend=selected["frontend"],
        backend=selected["backend"],
        database=selected["database"],
        ai_tools=selected["aiTools"],
        deployment=selected["deployment"],
        recommended_ide=str(value.get("recommended_ide") or value.get("recommendedIde") or entry.recommended_ide),
        alternative_ide=str(value.get("alternative_ide") or value.get("alternativeIde") or entry.alternative_ide),
        runtime_tools=[str(item) for item in value.get("runtime_tools", value.get("runtimeTools", entry.runtime_tools))],
        package_manager=str(value.get("package_manager") or value.get("packageManager") or entry.package_manager),
        required_files=[str(item) for item in value.get("required_files", value.get("requiredFiles", entry.required_files))],
        forbidden_files=[str(item) for item in value.get("forbidden_files", value.get("forbiddenFiles", entry.forbidden_files))],
        forbidden_content=[str(item) for item in value.get("forbidden_content", value.get("forbiddenContent", entry.forbidden_content))],
        install_commands=[str(item) for item in value.get("install_commands", value.get("installCommands", entry.install_commands))],
        run_commands=[str(item) for item in value.get("run_commands", value.get("runCommands", entry.run_commands))],
        required_inputs=[dict(item) for item in value.get("required_inputs", value.get("requiredInputs", [])) if isinstance(item, Mapping)],
        docs_required=[str(item) for item in value.get("docs_required", value.get("docsRequired", entry.docs_required))],
        migration_summary=dict(value.get("migration_summary", value.get("migrationSummary", {})) or {}),
        backend_required=bool(value.get("backend_required", value.get("backendRequired", entry.backend_required))),
        database_required=bool(value.get("database_required", value.get("databaseRequired", entry.database_required))),
        is_migrated=bool(value.get("is_migrated", value.get("isMigrated", False))),
    )


def _normalize_stack(stack: Mapping[str, Any]) -> dict[str, str]:
    return {
        "language": str(stack.get("language") or "Auto"),
        "frontend": str(stack.get("frontend") or "Auto"),
        "backend": str(stack.get("backend") or "Auto"),
        "database": str(stack.get("database") or "Auto"),
        "aiTools": str(stack.get("aiTools") or "Auto"),
        "deployment": str(stack.get("deployment") or "Auto"),
    }


def _choose_stack_family(
    prompt: str,
    requested: Mapping[str, str],
    project_category: str,
    declared_project_type: str,
) -> str:
    lowered = prompt.lower()
    explicit_backend = requested.get("backend") not in NO_VALUES
    explicit_database = requested.get("database") not in NO_VALUES
    if _is_game_or_puzzle(lowered, project_category) and not explicit_backend and not explicit_database:
        return "static_frontend"
    if requested.get("backend") == "Spring Boot" or requested.get("language") == "Java":
        return "java_spring_boot"
    if requested.get("backend") == "Flask":
        return "python_flask"
    if requested.get("backend") == "FastAPI" or requested.get("language") == "Python":
        return "python_fastapi"
    if requested.get("backend") in {"Express", "NestJS"}:
        return "node_express"
    if requested.get("language") == "C++":
        return "cpp_project"
    if requested.get("frontend") in {"React", "Next.js", "Vue"} and requested.get("backend") in NO_VALUES:
        return "react_frontend"
    if any(token in lowered for token in ("rest api", "backend", "server", "login", "auth", "database", "chatbot", "ai assistant", "api key", "llm")):
        if "java" in lowered or "spring" in lowered:
            return "java_spring_boot"
        if "flask" in lowered:
            return "python_flask"
        if "express" in lowered or "node" in lowered:
            return "node_express"
        return "python_fastapi"
    if any(token in lowered for token in ("landing page", "portfolio", "frontend", "react")):
        return "react_frontend" if "react" in lowered else "static_frontend"
    if declared_project_type == "frontend-only":
        return "react_frontend"
    return "python_fastapi"


def _selected_stack_for_entry(
    entry: StackRegistryEntry,
    requested: Mapping[str, str],
    prompt: str,
) -> dict[str, str]:
    selected = {
        "language": entry.language,
        "frontend": entry.frontend,
        "backend": entry.backend,
        "database": entry.database,
        "aiTools": entry.ai_tools,
        "deployment": entry.deployment,
    }
    if entry.stack_family in {"python_fastapi", "python_flask", "java_spring_boot", "node_express"}:
        if requested.get("frontend") not in NO_VALUES:
            selected["frontend"] = requested["frontend"]
        if requested.get("database") not in AUTO_VALUES:
            selected["database"] = requested["database"]
        if _prompt_requests_frontend(prompt) and selected["frontend"] == "None":
            selected["frontend"] = "React"
    if entry.stack_family == "react_frontend" and requested.get("backend") not in NO_VALUES:
        return _selected_stack_for_entry(STACK_REGISTRY["python_fastapi"], requested, prompt)
    return selected


def _project_type_from_stack(
    entry: StackRegistryEntry,
    selected: Mapping[str, str],
    declared_project_type: str,
) -> str:
    if entry.stack_family == "static_frontend":
        return "frontend-only"
    if selected.get("frontend") not in NO_VALUES and selected.get("backend") not in NO_VALUES:
        return "full-stack"
    if selected.get("backend") not in NO_VALUES:
        return "backend-only"
    if selected.get("frontend") not in NO_VALUES:
        return "frontend-only"
    return declared_project_type or entry.project_type


def _is_game_or_puzzle(lowered: str, project_category: str) -> bool:
    return project_category == "game" or any(
        token in lowered
        for token in ("sudoku", "puzzle", "game", "quiz", "memory game", "tic tac toe", "snake")
    )


def _prompt_requests_frontend(prompt: str) -> bool:
    lowered = prompt.lower()
    return any(token in lowered for token in ("web app", "dashboard", "crm", "admin panel", "frontend", "ui", "portal"))
