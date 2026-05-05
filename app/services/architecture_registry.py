from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


AUTO_VALUES = {"", "Auto", "auto", "AUTO", None}


@dataclass(frozen=True, slots=True)
class StackRegistryEntry:
    key: str
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
    forbidden_terms: list[str]
    install_commands: list[str]
    run_commands: list[str]
    package_requirements: list[str]
    backend_required: bool = False
    database_required: bool = False


@dataclass(slots=True)
class FinalArchitectureDecision:
    stack_selection_source: str
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
    runtime_tools: list[str] = field(default_factory=list)
    package_manager: str = ""
    required_files: list[str] = field(default_factory=list)
    forbidden_files: list[str] = field(default_factory=list)
    forbidden_terms: list[str] = field(default_factory=list)
    install_commands: list[str] = field(default_factory=list)
    run_commands: list[str] = field(default_factory=list)
    package_requirements: list[str] = field(default_factory=list)
    main_file: str = ""
    main_run_target: str = ""
    local_url: str = ""
    required_inputs: list[dict[str, Any]] = field(default_factory=list)
    docs_required: list[str] = field(default_factory=list)
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


DOC_FILES = [
    "README.md",
    "SETUP_INSTRUCTIONS.md",
    "FULL_RUNTIME_INSTRUCTIONS.md",
    "FILE_STRUCTURE.md",
    "PACKAGE_REQUIREMENTS.md",
]

VSCODE_FILES = [
    ".vscode/launch.json",
    ".vscode/tasks.json",
]

CONFIG_DOC_FILES = [
    "REQUIRED_INPUTS.md",
    ".env.example",
]


