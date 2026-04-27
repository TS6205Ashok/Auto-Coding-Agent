from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


MAX_GENERATED_FILES = 60
MAX_FILE_SIZE_BYTES = 250 * 1024

SYSTEM_FILENAMES = {
    "README.md",
    "PROJECT_EXPLANATION.md",
    "SETUP_INSTRUCTIONS.md",
    "FILE_STRUCTURE.md",
    "PACKAGE_REQUIREMENTS.md",
    "REQUIRED_INPUTS.md",
    ".env.example",
}


def slugify(value: str, fallback: str = "project-agent-output") -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def sanitize_relative_path(raw_path: str) -> Path:
    if not isinstance(raw_path, str):
        raise ValueError("Generated file paths must be strings.")

    normalized = raw_path.replace("\\", "/").strip()
    if not normalized:
        raise ValueError("Generated file paths cannot be empty.")
    if normalized.startswith(("/", "~")):
        raise ValueError(f"Absolute paths are not allowed: {raw_path}")
    if re.match(r"^[a-zA-Z]:", normalized):
        raise ValueError(f"Drive-qualified paths are not allowed: {raw_path}")

    posix_path = PurePosixPath(normalized)
    safe_parts: list[str] = []
    for part in posix_path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            raise ValueError(f"Path traversal is not allowed: {raw_path}")
        safe_parts.append(part)

    if not safe_parts:
        raise ValueError(f"Generated file path is invalid: {raw_path}")

    return Path(*safe_parts)


def ensure_within_directory(base_dir: Path, candidate: Path) -> bool:
    resolved_base = base_dir.resolve()
    resolved_candidate = candidate.resolve()
    return resolved_candidate.is_relative_to(resolved_base)


def validate_generated_files(files: list[dict[str, str]]) -> list[dict[str, str]]:
    if len(files) > MAX_GENERATED_FILES:
        raise ValueError(
            f"Generated output exceeds the limit of {MAX_GENERATED_FILES} files."
        )

    validated: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    for file_entry in files:
        raw_path = str(file_entry.get("path", ""))
        relative_path = sanitize_relative_path(raw_path)
        normalized_path = relative_path.as_posix()
        if normalized_path in seen_paths:
            continue

        content = str(file_entry.get("content", ""))
        content_size = len(content.encode("utf-8"))
        if content_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"Generated file '{normalized_path}' exceeds the size limit of 250 KB."
            )

        seen_paths.add(normalized_path)
        validated.append({"path": normalized_path, "content": content})

    return validated


def build_required_docs(
    preview: dict[str, Any], bundle_info: dict[str, Any] | None = None
) -> dict[str, str]:
    bundle_info = bundle_info or {}
    project_name = str(preview.get("projectName") or "Generated Project").strip()
    detected_choices = _listify(preview.get("detectedUserChoices"))
    chosen_stack = _listify(preview.get("chosenStack"))
    assumptions = _listify(preview.get("assumptions"))
    architecture = _listify(preview.get("architecture"))
    package_requirements = _listify(preview.get("packageRequirements"))
    install_commands = _listify(preview.get("installCommands"))
    run_commands = _listify(preview.get("runCommands"))
    modules = preview.get("modules") or []
    required_inputs = _required_input_list(preview.get("requiredInputs"))
    env_variables = _env_list(preview.get("envVariables")) or _required_inputs_to_env_list(
        required_inputs
    )
    file_tree = str(
        bundle_info.get("actualFileTree") or preview.get("fileTree") or ""
    ).strip()
    summary = str(preview.get("summary") or "No summary was provided by the model.").strip()
    problem_statement = str(
        preview.get("problemStatement") or "No problem statement was provided by the model."
    ).strip()
    selected_stack = preview.get("selectedStack") or {}

    readme = "\n".join(
        [
            f"# {project_name}",
            "",
            summary,
            "",
            "## What Was Generated",
            "This ZIP contains a 100% runnable starter project from the latest preview, including dependency files, setup scripts, run scripts, starter source code, and required input guidance.",
            "",
            "## Problem Statement",
            problem_statement,
            "",
            "## Selected Stack",
            _selected_stack_text(selected_stack),
            "",
            "## Chosen Stack",
            _bullet_text(chosen_stack, "The generated plan did not include stack details."),
            "",
            "## Detected User Choices",
            _bullet_text(
                detected_choices,
                "The user did not explicitly specify language, tooling, or framework choices.",
            ),
            "",
            "## Architecture Highlights",
            _bullet_text(architecture, "Architecture details were not provided."),
            "",
            "## Core Modules",
            _modules_text(modules),
            "",
            "## Setup",
            "Fill `.env` from `.env.example`, then run the setup script before starting the project.",
            "- Windows: `setup.bat`",
            "- Mac/Linux: `setup.sh`",
            "",
            "## How To Run",
            _bullet_text(run_commands, "No run commands were provided."),
            "",
            "## Required Inputs",
            "Fill these values in `.env` before running the project.",
            "",
            _required_inputs_summary(required_inputs),
            "",
            "## Notes",
            _bullet_text(assumptions, "No assumptions were recorded."),
        ]
    ).strip() + "\n"

    explanation = "\n".join(
        [
            f"# {project_name} Explanation",
            "",
            "## Summary",
            summary,
            "",
            "## Problem Statement",
            problem_statement,
            "",
            "## Selected Stack",
            _selected_stack_text(selected_stack),
            "",
            "## Architecture",
            _bullet_text(architecture, "Architecture details were not provided."),
            "",
            "## Modules",
            _modules_text(modules),
            "",
            "## Assumptions",
            _bullet_text(assumptions, "No assumptions were recorded."),
        ]
    ).strip() + "\n"

    setup_instructions = "\n".join(
        [
            "# Setup Instructions",
            "",
            "## Quick Start",
            "1. Run `run.bat` on Windows or `./run.sh` on Mac/Linux.",
            "2. Enter any missing required inputs when the app prompts for them at runtime.",
            "3. The application will finish startup automatically after dependencies install and required values are provided.",
            "",
            "## Windows",
            "1. Run `run.bat`.",
            "2. If `.env` is missing, the script will create it from `.env.example` automatically.",
            "3. If a required backend value is still missing, enter it when prompted in the terminal.",
            "",
            "## Mac/Linux",
            "1. Run `chmod +x setup.sh run.sh` once if the scripts are not executable.",
            "2. Run `./run.sh`.",
            "3. If `.env` is missing, the script will create it from `.env.example` automatically.",
            "4. If a required backend value is still missing, enter it when prompted in the terminal.",
            "",
            "## Setup Scripts",
            "- Windows: `setup.bat`",
            "- Mac/Linux: `setup.sh`",
            "",
            "## Selected Stack",
            _selected_stack_text(selected_stack),
            "",
            "## Install Commands",
            _bullet_text(install_commands, "No install commands were provided."),
            "",
            "## Run Commands",
            _bullet_text(run_commands, "No run commands were provided."),
            "",
            "## Environment Variables",
            _env_variables_text(env_variables),
            "",
            "## Troubleshooting",
            "- If dependencies fail to install, confirm Python, Node.js, or Maven is installed for the selected stack.",
            "- If the app cannot connect to a service, double-check the values in `.env` against `REQUIRED_INPUTS.md`.",
            "- If frontend and backend both start locally, verify `VITE_API_BASE_URL` or related API host settings match the backend URL.",
            "",
            "## Notes",
            _bullet_text(assumptions, "No additional assumptions were provided."),
        ]
    ).strip() + "\n"

    structure = "\n".join(
        [
            "# File Structure",
            "",
            "## Final Generated Tree",
            "```text",
            file_tree or "No file tree was available.",
            "```",
            "",
            "## Included Modules",
            _modules_text(modules),
        ]
    ).strip() + "\n"

    package_docs = "\n".join(
        [
            "# Package Requirements",
            "",
            "## Libraries And Packages",
            _bullet_text(package_requirements, "No package requirements were provided."),
            "",
            "## Install Commands",
            _bullet_text(install_commands, "No install commands were provided."),
            "",
            "## Run Commands",
            _bullet_text(run_commands, "No run commands were provided."),
        ]
    ).strip() + "\n"

    required_inputs_doc = "\n".join(
        [
            "# Required Inputs",
            "",
            "Fill these values in `.env` before running the project.",
            "",
            "| Name | Required | Example | Where To Add | Purpose |",
            "|---|---|---|---|---|",
            _required_inputs_table(required_inputs),
        ]
    ).strip() + "\n"

    docs = {
        "README.md": readme,
        "PROJECT_EXPLANATION.md": explanation,
        "SETUP_INSTRUCTIONS.md": setup_instructions,
        "FILE_STRUCTURE.md": structure,
        "PACKAGE_REQUIREMENTS.md": package_docs,
        "REQUIRED_INPUTS.md": required_inputs_doc,
        ".env.example": build_env_example(required_inputs),
    }

    return docs


