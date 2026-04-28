from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AgentWorkflowContext:
    prompt: str
    generation_mode: str = "fast"
    requested_stack: dict[str, str] = field(default_factory=dict)
    final_requirements: str = ""
    generation_context: str = ""
    detected_user_choices: list[str] = field(default_factory=list)
    declared_project_type: str = ""
    project_category: str = ""
    direct_generation_allowed: bool = False
    migration_active: bool = False
    migration_requested: bool = False
    source_language: str = ""
    source_framework: str = ""
    source_project_type: str = ""
    source_architecture_pattern: str = ""
    target_language: str = ""
    target_framework: str = ""
    target_project_type: str = ""
    understanding: str = ""
    selected_stack: dict[str, str] = field(default_factory=dict)
    project_kind: dict[str, Any] = field(default_factory=dict)
    architecture: list[str] = field(default_factory=list)
    template_family: str = ""
    project_name: str = ""
    problem_statement: str = ""
    summary: str = ""
    assumptions: list[str] = field(default_factory=list)
    questions: list[dict[str, Any]] = field(default_factory=list)
    modules: list[dict[str, Any]] = field(default_factory=list)
    package_requirements: list[str] = field(default_factory=list)
    install_commands: list[str] = field(default_factory=list)
    run_commands: list[str] = field(default_factory=list)
    required_inputs: list[dict[str, Any]] = field(default_factory=list)
    env_variables: list[dict[str, Any]] = field(default_factory=list)
    custom_manifest: list[dict[str, str]] = field(default_factory=list)
    file_manifest: list[str] = field(default_factory=list)
    files: list[dict[str, str]] = field(default_factory=list)
    file_tree: str = ""
    preview: dict[str, Any] = field(default_factory=dict)
    validation_findings: list[str] = field(default_factory=list)
    repaired_files: list[str] = field(default_factory=list)
    recommended_ide: str = ""
    alternative_ide: str = ""
    runtime_tools: list[str] = field(default_factory=list)
    package_manager: str = ""
    migration_summary: dict[str, Any] = field(default_factory=dict)
    fallback_used: bool = False
    fallback_reason: str = ""
    ai_raw_plan: dict[str, Any] = field(default_factory=dict)