STACK_REGISTRY: dict[str, StackRegistryEntry] = {
    "static_frontend": StackRegistryEntry(
        key="static_frontend",
        stack_family="static_frontend",
        language="JavaScript",
        frontend="HTML/CSS/JavaScript",
        backend="None",
        database="None",
        ai_tools="None",
        deployment="None",
        recommended_ide="VS Code",
        alternative_ide="WebStorm",
        runtime_tools=["Modern browser"],
        package_manager="None",
        required_files=["index.html", "style.css", "script.js", "run.sh", "run.bat", "setup.sh", "setup.bat", *VSCODE_FILES, *DOC_FILES],
        forbidden_files=["backend/", "requirements.txt", "pom.xml", "backend/package.json"],
        forbidden_terms=["uvicorn", "FastAPI", "Flask", "Spring Boot", "pip install", "mvn ", "MySQL setup"],
        install_commands=["No install required"],
        run_commands=["Open index.html directly in a browser"],
        package_requirements=[],
    ),
    "python_fastapi": StackRegistryEntry(
        key="python_fastapi",
        stack_family="python_fastapi",
        language="Python",
        frontend="None",
        backend="FastAPI",
        database="SQLite",
        ai_tools="None",
        deployment="Render",
        recommended_ide="VS Code",
        alternative_ide="PyCharm",
        runtime_tools=["Python 3.11+", "pip", "Uvicorn"],
        package_manager="pip",
        required_files=[
            "backend/app/main.py",
            "backend/app/config.py",
            "backend/app/routers/health.py",
            "backend/app/services/app_service.py",
            "backend/requirements.txt",
            "backend/run.sh",
            "backend/run.bat",
            "backend/setup.sh",
            "backend/setup.bat",
            *VSCODE_FILES,
            ".env.example",
            "REQUIRED_INPUTS.md",
            *DOC_FILES,
        ],
        forbidden_files=["pom.xml", "src/main/java/", "backend/src/main/java/"],
        forbidden_terms=["SpringApplication", "spring-boot:run", "mvn "],
        install_commands=["cd backend", "pip install -r requirements.txt"],
        run_commands=["cd backend", "python -m uvicorn app.main:app --reload"],
        package_requirements=["fastapi", "uvicorn", "python-dotenv"],
        backend_required=True,
    ),
    "python_flask": StackRegistryEntry(
        key="python_flask",
        stack_family="python_flask",
        language="Python",
        frontend="None",
        backend="Flask",
        database="SQLite",
        ai_tools="None",
        deployment="Render",
        recommended_ide="VS Code",
        alternative_ide="PyCharm",
        runtime_tools=["Python 3.11+", "pip"],
        package_manager="pip",
        required_files=[
            "backend/app/main.py",
            "backend/app/config.py",
            "backend/requirements.txt",
            "backend/run.sh",
            "backend/run.bat",
            "backend/setup.sh",
            "backend/setup.bat",
            *VSCODE_FILES,
            ".env.example",
            "REQUIRED_INPUTS.md",
            *DOC_FILES,
        ],
        forbidden_files=["pom.xml", "src/main/java/", "backend/src/main/java/"],
        forbidden_terms=["FastAPI", "uvicorn", "SpringApplication", "spring-boot:run", "mvn "],
        install_commands=["cd backend", "pip install -r requirements.txt"],
        run_commands=["cd backend", "python app/main.py"],
        package_requirements=["flask", "python-dotenv"],
        backend_required=True,
    ),
    "java_spring_boot": StackRegistryEntry(
        key="java_spring_boot",
        stack_family="java_spring_boot",
        language="Java",
        frontend="None",
        backend="Spring Boot",
        database="H2",
        ai_tools="None",
        deployment="Render",
        recommended_ide="IntelliJ IDEA",
        alternative_ide="VS Code",
        runtime_tools=["JDK 17+", "Maven"],
        package_manager="Maven",
        required_files=[
            "backend/pom.xml",
            "backend/src/main/java/com/example/app/Application.java",
            "backend/src/main/java/com/example/app/controller/HealthController.java",
            "backend/src/main/resources/application.properties",
            "backend/run.sh",
            "backend/run.bat",
            "backend/setup.sh",
            "backend/setup.bat",
            *VSCODE_FILES,
            ".env.example",
            "REQUIRED_INPUTS.md",
            *DOC_FILES,
        ],
        forbidden_files=["requirements.txt", "backend/app/main.py", "backend/app/"],
        forbidden_terms=["FastAPI", "Flask", "uvicorn", "pip install"],
        install_commands=["cd backend", "mvn clean install"],
        run_commands=["cd backend", "mvn spring-boot:run"],
        package_requirements=["spring-boot-starter-web", "spring-boot-starter-validation"],
        backend_required=True,
    ),
    "node_express": StackRegistryEntry(
        key="node_express",
        stack_family="node_express",
        language="JavaScript",
        frontend="None",
        backend="Express",
        database="SQLite",
        ai_tools="None",
        deployment="Render",
        recommended_ide="VS Code",
        alternative_ide="WebStorm",
        runtime_tools=["Node.js 20+", "npm"],
        package_manager="npm",
        required_files=["backend/package.json", "backend/src/server.js", "backend/run.sh", "backend/run.bat", "backend/setup.sh", "backend/setup.bat", *VSCODE_FILES, ".env.example", "REQUIRED_INPUTS.md", *DOC_FILES],
        forbidden_files=["requirements.txt", "pom.xml", "backend/app/main.py", "src/main/java/"],
        forbidden_terms=["FastAPI", "Flask", "SpringApplication", "mvn ", "pip install"],
        install_commands=["cd backend", "npm install"],
        run_commands=["cd backend", "npm run dev"],
        package_requirements=["express", "cors", "dotenv"],
        backend_required=True,
    ),
    "react_frontend": StackRegistryEntry(
        key="react_frontend",
        stack_family="react_frontend",
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
        required_files=[
            "frontend/package.json",
            "frontend/index.html",
            "frontend/src/main.jsx",
            "frontend/src/App.jsx",
            "frontend/src/styles.css",
            "frontend/run.sh",
            "frontend/run.bat",
            "frontend/setup.sh",
            "frontend/setup.bat",
            *VSCODE_FILES,
            *DOC_FILES,
        ],
        forbidden_files=["backend/", "requirements.txt", "pom.xml"],
        forbidden_terms=["FastAPI", "Flask", "Spring Boot", "uvicorn", "spring-boot:run"],
        install_commands=["cd frontend", "npm install"],
        run_commands=["cd frontend", "npm run dev"],
        package_requirements=["react", "vite"],
    ),
    "cpp_project": StackRegistryEntry(
        key="cpp_project",
        stack_family="cpp_project",
        language="C++",
        frontend="None",
        backend="None",
        database="None",
        ai_tools="None",
        deployment="None",
        recommended_ide="CLion",
        alternative_ide="Visual Studio",
        runtime_tools=["g++ or MSVC", "CMake optional"],
        package_manager="CMake",
        required_files=["main.cpp", "run.sh", "run.bat", *VSCODE_FILES, *DOC_FILES],
        forbidden_files=["requirements.txt", "pom.xml", "backend/app/main.py", "backend/", "package.json"],
        forbidden_terms=["FastAPI", "Flask", "Spring Boot", "uvicorn", "pip install", "npm install"],
        install_commands=["No package install required"],
        run_commands=["g++ main.cpp -o app", "./app"],
        package_requirements=[],
    ),
}