def build_env_example(required_inputs: list[dict[str, Any]]) -> str:
    if not required_inputs:
        return (
            "# No required inputs were detected for this starter.\n"
            "# Copy this file to .env if you want to override defaults later.\n"
        )

    lines = [
        "# Fill these values in .env before running the project.",
        "# Copy this file to .env and replace the example values as needed.",
        "",
    ]
    for variable in required_inputs:
        name = str(variable.get("name") or "").strip()
        example = str(variable.get("example") or "").strip()
        if name:
            lines.append(f"{name}={example}")
    return "\n".join(lines).rstrip() + "\n"


def build_file_tree_from_paths(paths: list[str]) -> str:
    if not paths:
        return ""

    tree: dict[str, Any] = {}
    for raw_path in paths:
        parts = [part for part in raw_path.replace("\\", "/").split("/") if part]
        current = tree
        for part in parts:
            current = current.setdefault(part, {})

    lines: list[str] = []

    def walk(node: dict[str, Any], depth: int = 0) -> None:
        for name, child in sorted(node.items()):
            lines.append(f"{'  ' * depth}{name}")
            walk(child, depth + 1)

    walk(tree)
    return "\n".join(lines)


def _listify(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [line.strip(" -*\t") for line in value.splitlines()]
        return [item for item in items if item]
    if isinstance(value, dict):
        return [
            f"{key}: {str(item).strip()}"
            for key, item in value.items()
            if str(item).strip()
        ]
    if isinstance(value, (list, tuple, set)):
        items = []
        for item in value:
            text = str(item).strip()
            if text:
                items.append(text)
        return items
    text = str(value).strip()
    return [text] if text else []


def _env_list(value: Any) -> list[dict[str, str]]:
    env_vars: list[dict[str, str]] = []
    if isinstance(value, dict):
        value = [
            {
                "name": key,
                "value": str(item).strip(),
                "description": "",
            }
            for key, item in value.items()
        ]
    if not isinstance(value, (list, tuple)):
        return env_vars

    for item in value:
        if not isinstance(item, dict):
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


def _required_input_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, Mapping):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return []

    required_inputs: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        required_inputs.append(
            {
                "name": name,
                "required": bool(item.get("required", True)),
                "example": str(item.get("example") or item.get("value") or "").strip(),
                "whereToAdd": str(item.get("whereToAdd") or ".env").strip() or ".env",
                "purpose": str(item.get("purpose") or item.get("description") or "").strip(),
            }
        )
    return required_inputs


def _bullet_text(items: list[str], fallback: str) -> str:
    if not items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in items)


def _selected_stack_text(selected_stack: dict[str, Any]) -> str:
    if not isinstance(selected_stack, dict) or not selected_stack:
        return "- No explicit stack selection was recorded."

    ordered_labels = [
        ("language", "Language"),
        ("frontend", "Frontend"),
        ("backend", "Backend"),
        ("database", "Database"),
        ("aiTools", "AI / Tools"),
        ("deployment", "Deployment"),
    ]
    lines = []
    for key, label in ordered_labels:
        value = str(selected_stack.get(key) or "Auto").strip()
        lines.append(f"- {label}: {value}")
    return "\n".join(lines)


def _env_variables_text(env_variables: list[dict[str, str]]) -> str:
    if not env_variables:
        return "- No environment variables are required."

    lines = []
    for variable in env_variables:
        description = variable.get("description", "").strip()
        value = variable.get("value", "").strip()
        suffix = f" ({description})" if description else ""
        default_text = f" default `{value}`" if value else ""
        lines.append(f"- `{variable['name']}`{suffix}{default_text}")
    return "\n".join(lines)


def _required_inputs_to_env_list(required_inputs: list[dict[str, Any]]) -> list[dict[str, str]]:
    env_vars: list[dict[str, str]] = []
    for item in required_inputs:
        env_vars.append(
            {
                "name": str(item.get("name") or "").strip(),
                "value": str(item.get("example") or "").strip(),
                "description": str(item.get("purpose") or "").strip(),
            }
        )
    return [item for item in env_vars if item["name"]]


def _required_inputs_summary(required_inputs: list[dict[str, Any]]) -> str:
    if not required_inputs:
        return "- No required inputs were detected. `.env.example` is still included for future overrides."
    return "\n".join(
        f"- `{item['name']}` ({'required' if item.get('required', True) else 'optional'}): {item.get('purpose') or 'No description provided.'}"
        for item in required_inputs
    )


def _required_inputs_table(required_inputs: list[dict[str, Any]]) -> str:
    if not required_inputs:
        return "| None | No | n/a | `.env` | No required external values were detected for this starter. |"

    rows = []
    for item in required_inputs:
        rows.append(
            "| {name} | {required} | {example} | {where_to_add} | {purpose} |".format(
                name=item.get("name") or "",
                required="Yes" if item.get("required", True) else "No",
                example=(item.get("example") or "").replace("|", "\\|"),
                where_to_add=(item.get("whereToAdd") or ".env").replace("|", "\\|"),
                purpose=(item.get("purpose") or "").replace("|", "\\|"),
            )
        )
    return "\n".join(rows)


def _modules_text(modules: list[dict[str, Any]]) -> str:
    if not modules:
        return "- No modules were provided."

    lines: list[str] = []
    for module in modules:
        name = str(module.get("name") or "Unnamed module").strip()
        purpose = str(module.get("purpose") or "No purpose provided.").strip()
        key_files = _listify(module.get("keyFiles"))
        lines.append(f"- {name}: {purpose}")
        if key_files:
            lines.append(f"  Key files: {', '.join(key_files)}")
    return "\n".join(lines)


MAX_CUSTOM_TEMPLATE_FILES = 8
MAX_CUSTOM_FILE_LINES = 300


def finalize_preview_files(
    *,
    project_name: str,
    selected_stack: Mapping[str, Any],
    project_kind: Mapping[str, Any],
    required_inputs: Sequence[Mapping[str, Any]] | None = None,
    template_family: str = "",
    custom_manifest: Sequence[Mapping[str, Any]] | None = None,
    raw_files: Any = None,
) -> list[dict[str, str]]:
    standard_files = _build_standard_files(
        project_name,
        selected_stack,
        project_kind,
        required_inputs=required_inputs,
        template_family=template_family,
    )
    custom_template_files = _build_custom_template_files(
        custom_manifest or [],
        project_name,
        selected_stack,
        project_kind,
    )
    existing_files = _normalize_preview_files(raw_files)

    merged_files = _merge_file_entries(standard_files, custom_template_files)
    merged_files = _merge_file_entries(merged_files, existing_files)
    completed_files = _ensure_minimum_project_files(
        merged_files,
        project_name,
        selected_stack,
        project_kind,
        required_inputs=required_inputs,
        template_family=template_family,
    )
    repaired_files = _repair_runtime_contract(
        completed_files,
        project_name,
        selected_stack,
        project_kind,
        required_inputs=required_inputs,
        template_family=template_family,
    )
    return validate_generated_files(repaired_files)


def build_preview_file_tree(
    files: Sequence[Mapping[str, Any]],
    *,
    include_env_example: bool,
) -> str:
    file_paths = [str(file_entry.get("path") or "").strip() for file_entry in files]
    all_paths = [path for path in file_paths if path]
    if include_env_example and ".env.example" not in all_paths:
        all_paths.append(".env.example")
    return build_file_tree_from_paths(all_paths)


def assemble_complete_preview_files(
    preview: Mapping[str, Any],
    *,
    selected_stack: Mapping[str, Any],
    project_kind: Mapping[str, Any],
) -> tuple[list[dict[str, str]], list[str]]:
    base_files = validate_generated_files(_normalize_preview_files(preview.get("files")))
    actual_paths = [entry["path"] for entry in base_files]
    bundle_info = {
        "actualFileTree": build_file_tree_from_paths(actual_paths + list(SYSTEM_FILENAMES)),
    }
    required_docs = build_required_docs(dict(preview), bundle_info)

    merged = {entry["path"]: entry["content"] for entry in base_files}
    injected_paths: list[str] = []
    for doc_name, content in required_docs.items():
        if not str(merged.get(doc_name, "")).strip():
            injected_paths.append(doc_name)
        merged[doc_name] = content

    complete_files = validate_generated_files(
        [{"path": path, "content": content} for path, content in merged.items()]
    )
    return complete_files, sorted(set(injected_paths))


def required_preview_paths(
    selected_stack: Mapping[str, Any],
    project_kind: Mapping[str, Any],
    template_family: str = "",
) -> set[str]:
    paths = set(_required_runtime_paths(selected_stack, project_kind, template_family=template_family))
    paths.update(SYSTEM_FILENAMES)
    return paths


def _build_standard_files(
    project_name: str,
    selected_stack: Mapping[str, Any],
    project_kind: Mapping[str, Any],
    *,
    required_inputs: Sequence[Mapping[str, Any]] | None = None,
    template_family: str = "",
) -> list[dict[str, str]]:
    if template_family == "puzzle-game":
        files = _build_puzzle_game_files(project_name)
        return [{"path": path, "content": content} for path, content in files.items()]

    files: dict[str, str] = {}
    if project_kind["isFullStack"]:
        if project_kind["hasFrontend"]:
            files.update(
                _build_frontend_files(
                    str(selected_stack.get("frontend") or "React"),
                    project_name,
                    "frontend",
                )
            )
        if project_kind["hasBackend"]:
            files.update(
                _build_backend_files(
                    selected_stack,
                    project_name,
                    "backend",
                    required_inputs=required_inputs,
                )
            )
        files.update(_build_root_scripts(selected_stack, project_kind))
    elif project_kind["hasBackend"]:
        files.update(_build_backend_files(selected_stack, project_name, "", required_inputs=required_inputs))
        files.update(_build_root_scripts(selected_stack, project_kind))
    else:
        files.update(
            _build_frontend_files(
                str(selected_stack.get("frontend") or "React"),
                project_name,
                "",
            )
        )
        files.update(_build_root_scripts(selected_stack, project_kind))
    return [{"path": path, "content": content} for path, content in files.items()]


def _build_custom_template_files(
    manifest: Sequence[Mapping[str, Any]],
    project_name: str,
    selected_stack: Mapping[str, Any],
    project_kind: Mapping[str, Any],
) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    for item in list(manifest)[:MAX_CUSTOM_TEMPLATE_FILES]:
        path = _clean_relative_path(item.get("path"))
        purpose = str(item.get("purpose") or "").strip()
        if not path or not purpose:
            continue
        content = _build_custom_template_content(
            path,
            purpose,
            project_name,
            selected_stack,
            project_kind,
        )
        files.append({"path": path, "content": _trim_content_lines(content)})
    return files


def _build_custom_template_content(
    path: str,
    purpose: str,
    project_name: str,
    selected_stack: Mapping[str, Any],
    project_kind: Mapping[str, Any],
) -> str:
    del selected_stack, project_kind
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