def build_final_architecture_decision(
    *,
    prompt: str,
    requested_stack: Mapping[str, Any] | None = None,
    inferred_stack: Mapping[str, Any] | None = None,
    declared_project_type: str = "",
    project_category: str = "",
    migration_summary: Mapping[str, Any] | None = None,
    is_migrated: bool = False,
    stack_selection_source: str = "",
    is_user_confirmed_stack: bool = False,
    last_modified_field: str = "",
) -> FinalArchitectureDecision:
    requested = _normalize_stack(requested_stack)
    inferred = _normalize_stack(inferred_stack)
    source = stack_selection_source or str((requested_stack or {}).get("source") or "")
    confirmed = bool(
        is_user_confirmed_stack
        or (requested_stack or {}).get("isUserConfirmedStack")
        or (requested_stack or {}).get("is_user_confirmed")
        or (requested_stack or {}).get("isDirty")
        or (requested_stack or {}).get("is_dirty")
    )
    last_field = str(
        last_modified_field
        or (requested_stack or {}).get("lastModifiedField")
        or (requested_stack or {}).get("last_modified_field")
        or ""
    )
    prompt_l = (prompt or "").lower()
    project_type = _project_type(prompt_l, declared_project_type, project_category)
    backend_explicit = confirmed and _explicit(requested.get("backend")) or _explicit(requested.get("backend")) or _mentions_backend(prompt_l)
    database_explicit = _explicit(requested.get("database")) or any(word in prompt_l for word in ["database", "mysql", "postgres", "sqlite", "mongodb"])

    key = _registry_key_for(
        requested,
        inferred,
        prompt_l,
        project_type,
        backend_explicit,
        is_user_confirmed_stack=confirmed,
        last_modified_field=last_field,
    )
    entry = STACK_REGISTRY[key]

    selected = asdict(entry)
    language = entry.language
    frontend = entry.frontend
    backend = entry.backend
    database = entry.database
    ai_tools = entry.ai_tools
    deployment = entry.deployment

    if key not in {"static_frontend", "react_frontend", "cpp_project"}:
        frontend = _pick(requested.get("frontend"), inferred.get("frontend"), entry.frontend)
        if frontend in {"Auto", ""}:
            frontend = entry.frontend
        if frontend == "React" and key in {"python_fastapi", "python_flask", "java_spring_boot", "node_express"}:
            selected["required_files"] = _with_react_files(entry.required_files)
    if key == "react_frontend":
        frontend = "React"
    if key not in {"static_frontend", "react_frontend", "cpp_project"} and database_explicit:
        database = _pick(requested.get("database"), inferred.get("database"), entry.database)
    ai_tools = _pick(requested.get("aiTools"), inferred.get("aiTools"), entry.ai_tools)
    if ai_tools == "Auto":
        ai_tools = entry.ai_tools
    deployment = _pick(requested.get("deployment"), inferred.get("deployment"), entry.deployment)
    if deployment == "Auto":
        deployment = entry.deployment

    docs_required = list(DOC_FILES)
    if entry.backend_required or database != "None" or ai_tools != "None":
        docs_required = [*docs_required, *CONFIG_DOC_FILES]
    if is_migrated:
        docs_required.append("MIGRATION_SUMMARY.md")

    required_files = sorted(set(selected["required_files"]) | set(docs_required))
    if is_migrated:
        required_files.append("MIGRATION_SUMMARY.md")

    return FinalArchitectureDecision(
        stack_selection_source=_stack_source_label(source, confirmed),
        project_type=project_type,
        stack_family=entry.stack_family,
        language=language,
        frontend=frontend,
        backend=backend,
        database=database,
        ai_tools=ai_tools,
        deployment=deployment,
        recommended_ide=entry.recommended_ide,
        alternative_ide=entry.alternative_ide,
        runtime_tools=list(entry.runtime_tools),
        package_manager=entry.package_manager,
        required_files=sorted(set(required_files)),
        forbidden_files=list(entry.forbidden_files),
        forbidden_terms=list(entry.forbidden_terms),
        install_commands=list(entry.install_commands),
        run_commands=list(entry.run_commands),
        package_requirements=list(entry.package_requirements),
        main_file=_main_file_for(entry.stack_family, language, frontend, backend),
        main_run_target=_main_run_target_for(entry.stack_family, language, frontend, backend),
        local_url=_local_url_for(entry.stack_family, frontend, backend),
        docs_required=sorted(set(docs_required)),
        migration_summary=dict(migration_summary or {}),
        backend_required=entry.backend_required,
        database_required=entry.database_required or database != "None",
        is_migrated=is_migrated,
    )