export default function {_safe_component_name(stem)}() {{
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
        return f"""export default function {_safe_component_name(stem)}() {{
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
def read_{_safe_python_name(stem)}() -> dict[str, str]:
    return {{
        "message": "{purpose}",
        "project": "{project_name}",
    }}
"""
        if "schema" in path or "/schemas/" in path:
            return f"""from pydantic import BaseModel


class {_safe_component_name(stem)}(BaseModel):
    name: str
    description: str = "{purpose}"
"""
        if "model" in path or "/models/" in path:
            return f"""from dataclasses import dataclass


@dataclass
class {_safe_component_name(stem)}:
    name: str
    status: str = "ready"
"""
        return f"""def {_safe_python_name(stem)}_summary() -> dict[str, str]:
    return {{
        "name": "{pretty_name}",
        "purpose": "{purpose}",
        "project": "{project_name}",
    }}
"""

    if extension in {".js", ".mjs"}:
        if "service" in path.lower():
            return f"""export function get{_safe_component_name(stem)}Summary() {{
  return {{
    project: "{project_name}",
    purpose: "{purpose}"
  }};
}}
"""
        if "controller" in path.lower():
            return f"""export function {_safe_js_name(stem)}(_req, res) {{
  res.json({{
    project: "{project_name}",
    purpose: "{purpose}"
  }});
}}
"""
        return f"""export const {_safe_js_name(stem)} = {{
  project: "{project_name}",
  purpose: "{purpose}"
}};
"""

    if extension == ".java":
        class_name = _safe_component_name(stem)
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


def _ensure_minimum_project_files(
    files: Sequence[Mapping[str, str]],
    project_name: str,
    selected_stack: Mapping[str, Any],
    project_kind: Mapping[str, Any],
    *,
    required_inputs: Sequence[Mapping[str, Any]] | None = None,
    template_family: str = "",
) -> list[dict[str, str]]:
    merged = {str(entry["path"]): str(entry["content"]) for entry in files}
    if template_family == "puzzle-game":
        for path, content in _build_puzzle_game_files(project_name).items():
            merged.setdefault(path, content)
    else:
        for path, content in _build_root_scripts(selected_stack, project_kind).items():
            merged.setdefault(path, content)

    if template_family == "puzzle-game":
        minimum_files = 7
    elif project_kind["isFullStack"]:
        for path, content in _build_frontend_files(
            str(selected_stack.get("frontend") or "React"),
            project_name,
            "frontend",
        ).items():
            merged.setdefault(path, content)
        for path, content in _build_backend_files(
            selected_stack,
            project_name,
            "backend",
            required_inputs=required_inputs,
        ).items():
            merged.setdefault(path, content)
    elif project_kind["hasBackend"]:
        for path, content in _build_backend_files(selected_stack, project_name, "", required_inputs=required_inputs).items():
            merged.setdefault(path, content)
    else:
        for path, content in _build_frontend_files(
            str(selected_stack.get("frontend") or "React"),
            project_name,
            "",
        ).items():
            merged.setdefault(path, content)

    filler_index = 1
    minimum_files = max(minimum_files if template_family == "puzzle-game" else 0, int(project_kind.get("minimumFiles") or 0))
    while len(merged) < minimum_files:
        filler_path = f"notes/starter-note-{filler_index}.md"
        merged.setdefault(
            filler_path,
            f"# Starter Note {filler_index}\n\nThis file preserves the complete minimum project structure while you continue iterating.\n",
        )
        filler_index += 1

    return [{"path": path, "content": content} for path, content in merged.items()]


def _repair_runtime_contract(
    files: Sequence[Mapping[str, str]],
    project_name: str,
    selected_stack: Mapping[str, Any],
    project_kind: Mapping[str, Any],
    *,
    required_inputs: Sequence[Mapping[str, Any]] | None = None,
    template_family: str = "",
) -> list[dict[str, str]]:
    standard_map = {
        item["path"]: item["content"]
        for item in _build_standard_files(
            project_name,
            selected_stack,
            project_kind,
            required_inputs=required_inputs,
            template_family=template_family,
        )
    }
    merged = {str(entry["path"]): str(entry["content"]) for entry in files}

    for protected_path in _protected_runtime_paths(selected_stack, project_kind, template_family=template_family):
        template_content = standard_map.get(protected_path)
        if template_content is not None:
            merged[protected_path] = template_content

    for required_path in _required_runtime_paths(selected_stack, project_kind, template_family=template_family):
        template_content = standard_map.get(required_path)
        if template_content is None:
            continue
        if not str(merged.get(required_path, "")).strip():
            merged[required_path] = template_content

    for path, content in list(merged.items()):
        if not str(content).strip():
            replacement = standard_map.get(path) or _build_safe_fallback_content(
                path,
                project_name,
            )
            merged[path] = replacement

    for path, content in list(merged.items()):
        if not path.endswith(".py"):
            continue
        if _python_compiles(content):
            continue
        merged[path] = standard_map.get(path) or _build_safe_fallback_content(path, project_name)

    for package_json_path in _package_json_paths(selected_stack, project_kind, template_family=template_family):
        if package_json_path not in merged or not _valid_package_json(
            merged[package_json_path],
            _expected_package_scripts(package_json_path, selected_stack, project_kind),
        ):
            template = standard_map.get(package_json_path)
            if template is not None:
                merged[package_json_path] = template

    for entry_path in _entry_validation_paths(selected_stack, project_kind, template_family=template_family):
        template = standard_map.get(entry_path)
        content = str(merged.get(entry_path, ""))
        if template is None:
            continue
        if not content.strip() or not _valid_entry_file(entry_path, content):
            merged[entry_path] = template

    if project_kind["hasBackend"]:
        for endpoint_path in _backend_endpoint_paths(selected_stack, project_kind):
            template = standard_map.get(endpoint_path)
            if template is None:
                continue
            content = str(merged.get(endpoint_path, ""))
            if not content.strip() or not _valid_backend_endpoint_file(endpoint_path, content):
                merged[endpoint_path] = template

    if project_kind["hasFrontend"]:
        for page_path in _frontend_page_paths(selected_stack, project_kind, template_family=template_family):
            template = standard_map.get(page_path)
            if template is None:
                continue
            if not str(merged.get(page_path, "")).strip():
                merged[page_path] = template

    return [{"path": path, "content": content} for path, content in merged.items()]


def _build_backend_files(
    selected_stack: Mapping[str, Any],
    project_name: str,
    prefix: str,
    *,
    required_inputs: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, str]:
    backend = str(selected_stack.get("backend") or "FastAPI")
    if backend in {"FastAPI", "Flask"}:
        return _build_fastapi_backend_files(project_name, prefix, required_inputs=required_inputs)
    if backend in {"Express", "NestJS"}:
        return _build_express_backend_files(project_name, prefix)
    if backend == "Spring Boot":
        return _build_spring_backend_files(project_name, prefix)
    return _build_fastapi_backend_files(project_name, prefix, required_inputs=required_inputs)


def _build_frontend_files(frontend: str, project_name: str, prefix: str) -> dict[str, str]:
    if frontend in {"React", "Next.js", "Vue"}:
        return _build_react_frontend_files(project_name, prefix)
    return _build_vanilla_frontend_files(project_name, prefix)


def _build_puzzle_game_files(project_name: str) -> dict[str, str]:
    return {
        "index.html": f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{project_name}</title>
    <link rel="stylesheet" href="style.css" />
  </head>
  <body>
    <main class="app-shell">
      <section class="hero">
        <p class="eyebrow">Project Agent Starter</p>
        <h1>{project_name}</h1>
        <p class="hero-copy">
          Slide the numbered tiles into order. Click a tile next to the empty space to move it.
        </p>
      </section>

      <section class="panel controls">
        <button id="shuffleButton" type="button">Shuffle / Start</button>
        <button id="resetButton" type="button">Reset</button>
        <p id="moveCounter">Moves: 0</p>
        <p id="statusMessage">Arrange the board in order from 1 to 8.</p>
      </section>

      <section class="panel board-panel">
        <div id="puzzleBoard" class="puzzle-board" aria-label="Sliding puzzle board"></div>
      </section>

      <section class="panel instructions">
        <h2>How to play</h2>
        <ol>
          <li>Click <strong>Shuffle / Start</strong> to scramble the board.</li>
          <li>Move any tile touching the empty space.</li>
          <li>Put the numbers back in order to win.</li>
        </ol>
      </section>
    </main>
    <script src="script.js"></script>
  </body>
</html>
""",
        "style.css": """:root {
  font-family: "Segoe UI", Arial, sans-serif;
  color: #10243b;
  background: linear-gradient(180deg, #eef4ff 0%, #f8fbff 100%);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
}

.app-shell {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 20px 56px;
}

.hero,
.panel {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(16, 36, 59, 0.08);
  border-radius: 22px;
  box-shadow: 0 18px 40px rgba(16, 36, 59, 0.08);
}

.hero {
  padding: 28px;
  margin-bottom: 20px;
}

.eyebrow {
  margin: 0 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.78rem;
  color: #58708a;
}

.hero h1 {
  margin: 0 0 12px;
  font-size: clamp(2rem, 4vw, 3.2rem);
}

.hero-copy,
#statusMessage,
#moveCounter {
  margin: 0;
  color: #3f566d;
}

.controls,
.instructions {
  padding: 20px 24px;
  margin-bottom: 20px;
}

.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 16px;
  align-items: center;
}

.controls button {
  border: none;
  border-radius: 999px;
  padding: 12px 18px;
  font-weight: 700;
  background: #155eef;
  color: white;
  cursor: pointer;
}

.controls button:last-of-type {
  background: #e6eef9;
  color: #10243b;
}

.board-panel {
  padding: 24px;
  margin-bottom: 20px;
}

.puzzle-board {
  width: min(92vw, 420px);
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.tile,
.empty-tile {
  aspect-ratio: 1 / 1;
  border-radius: 18px;
  display: grid;
  place-items: center;
  font-size: clamp(1.4rem, 5vw, 2.2rem);
  font-weight: 800;
}

.tile {
  border: none;
  cursor: pointer;
  background: linear-gradient(135deg, #155eef 0%, #14b8a6 100%);
  color: white;
  box-shadow: 0 12px 24px rgba(21, 94, 239, 0.22);
}

.tile:hover {
  transform: translateY(-1px);
}

.empty-tile {
  border: 2px dashed rgba(16, 36, 59, 0.18);
  background: rgba(16, 36, 59, 0.04);
}

.instructions h2 {
  margin-top: 0;
}

.instructions ol {
  margin: 0;
  padding-left: 20px;
  color: #3f566d;
}
""",
        "script.js": """const GOAL_STATE = [1, 2, 3, 4, 5, 6, 7, 8, 0];
let boardState = [...GOAL_STATE];
let moveCount = 0;

const boardElement = document.getElementById("puzzleBoard");
const moveCounter = document.getElementById("moveCounter");
const statusMessage = document.getElementById("statusMessage");
const shuffleButton = document.getElementById("shuffleButton");
const resetButton = document.getElementById("resetButton");

shuffleButton.addEventListener("click", startGame);
resetButton.addEventListener("click", resetBoard);

renderBoard();

function startGame() {
  boardState = shuffleBoard([...GOAL_STATE]);
  moveCount = 0;
  updateMoveCounter();
  statusMessage.textContent = "Game started. Put the numbers back in order.";
  renderBoard();
}

function resetBoard() {
  boardState = [...GOAL_STATE];
  moveCount = 0;
  updateMoveCounter();
  statusMessage.textContent = "Board reset. Click Shuffle / Start to play again.";
  renderBoard();
}

function shuffleBoard(state) {
  const shuffled = [...state];
  do {
    for (let index = shuffled.length - 1; index > 0; index -= 1) {
      const swapIndex = Math.floor(Math.random() * (index + 1));
      [shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex], shuffled[index]];
    }
  } while (!isSolvable(shuffled) || isSolved(shuffled));
  return shuffled;
}

function isSolvable(state) {
  let inversions = 0;
  const filtered = state.filter((value) => value !== 0);
  for (let left = 0; left < filtered.length; left += 1) {
    for (let right = left + 1; right < filtered.length; right += 1) {
      if (filtered[left] > filtered[right]) {
        inversions += 1;
      }
    }
  }
  return inversions % 2 === 0;
}

function isSolved(state) {
  return state.every((value, index) => value === GOAL_STATE[index]);
}

function renderBoard() {
  boardElement.replaceChildren();

  boardState.forEach((value, index) => {
    if (value === 0) {
      const emptyTile = document.createElement("div");
      emptyTile.className = "empty-tile";
      emptyTile.setAttribute("aria-hidden", "true");
      boardElement.appendChild(emptyTile);
      return;
    }

    const button = document.createElement("button");
    button.type = "button";
    button.className = "tile";
    button.textContent = String(value);
    button.addEventListener("click", () => attemptMove(index));
    boardElement.appendChild(button);
  });
}

function attemptMove(index) {
  const emptyIndex = boardState.indexOf(0);
  const validMoves = getAdjacentIndexes(emptyIndex);
  if (!validMoves.includes(index)) {
    statusMessage.textContent = "That tile cannot move. Choose a tile next to the empty space.";
    return;
  }

  [boardState[index], boardState[emptyIndex]] = [boardState[emptyIndex], boardState[index]];
  moveCount += 1;
  updateMoveCounter();
  renderBoard();

  if (isSolved(boardState)) {
    statusMessage.textContent = `You solved the puzzle in ${moveCount} moves. Great job!`;
    return;
  }

  statusMessage.textContent = "Nice move. Keep going!";
}

function getAdjacentIndexes(index) {
  const row = Math.floor(index / 3);
  const column = index % 3;
  const adjacent = [];

  if (row > 0) adjacent.push(index - 3);
  if (row < 2) adjacent.push(index + 3);
  if (column > 0) adjacent.push(index - 1);
  if (column < 2) adjacent.push(index + 1);

  return adjacent;
}

function updateMoveCounter() {
  moveCounter.textContent = `Moves: ${moveCount}`;
}
""",
        "setup.bat": """@echo off
echo No setup is required for this static puzzle game.
echo Open index.html directly or run run.bat.
""",
        "setup.sh": """#!/usr/bin/env bash
echo "No setup is required for this static puzzle game."
echo "Open index.html directly or run ./run.sh."
""",
        "run.bat": """@echo off
start "" "%~dp0index.html"
""",
        "run.sh": """#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Serving the puzzle game at http://127.0.0.1:4173"
cd "$SCRIPT_DIR"
python3 -m http.server 4173
""",
    }


def _build_fastapi_runtime_setting_lines(
    required_inputs: Sequence[Mapping[str, Any]] | None,
) -> str:
    normalized_inputs = list(required_inputs or [])
    lines = [
        '        self.app_env = get_env("APP_ENV", default="development")',
        '        self.port = int(get_env("PORT", default="8000") or "8000")',
    ]
    seen_names = {"APP_ENV", "PORT"}
    for item in normalized_inputs:
        name = str(item.get("name") or "").strip()
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        example = str(item.get("example") or "").strip().replace("\\", "\\\\").replace('"', '\\"')
        required = bool(item.get("required", True))
        attribute_name = _safe_python_name(name)
        if required:
            line = f'        self.{attribute_name} = get_env("{name}", required=True, example="{example}")'
        else:
            default = example or ""
            line = f'        self.{attribute_name} = get_env("{name}", default="{default}", example="{example}")'
        lines.append(line)
    return "\n".join(lines)


def _build_fastapi_backend_files(
    project_name: str,
    prefix: str,
    *,
    required_inputs: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, str]:
    app_prefix = _prefixed(prefix, "app")
    runtime_env_lines = _build_fastapi_runtime_setting_lines(required_inputs)
    files = {
        _prefixed(prefix, "requirements.txt"): "\n".join(
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
        _prefixed(app_prefix, "__init__.py"): '"""Application package for the generated backend."""\n',
        _prefixed(app_prefix, "main.py"): """from fastapi import FastAPI
import uvicorn

from app.config import settings
from app.routers import health, items


app = FastAPI(title="Project Agent Starter API")
app.include_router(health.router)
app.include_router(items.router, prefix="/api/items", tags=["items"])


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "status": "ok",
        "message": "Project is running",
        "environment": settings.app_env,
    }


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)
""",
        _prefixed(app_prefix, "routers/__init__.py"): '"""Router package for generated API endpoints."""\n',
        _prefixed(app_prefix, "routers/health.py"): """from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok", message="Project is running")
""",
        _prefixed(app_prefix, "routers/items.py"): """from fastapi import APIRouter

from app.schemas.item import Item
from app.services.item_service import list_items

router = APIRouter()


@router.get("/", response_model=list[Item])
def get_items() -> list[Item]:
    return list_items()
""",
        _prefixed(app_prefix, "services/__init__.py"): '"""Service package for generated backend logic."""\n',
        _prefixed(app_prefix, "services/app_service.py"): f"""def get_app_summary() -> str:
    return "{project_name} includes routes, services, schemas, and configuration for quick iteration."
""",
        _prefixed(app_prefix, "services/item_service.py"): """from app.schemas.item import Item


def list_items() -> list[Item]:
    return [
        Item(id=1, name="Starter task", status="ready"),
        Item(id=2, name="Next iteration", status="planned"),
    ]
""",
        _prefixed(app_prefix, "models/__init__.py"): '"""Model package for generated backend persistence."""\n',
        _prefixed(app_prefix, "models/base.py"): """from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
""",
        _prefixed(app_prefix, "models/item.py"): """from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ItemModel(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40), default="ready")