def final_architecture_from_preview(preview: Mapping[str, Any]) -> FinalArchitectureDecision:
    prompt = str(preview.get("problemStatement") or preview.get("summary") or preview.get("projectName") or "")
    return build_final_architecture_decision(
        prompt=prompt,
        requested_stack=_normalize_stack(preview.get("selectedStack")),
        inferred_stack=_normalize_stack(preview.get("selectedStack")),
        declared_project_type=str(preview.get("projectType") or ""),
        project_category="game" if str(preview.get("templateFamily") or "") == "puzzle-game" else "",
        migration_summary=preview.get("migrationSummary") if isinstance(preview.get("migrationSummary"), Mapping) else None,
        is_migrated=bool(preview.get("migrationSummary")),
        stack_selection_source=str(preview.get("stackSelectionSource") or ""),
        is_user_confirmed_stack=bool(preview.get("isUserConfirmedStack") or False),
    )


def stack_key_for_selected(selected_stack: Mapping[str, Any], template_family: str = "") -> str:
    normalized = _normalize_stack(selected_stack)
    if template_family == "puzzle-game":
        return "static_frontend"
    return _registry_key_for(normalized, normalized, "", "", _explicit(normalized.get("backend")))


def registry_entry_for_selected(selected_stack: Mapping[str, Any], template_family: str = "") -> StackRegistryEntry:
    return STACK_REGISTRY[stack_key_for_selected(selected_stack, template_family)]


def forbidden_path(path: str, forbidden_files: list[str]) -> bool:
    lower = path.replace("\\", "/").lower()
    for forbidden in forbidden_files:
        check = forbidden.replace("\\", "/").lower()
        if check.endswith("/"):
            if lower.startswith(check) or f"/{check}" in lower:
                return True
        elif lower == check or lower.endswith("/" + check):
            return True
    return False


def _normalize_stack(stack: Mapping[str, Any] | None) -> dict[str, str]:
    source = dict(stack or {})
    return {
        "language": str(source.get("language") or "Auto"),
        "frontend": str(source.get("frontend") or "Auto"),
        "backend": str(source.get("backend") or "Auto"),
        "database": str(source.get("database") or "Auto"),
        "aiTools": str(source.get("aiTools") or source.get("ai_tools") or "Auto"),
        "deployment": str(source.get("deployment") or "Auto"),
    }


def _explicit(value: Any) -> bool:
    return value not in AUTO_VALUES and str(value) != "None"


def _pick(*values: Any) -> str:
    for value in values:
        if _explicit(value):
            return str(value)
    return "Auto"


def _project_type(prompt_l: str, declared: str, category: str) -> str:
    if category == "game" or any(word in prompt_l for word in ["sudoku", "puzzle", "game", "quiz", "tic tac toe", "snake", "memory game"]):
        return "game_or_puzzle"
    if any(word in prompt_l for word in ["chatbot", "ai assistant", "api key", "llm"]):
        return "ai_app"
    if any(word in prompt_l for word in ["inventory", "dashboard", "crm", "admin panel"]):
        return "business_app"
    return declared or "web_app"


def _stack_source_label(source: str, confirmed: bool) -> str:
    if confirmed:
        return source or "user_modified_suggestion"
    return source or "architecture_default"


def _mentions_backend(prompt_l: str) -> bool:
    return any(word in prompt_l for word in ["backend", "server", "rest api", "login", "auth", "database", "api endpoint"])