""",
        _prefixed(app_prefix, "schemas/__init__.py"): '"""Schema package for generated backend payloads."""\n',
        _prefixed(app_prefix, "schemas/health.py"): """from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    message: str
""",
        _prefixed(app_prefix, "schemas/item.py"): """from pydantic import BaseModel


class Item(BaseModel):
    id: int
    name: str
    status: str
""",
        _prefixed(app_prefix, "database.py"): """from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
""",
        _prefixed(app_prefix, "config.py"): f"""from pathlib import Path
import os

from dotenv import load_dotenv


APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
PARENT_PROJECT_DIR = PROJECT_DIR.parent

for candidate in (PROJECT_DIR / ".env", PARENT_PROJECT_DIR / ".env"):
    if candidate.exists():
        load_dotenv(candidate, override=False)


def get_env(name: str, default: str | None = None, required: bool = False, example: str = "") -> str:
    value = os.getenv(name)
    if value:
        return value
    if not required:
        return default or ""
    prompt = f"Enter {{name}}"
    if example:
        prompt += f" (example: {{example}})"
    prompt += ": "
    return input(prompt).strip()


class Settings:
    def __init__(self) -> None:
{runtime_env_lines}


settings = Settings()
""",
    }
    files.update(_build_backend_subproject_scripts("FastAPI", prefix))
    return files


def _build_express_backend_files(project_name: str, prefix: str) -> dict[str, str]:
    files = {
        _prefixed(prefix, "package.json"): json.dumps(
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
        _prefixed(prefix, "server.js"): f"""import cors from "cors";
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
        _prefixed(prefix, "src/routes/index.js"): """import { Router } from "express";
import { getStatus } from "../controllers/appController.js";

const router = Router();
router.get("/", getStatus);

export default router;
""",
        _prefixed(prefix, "src/routes/items.js"): """import { Router } from "express";
import { listItems } from "../controllers/itemController.js";

const router = Router();
router.get("/", listItems);

export default router;
""",
        _prefixed(prefix, "src/controllers/appController.js"): """export function getStatus(_req, res) {
  res.json({ status: "ok", message: "Project is running" });
}
""",
        _prefixed(prefix, "src/controllers/itemController.js"): """import { getItems } from "../services/itemService.js";

export function listItems(_req, res) {
  res.json(getItems());
}
""",
        _prefixed(prefix, "src/services/appService.js"): f"""export function getAppSummary() {{
  return "{project_name} includes routes, controllers, services, and starter configuration.";
}}
""",
        _prefixed(prefix, "src/services/itemService.js"): """export function getItems() {
  return [
    { id: 1, name: "Starter task", status: "ready" },
    { id: 2, name: "Next iteration", status: "planned" }
  ];
}
""",
        _prefixed(prefix, "src/models/itemModel.js"): """export const itemShape = {
  id: "number",
  name: "string",
  status: "string"
};
""",
    }
    files.update(_build_backend_subproject_scripts("Express", prefix))
    return files