def _registry_key_for(
    requested: Mapping[str, str],
    inferred: Mapping[str, str],
    prompt_l: str,
    project_type: str,
    backend_explicit: bool,
    *,
    is_user_confirmed_stack: bool = False,
    last_modified_field: str = "",
) -> str:
    language = _pick(requested.get("language"), inferred.get("language"))
    frontend = _pick(requested.get("frontend"), inferred.get("frontend"))
    backend = _pick(requested.get("backend"), inferred.get("backend"))
    combined = " ".join([language, frontend, backend, prompt_l]).lower()

    if is_user_confirmed_stack:
        if last_modified_field == "backend":
            if backend == "Spring Boot":
                return "java_spring_boot"
            if backend == "Flask":
                return "python_flask"
            if backend == "FastAPI":
                return "python_fastapi"
            if backend == "Express":
                return "node_express"
        if last_modified_field == "language":
            if language == "Java":
                return "java_spring_boot"
            if language == "Python":
                return "python_fastapi"
            if language == "JavaScript":
                return "react_frontend" if backend in {"Auto", "None", ""} and frontend == "React" else "node_express"
            if language == "C++":
                return "cpp_project"
        if backend == "Spring Boot" or language == "Java":
            return "java_spring_boot"
        if backend == "Flask":
            return "python_flask"
        if backend == "FastAPI" or language == "Python":
            return "python_fastapi"
        if backend == "Express":
            return "node_express"
        if frontend == "React" and not backend_explicit:
            return "react_frontend"

    if project_type == "game_or_puzzle" and not backend_explicit:
        return "static_frontend"
    if "spring boot" in combined or language == "Java":
        return "java_spring_boot"
    if backend == "Flask" or "flask" in combined:
        return "python_flask"
    if backend == "FastAPI" or language == "Python" or "fastapi" in combined:
        return "python_fastapi"
    if backend == "Express" or "express" in combined or "node" in combined:
        return "node_express"
    if frontend == "React" and not backend_explicit:
        return "react_frontend"
    if language == "C++" or "c++" in combined or "main.cpp" in prompt_l:
        return "cpp_project"
    if frontend == "HTML/CSS/JavaScript":
        return "static_frontend"
    return "python_fastapi"


def _with_react_files(required_files: list[str]) -> list[str]:
    return [
        *required_files,
        "frontend/package.json",
        "frontend/index.html",
        "frontend/src/main.jsx",
        "frontend/src/App.jsx",
        "frontend/src/styles.css",
        "frontend/run.sh",
        "frontend/run.bat",
        "frontend/setup.sh",
        "frontend/setup.bat",
        ".vscode/launch.json",
        ".vscode/tasks.json",
    ]


def _main_file_for(stack_family: str, language: str, frontend: str, backend: str) -> str:
    if backend in {"FastAPI", "Flask"}:
        return "backend/app/main.py"
    if backend == "Spring Boot" or language == "Java":
        return "backend/src/main/java/com/example/app/Application.java"
    if backend == "Express":
        return "backend/server.js"
    if frontend == "React":
        return "frontend/src/main.jsx"
    if stack_family == "static_frontend" or frontend == "HTML/CSS/JavaScript":
        return "index.html"
    if language == "C++":
        return "main.cpp"
    return "README.md"


def _main_run_target_for(stack_family: str, language: str, frontend: str, backend: str) -> str:
    if stack_family == "static_frontend" or frontend == "HTML/CSS/JavaScript":
        return "Open index.html in browser"
    if backend == "FastAPI":
        return "Click IDE Play button or run run.bat / run.sh"
    if backend == "Flask":
        return "Click IDE Play button or run run.bat / run.sh"
    if backend == "Spring Boot" or language == "Java":
        return "Click IDE Play button or run mvn spring-boot:run"
    if backend == "Express":
        return "VS Code Run Task or run npm run dev"
    if frontend == "React":
        return "VS Code Run Task or run npm run dev"
    if language == "C++":
        return "VS Code Run Task or run run.bat / run.sh"
    return "Run run.bat / run.sh"


def _local_url_for(stack_family: str, frontend: str, backend: str) -> str:
    if backend == "FastAPI":
        return "http://localhost:8000"
    if backend == "Flask":
        return "http://localhost:5000"
    if backend == "Spring Boot":
        return "http://localhost:8080"
    if frontend == "React":
        return "http://localhost:5173"
    if stack_family == "static_frontend" or frontend == "HTML/CSS/JavaScript":
        return "Open index.html directly"
    return ""