def _build_react_frontend_files(project_name: str, prefix: str) -> dict[str, str]:
    files = {
        _prefixed(prefix, "package.json"): json.dumps(
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
        _prefixed(prefix, "index.html"): """<!doctype html>
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
        _prefixed(prefix, "vite.config.js"): """import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173
  }
});
""",
        _prefixed(prefix, "src/main.jsx"): """import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
""",
        _prefixed(prefix, "src/App.jsx"): f"""import AppShell from "./components/AppShell";
import HomePage from "./pages/HomePage";

export default function App() {{
  return (
    <AppShell title="{project_name}">
      <HomePage />
    </AppShell>
  );
}}
""",
        _prefixed(prefix, "src/components/AppShell.jsx"): """export default function AppShell({ title, children }) {
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
        _prefixed(prefix, "src/pages/HomePage.jsx"): """import { getProjectHealth } from "../services/api";

export default function HomePage() {
  const projectHealth = getProjectHealth();

  return (
    <section className="card">
      <h2>Starter Overview</h2>
      <p>This 100% runnable starter project is ready for your first feature slice.</p>
      <p>API health source: {projectHealth}</p>
    </section>
  );
}
""",
        _prefixed(prefix, "src/services/api.js"): """export function getProjectHealth() {
  return import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
}
""",
        _prefixed(prefix, "src/styles.css"): """:root {
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
    files.update(_build_frontend_subproject_scripts(prefix))
    return files


def _build_vanilla_frontend_files(project_name: str, prefix: str) -> dict[str, str]:
    files = {
        _prefixed(prefix, "package.json"): json.dumps(
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
        _prefixed(prefix, "index.html"): """<!doctype html>
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
        _prefixed(prefix, "vite.config.js"): """import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173
  }
});
""",
        _prefixed(prefix, "src/main.js"): f"""import {{ renderHomePage }} from "./views/home.js";
import "./styles.css";

document.querySelector("#app").innerHTML = renderHomePage("{project_name}");
""",
        _prefixed(prefix, "src/views/home.js"): """export function renderHomePage(title) {
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
        _prefixed(prefix, "src/services/api.js"): """export function getApiBaseUrl() {
  return import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
}
""",
        _prefixed(prefix, "src/styles.css"): """body {
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
    files.update(_build_frontend_subproject_scripts(prefix))
    return files


def _build_spring_backend_files(project_name: str, prefix: str) -> dict[str, str]:
    java_base = _prefixed(prefix, "src/main/java/com/example/demo")
    resources_base = _prefixed(prefix, "src/main/resources")
    files = {
        _prefixed(prefix, "pom.xml"): """<project xmlns="http://maven.apache.org/POM/4.0.0"
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
        _prefixed(java_base, "Application.java"): """package com.example.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
    files.update(_build_backend_subproject_scripts("Spring Boot", prefix))
    return files
}
""",
        _prefixed(java_base, "controller/AppController.java"): """package com.example.demo.controller;

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
        return Map.of("status", "ok", "message", "Project is running");
    }
}
""",
        _prefixed(java_base, "service/AppService.java"): f"""package com.example.demo.service;

import org.springframework.stereotype.Service;

@Service
public class AppService {{
    public String status() {{
        return "Project is running";
    }}
}}
""",
        _prefixed(java_base, "model/AppModel.java"): """package com.example.demo.model;

public class AppModel {
    private Long id;
    private String name;

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
}
""",
        _prefixed(java_base, "repository/AppRepository.java"): """package com.example.demo.repository;

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
        _prefixed(resources_base, "application.properties"): """spring.application.name=demo
server.port=8080
""",
    }


def _build_root_scripts(
    selected_stack: Mapping[str, Any],
    project_kind: Mapping[str, Any],
) -> dict[str, str]:
    if project_kind["isFullStack"]:
        return _build_fullstack_scripts(selected_stack)
    if project_kind["hasBackend"]:
        backend = str(selected_stack.get("backend") or "FastAPI")
        if backend in {"FastAPI", "Flask"}:
            return _build_python_scripts(".")
        if backend in {"Express", "NestJS"}:
            return _build_node_scripts(".", "start")
        if backend == "Spring Boot":
            return _build_java_scripts(".")
    return _build_node_scripts(".", "dev")


def _build_fullstack_scripts(selected_stack: Mapping[str, Any]) -> dict[str, str]:
    backend_setup = ""
    backend_run_windows = "echo No backend runtime configured.\n"
    backend_run_unix = 'echo "No backend runtime configured."\n'
    backend = str(selected_stack.get("backend") or "")

    if backend in {"FastAPI", "Flask"}:
        backend_setup = (
            "if exist backend\\requirements.txt (\n"
            "  pushd backend\n"
            "  python -m venv .venv\n"
            "  call .venv\\Scripts\\python -m pip install --upgrade pip\n"
            "  call .venv\\Scripts\\pip install -r requirements.txt\n"
            "  popd\n"
            ")\n"
        )
        backend_run_windows = (
            'start "Backend" cmd /k "cd backend && call run.bat"\n'
        )
        backend_run_unix = '(cd backend && ./run.sh) &\n'
    elif backend in {"Express", "NestJS"}:
        backend_setup = (
            "if exist backend\\package.json (\n"
            "  pushd backend\n"
            "  call npm install\n"
            "  popd\n"
            ")\n"
        )
        backend_run_windows = 'start "Backend" cmd /k "cd backend && npm start"\n'
        backend_run_unix = '(cd backend && npm start) &\n'
    elif backend == "Spring Boot":
        backend_setup = (
            "where mvn >nul 2>nul && (\n"
            "  pushd backend\n"
            "  call mvn install\n"
            "  popd\n"
            ") || echo Maven not found. Skipping backend install.\n"
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
  (
    cd backend
    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
  )
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


def _build_python_scripts(target_dir: str) -> dict[str, str]:
    del target_dir
    return {
        "setup.bat": """@echo off
setlocal
python -m venv .venv
call .venv\\Scripts\\python -m pip install --upgrade pip
call .venv\\Scripts\\pip install -r requirements.txt
echo Setup complete.
""",
        "setup.sh": """#!/usr/bin/env bash
set -e
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo "Setup complete."
""",
        "run.bat": """@echo off
setlocal
echo Starting Project...
if not exist .env if exist .env.example copy .env.example .env >nul
if not exist .venv python -m venv .venv
call .venv\\Scripts\\python -m pip install --upgrade pip
call .venv\\Scripts\\pip install -r requirements.txt
call .venv\\Scripts\\python app/main.py
""",
        "run.sh": """#!/usr/bin/env bash
set -e
echo "Starting Project..."
if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
fi
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app/main.py
""",
    }


def _build_node_scripts(target_dir: str, script_name: str) -> dict[str, str]:
    directory_prefix = "" if target_dir in {"", "."} else f"{target_dir}/"
    windows_prefix = "" if target_dir in {"", "."} else f"{target_dir}\\"
    run_script = "npm start" if script_name == "start" else "npm run dev"
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
call {run_script}
popd
""",
        "run.sh": f"""#!/usr/bin/env bash
set -e
(cd {directory_prefix or "."} && {run_script})
""",
    }


def _build_backend_subproject_scripts(backend: str, prefix: str) -> dict[str, str]:
    if not prefix:
        return {}
    if backend in {"FastAPI", "Flask"}:
        return {
            _prefixed(prefix, "setup.bat"): """@echo off
setlocal
pushd "%~dp0"
python -m venv .venv
call .venv\\Scripts\\python -m pip install --upgrade pip
call .venv\\Scripts\\pip install -r requirements.txt
popd
echo Backend setup complete.
""",
            _prefixed(prefix, "run.bat"): """@echo off
setlocal
pushd "%~dp0"
echo Starting Project...
if not exist ..\\.env if exist ..\\.env.example copy ..\\.env.example ..\\.env >nul
if not exist .venv python -m venv .venv
call .venv\\Scripts\\python -m pip install --upgrade pip
call .venv\\Scripts\\pip install -r requirements.txt
call .venv\\Scripts\\python app/main.py
popd
""",
            _prefixed(prefix, "setup.sh"): """#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo "Backend setup complete."
""",
            _prefixed(prefix, "run.sh"): """#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
echo "Starting Project..."
if [ ! -f ../.env ] && [ -f ../.env.example ]; then
  cp ../.env.example ../.env
fi
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app/main.py
""",
        }
    if backend in {"Express", "NestJS"}:
        return {
            _prefixed(prefix, "setup.bat"): """@echo off
setlocal
pushd "%~dp0"
call npm install
popd
echo Backend setup complete.
""",
            _prefixed(prefix, "run.bat"): """@echo off
setlocal
pushd "%~dp0"
call npm start
popd
""",
            _prefixed(prefix, "setup.sh"): """#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
npm install
echo "Backend setup complete."
""",
            _prefixed(prefix, "run.sh"): """#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
npm start
""",
        }
    if backend == "Spring Boot":
        return {
            _prefixed(prefix, "setup.bat"): """@echo off
setlocal
pushd "%~dp0"
where mvn >nul 2>nul && call mvn install || echo Maven not found. Skipping install.
popd
""",
            _prefixed(prefix, "run.bat"): """@echo off
setlocal
pushd "%~dp0"
call mvn spring-boot:run
popd
""",
            _prefixed(prefix, "setup.sh"): """#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
if command -v mvn >/dev/null 2>&1; then
  mvn install
else
  echo "Maven not found. Skipping install."
fi
""",
            _prefixed(prefix, "run.sh"): """#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
mvn spring-boot:run
""",
        }
    return {}


def _build_frontend_subproject_scripts(prefix: str) -> dict[str, str]:
    if not prefix:
        return {}
    return {
        _prefixed(prefix, "setup.bat"): """@echo off
setlocal
pushd "%~dp0"
call npm install
popd
echo Frontend setup complete.
""",
        _prefixed(prefix, "run.bat"): """@echo off
setlocal
pushd "%~dp0"
call npm run dev
popd
""",
        _prefixed(prefix, "setup.sh"): """#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
npm install
echo "Frontend setup complete."
""",
        _prefixed(prefix, "run.sh"): """#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
npm run dev
""",
    }


def _protected_runtime_paths(
    selected_stack: Mapping[str, Any],
    project_kind: Mapping[str, Any],
    *,
    template_family: str = "",
) -> set[str]:
    if template_family == "puzzle-game":
        return {"index.html", "style.css", "script.js", "setup.bat", "setup.sh", "run.bat", "run.sh"}

    paths: set[str] = {"setup.bat", "setup.sh", "run.bat", "run.sh"}
    backend_prefix = "backend/" if project_kind["isFullStack"] else ""
    frontend_prefix = "frontend/" if project_kind["isFullStack"] else ""

    if project_kind["isFullStack"]:
        paths.update(
            {
                f"{backend_prefix}setup.bat",
                f"{backend_prefix}setup.sh",
                f"{backend_prefix}run.bat",
                f"{backend_prefix}run.sh",
                f"{frontend_prefix}setup.bat",
                f"{frontend_prefix}setup.sh",
                f"{frontend_prefix}run.bat",
                f"{frontend_prefix}run.sh",
            }
        )

    if project_kind["hasBackend"]:
        backend = str(selected_stack.get("backend") or "FastAPI")
        if backend in {"FastAPI", "Flask"}:
            paths.update(
                {
                    f"{backend_prefix}requirements.txt",
                    f"{backend_prefix}app/main.py",
                    f"{backend_prefix}app/routers/health.py",
                    f"{backend_prefix}app/schemas/health.py",
                    f"{backend_prefix}app/config.py",
                    f"{backend_prefix}app/database.py",
                }
            )
        elif backend in {"Express", "NestJS"}:
            paths.update(
                {
                    f"{backend_prefix}package.json",
                    f"{backend_prefix}server.js",
                    f"{backend_prefix}src/routes/index.js",
                    f"{backend_prefix}src/controllers/appController.js",
                }
            )
        elif backend == "Spring Boot":
            paths.update(
                {
                    f"{backend_prefix}pom.xml",
                    f"{backend_prefix}src/main/java/com/example/demo/Application.java",
                    f"{backend_prefix}src/main/java/com/example/demo/controller/AppController.java",
                    f"{backend_prefix}src/main/resources/application.properties",
                }
            )

    if project_kind["hasFrontend"]:
        frontend = str(selected_stack.get("frontend") or "React")
        if frontend in {"React", "Next.js", "Vue"}:
            paths.update(
                {
                    f"{frontend_prefix}package.json",
                    f"{frontend_prefix}index.html",
                    f"{frontend_prefix}vite.config.js",
                    f"{frontend_prefix}src/main.jsx",
                    f"{frontend_prefix}src/App.jsx",
                    f"{frontend_prefix}src/pages/HomePage.jsx",
                }
            )
        else:
            paths.update(
                {
                    f"{frontend_prefix}package.json",
                    f"{frontend_prefix}index.html",
                    f"{frontend_prefix}vite.config.js",
                    f"{frontend_prefix}src/main.js",
                    f"{frontend_prefix}src/views/home.js",
                }
            )

    return paths


def _required_runtime_paths(
    selected_stack: Mapping[str, Any],
    project_kind: Mapping[str, Any],
    *,
    template_family: str = "",
) -> set[str]:
    return set(_protected_runtime_paths(selected_stack, project_kind, template_family=template_family))


def _package_json_paths(
    selected_stack: Mapping[str, Any],
    project_kind: Mapping[str, Any],
    *,
    template_family: str = "",
) -> list[str]:
    if template_family == "puzzle-game":
        return []
    paths: list[str] = []
    backend_prefix = "backend/" if project_kind["isFullStack"] else ""
    frontend_prefix = "frontend/" if project_kind["isFullStack"] else ""
    if project_kind["hasBackend"] and str(selected_stack.get("backend") or "") in {"Express", "NestJS"}:
        paths.append(f"{backend_prefix}package.json")
    if project_kind["hasFrontend"]:
        paths.append(f"{frontend_prefix}package.json")
    return paths


def _expected_package_scripts(
    package_json_path: str,
    selected_stack: Mapping[str, Any],
    project_kind: Mapping[str, Any],
) -> set[str]:
    if package_json_path.endswith("backend/package.json") or (
        not project_kind["isFullStack"] and project_kind["hasBackend"]
    ):
        backend = str(selected_stack.get("backend") or "")
        if backend in {"Express", "NestJS"}:
            return {"start"}
    return {"dev"}


def _entry_validation_paths(
    selected_stack: Mapping[str, Any],
    project_kind: Mapping[str, Any],
    *,
    template_family: str = "",
) -> list[str]:
    if template_family == "puzzle-game":
        return ["index.html", "script.js"]
    paths: list[str] = []
    backend_prefix = "backend/" if project_kind["isFullStack"] else ""
    frontend_prefix = "frontend/" if project_kind["isFullStack"] else ""
    if project_kind["hasBackend"]:
        backend = str(selected_stack.get("backend") or "FastAPI")
        if backend in {"FastAPI", "Flask"}:
            paths.append(f"{backend_prefix}app/main.py")
        elif backend in {"Express", "NestJS"}:
            paths.append(f"{backend_prefix}server.js")
        elif backend == "Spring Boot":
            paths.append(f"{backend_prefix}src/main/java/com/example/demo/Application.java")
    if project_kind["hasFrontend"]:
        frontend = str(selected_stack.get("frontend") or "React")
        if frontend in {"React", "Next.js", "Vue"}:
            paths.extend([f"{frontend_prefix}src/main.jsx", f"{frontend_prefix}src/App.jsx"])
        else:
            paths.extend([f"{frontend_prefix}src/main.js", f"{frontend_prefix}index.html"])
    return paths


def _backend_endpoint_paths(
    selected_stack: Mapping[str, Any],
    project_kind: Mapping[str, Any],
) -> list[str]:
    if not project_kind["hasBackend"]:
        return []
    backend_prefix = "backend/" if project_kind["isFullStack"] else ""
    backend = str(selected_stack.get("backend") or "FastAPI")
    if backend in {"FastAPI", "Flask"}:
        return [f"{backend_prefix}app/main.py", f"{backend_prefix}app/routers/health.py"]
    if backend in {"Express", "NestJS"}:
        return [f"{backend_prefix}server.js", f"{backend_prefix}src/controllers/appController.js"]
    if backend == "Spring Boot":
        return [f"{backend_prefix}src/main/java/com/example/demo/controller/AppController.java"]
    return []


def _frontend_page_paths(
    selected_stack: Mapping[str, Any],
    project_kind: Mapping[str, Any],
    *,
    template_family: str = "",
) -> list[str]:
    if not project_kind["hasFrontend"]:
        return []
    if template_family == "puzzle-game":
        return ["index.html", "script.js", "style.css"]
    frontend_prefix = "frontend/" if project_kind["isFullStack"] else ""
    frontend = str(selected_stack.get("frontend") or "React")
    if frontend in {"React", "Next.js", "Vue"}:
        return [f"{frontend_prefix}src/App.jsx", f"{frontend_prefix}src/pages/HomePage.jsx"]
    return [f"{frontend_prefix}index.html", f"{frontend_prefix}src/views/home.js"]


def _valid_package_json(content: str, required_scripts: set[str]) -> bool:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, Mapping):
        return False
    scripts = payload.get("scripts")
    if not isinstance(scripts, Mapping):
        return False
    return required_scripts.issubset({str(key) for key in scripts.keys()})


def _valid_entry_file(path: str, content: str) -> bool:
    text = content.strip()
    if not text:
        return False
    lower = path.lower()
    if lower.endswith("app/main.py"):
        return "FastAPI" in text and "app = FastAPI" in text and '@app.get("/")' in text
    if lower.endswith("server.js"):
        return "express" in text and 'app.use("/", indexRouter)' in text and "app.listen" in text
    if lower.endswith("src/main.jsx"):
        return "ReactDOM.createRoot" in text and 'from "./App"' in text
    if lower.endswith("src/app.jsx"):
        return "export default function App" in text
    if lower.endswith("src/main.js"):
        return "renderHomePage" in text and 'querySelector("#app")' in text
    if lower.endswith("script.js"):
        return "GOAL_STATE" in text and "function startGame()" in text and "function attemptMove(index)" in text
    if lower.endswith("index.html"):
        return (
            '<div id="root"></div>' in text
            or '<div id="app"></div>' in text
            or 'id="puzzleBoard"' in text
        )
    if lower.endswith("application.java"):
        return "@SpringBootApplication" in text and "SpringApplication.run" in text
    return True


def _valid_backend_endpoint_file(path: str, content: str) -> bool:
    lower = path.lower()
    if lower.endswith("app/main.py"):
        return '"status": "ok"' in content and '"message": "Project is running"' in content
    if lower.endswith("routers/health.py"):
        return 'status="ok"' in content and 'message="Project is running"' in content
    if lower.endswith("server.js"):
        return 'app.use("/", indexRouter)' in content and "app.listen" in content
    if lower.endswith("appcontroller.js"):
        return 'status: "ok"' in content and 'message: "Project is running"' in content
    if lower.endswith("appcontroller.java"):
        return '"status", "ok"' in content and '"message", "Project is running"' in content
    return True


def _python_compiles(content: str) -> bool:
    try:
        compile(content, "<generated>", "exec")
    except SyntaxError:
        return False
    return True


def _build_safe_fallback_content(path: str, project_name: str) -> str:
    lower = path.lower()
    if lower.endswith(".py"):
        return f"""def generated_safe_summary() -> dict[str, str]:
    return {{"status": "ok", "message": "{project_name} safe fallback is loaded."}}
"""
    if lower.endswith(".jsx"):
        return f"""export default function SafeFallback() {{
  return <section className="card"><h2>{project_name}</h2><p>Safe fallback UI loaded.</p></section>;
}}
"""
    if lower.endswith(".js"):
        return f"""export const safeFallback = {{
  status: "ok",
  message: "{project_name} safe fallback loaded"
}};
"""
    if lower.endswith(".java"):
        return """package com.example.demo.service;

public class SafeFallback {
    public String summary() {
        return "Safe fallback loaded";
    }
}
"""
    return f"# Safe fallback\n\n{project_name} restored this file to preserve a runnable starter.\n"


def _build_java_scripts(target_dir: str) -> dict[str, str]:
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


def _normalize_preview_files(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    files: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        path = _clean_relative_path(item.get("path"))
        if not path:
            continue
        files.append(
            {
                "path": path,
                "content": _trim_content_lines(str(item.get("content") or ""), allow_long=True),
            }
        )
    return files


def _merge_file_entries(
    primary: Sequence[Mapping[str, str]],
    secondary: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for file_entry in primary:
        merged[str(file_entry["path"])] = {
            "path": str(file_entry["path"]),
            "content": str(file_entry["content"]),
        }
    for file_entry in secondary:
        merged[str(file_entry["path"])] = {
            "path": str(file_entry["path"]),
            "content": str(file_entry["content"]),
        }
    return list(merged.values())


def _clean_relative_path(value: Any) -> str:
    path = str(value or "").replace("\\", "/").strip().strip("/")
    if not path or path.startswith(".") or ".." in path.split("/"):
        return ""
    return path


def _trim_content_lines(content: str, allow_long: bool = False) -> str:
    if allow_long:
        return content
    lines = content.splitlines()
    if len(lines) <= MAX_CUSTOM_FILE_LINES:
        return content
    return "\n".join(lines[:MAX_CUSTOM_FILE_LINES]).rstrip() + "\n"


def _safe_component_name(value: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", value)
    return "".join(part.capitalize() for part in parts) or "GeneratedComponent"


def _safe_python_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()
    return cleaned or "generated_item"


def _safe_js_name(value: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", value)
    if not parts:
        return "generatedItem"
    head = parts[0].lower()
    tail = "".join(part.capitalize() for part in parts[1:])
    return head + tail


def _prefixed(prefix: str, path: str) -> str:
    base = Path(prefix) if prefix else Path()
    return (base / path).as_posix()
