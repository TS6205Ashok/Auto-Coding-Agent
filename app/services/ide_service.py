from __future__ import annotations

import os
import secrets
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen
from uuid import UUID, uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from app.services.file_service import ensure_within_directory, sanitize_relative_path, slugify


MAX_IDE_FILE_SIZE_BYTES = 512 * 1024
IDE_IMAGE_NAME = os.getenv("PROJECT_AGENT_IDE_IMAGE", "project-agent-ide")
IDE_CONTAINER_PORT = 8080
DEFAULT_IDE_HOST = os.getenv("PROJECT_AGENT_IDE_HOST", "127.0.0.1")
DEFAULT_OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
DOCKER_UNAVAILABLE_MESSAGE = "Docker Desktop is not running. Please start Docker and try again."
DEFAULT_IDLE_TIMEOUT_MINUTES = 45


@dataclass(slots=True)
class IdeInstance:
    project_id: str
    port: int
    container_id: str
    url: str
    status: str
    password: str
    last_accessed_at: float


IDE_REGISTRY: dict[str, IdeInstance] = {}


def validate_project_id(project_id: str) -> str:
    try:
        parsed = UUID(str(project_id), version=4)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid project id.") from exc
    return str(parsed)


def find_free_port(host: str = DEFAULT_IDE_HOST) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def project_dir_for(project_id: str, generated_projects_dir: Path) -> Path:
    safe_id = validate_project_id(project_id)
    base = generated_projects_dir.resolve()
    project_dir = (base / safe_id).resolve()
    if not ensure_within_directory(base, project_dir):
        raise ValueError("Project folder is outside generated_projects.")
    return project_dir


def materialize_preview_workspace(
    preview: dict[str, Any],
    generated_projects_dir: Path,
) -> dict[str, str]:
    generated_projects_dir.mkdir(parents=True, exist_ok=True)
    project_id = str(uuid4())
    project_dir = project_dir_for(project_id, generated_projects_dir)
    project_dir.mkdir(parents=True, exist_ok=False)
    for file_entry in preview.get("files", []):
        relative_path = sanitize_workspace_path(str(file_entry.get("path", "")))
        content = str(file_entry.get("content", ""))
        target_path = resolve_workspace_path(project_dir, relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
    return {
        "projectId": project_id,
        "projectPath": str(project_dir),
        "ideUrl": f"/open-ide/{project_id}",
        "workspaceDownloadUrl": f"/download/{project_id}",
    }


def sanitize_workspace_path(raw_path: str) -> Path:
    if not raw_path or not str(raw_path).strip():
        raise ValueError("File path is required.")
    raw = str(raw_path).replace("\\", "/").strip()
    candidate = PurePosixPath(raw)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise ValueError("Unsafe workspace path.")
    return sanitize_relative_path(raw)


def resolve_workspace_path(project_dir: Path, raw_path: str | Path) -> Path:
    relative_path = raw_path if isinstance(raw_path, Path) else sanitize_workspace_path(raw_path)
    target_path = (project_dir / relative_path).resolve()
    if not ensure_within_directory(project_dir.resolve(), target_path):
        raise ValueError("Path escapes generated project folder.")
    return target_path


def workspace_exists(project_id: str, generated_projects_dir: Path) -> bool:
    return project_dir_for(project_id, generated_projects_dir).is_dir()


def build_docker_run_command(project_id: str, project_dir: Path, port: int, password: str = "") -> list[str]:
    container_name = f"project-agent-ide-{project_id}"
    password = password or generate_ide_password()
    return [
        "docker",
        "run",
        "-d",
        "--name",
        container_name,
        "-p",
        f"127.0.0.1:{port}:{IDE_CONTAINER_PORT}",
        "-v",
        f"{str(project_dir)}:/workspace",
        "-e",
        f"PROJECT_AGENT_MODEL={os.getenv('PROJECT_AGENT_MODEL', 'qwen2.5-coder:latest')}",
        "-e",
        f"PROJECT_AGENT_FALLBACK_MODEL={os.getenv('PROJECT_AGENT_FALLBACK_MODEL', 'codellama:7b')}",
        "-e",
        f"PROJECT_AGENT_OLLAMA_URL={os.getenv('PROJECT_AGENT_OLLAMA_URL', DEFAULT_OLLAMA_URL)}",
        IDE_IMAGE_NAME,
    ]


def start_or_reuse_ide(project_id: str, generated_projects_dir: Path) -> IdeInstance:
    cleanup_idle_ide_instances()
    project_id = validate_project_id(project_id)
    project_dir = project_dir_for(project_id, generated_projects_dir)
    if not project_dir.is_dir():
        raise FileNotFoundError("Generated project not found.")

    existing = IDE_REGISTRY.get(project_id)
    if existing and _container_running(existing.container_id) and wait_for_ide_health(existing.url, timeout_seconds=2):
        existing.status = "running"
        existing.last_accessed_at = time.time()
        return existing

    container_name = f"project-agent-ide-{project_id}"
    if docker_container_exists(container_name):
        remove_container_by_name(container_name)

    port = find_free_port()
    password = generate_ide_password()
    command = build_docker_run_command(project_id, project_dir, port, password)
    result = run_docker_command(command[1:])
    if result.returncode != 0:
        raise RuntimeError(normalize_docker_error(result.stderr.strip() or result.stdout.strip()))
    container_id = result.stdout.strip()
    url = f"http://{DEFAULT_IDE_HOST}:{port}"
    instance = IdeInstance(
        project_id=project_id,
        port=port,
        container_id=container_id,
        url=url,
        status="starting",
        password=password,
        last_accessed_at=time.time(),
    )
    IDE_REGISTRY[project_id] = instance
    if not wait_for_ide_health(url):
        close_ide(project_id)
        raise RuntimeError("code-server did not become ready in time. Please check Docker logs and try again.")
    instance.status = "running"
    instance.last_accessed_at = time.time()
    return instance


def close_ide(project_id: str) -> bool:
    project_id = validate_project_id(project_id)
    instance = IDE_REGISTRY.pop(project_id, None)
    if not instance:
        return False
    try:
        run_docker_command(["stop", instance.container_id])
    except RuntimeError:
        pass
    try:
        run_docker_command(["rm", instance.container_id])
    except RuntimeError:
        pass
    return True


def ide_status(project_id: str) -> dict[str, Any]:
    cleanup_idle_ide_instances()
    project_id = validate_project_id(project_id)
    instance = IDE_REGISTRY.get(project_id)
    running = bool(instance and _container_running(instance.container_id))
    if instance:
        instance.status = "running" if running else "stopped"
        instance.last_accessed_at = time.time()
    return {
        "projectId": project_id,
        "running": running,
        "port": instance.port if instance else None,
        "containerId": instance.container_id if instance else "",
        "url": instance.url if instance else "",
        "status": instance.status if instance else "not_started",
        "password": instance.password if instance else "",
    }


def create_workspace_zip(project_id: str, generated_projects_dir: Path, zip_output_dir: Path) -> dict[str, str]:
    project_id = validate_project_id(project_id)
    project_dir = project_dir_for(project_id, generated_projects_dir)
    if not project_dir.is_dir():
        raise FileNotFoundError("Generated project not found.")
    zip_output_dir.mkdir(parents=True, exist_ok=True)
    zip_name = f"{project_id}.zip"
    zip_path = zip_output_dir / zip_name
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for file_path in sorted(project_dir.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, Path(project_id) / file_path.relative_to(project_dir))
    return {
        "filename": zip_name,
        "downloadUrl": f"/downloads/{zip_name}",
    }


def write_workspace_file(project_id: str, generated_projects_dir: Path, path: str, content: str) -> None:
    project_dir = project_dir_for(project_id, generated_projects_dir)
    target_path = resolve_workspace_path(project_dir, path)
    if len(content.encode("utf-8")) > MAX_IDE_FILE_SIZE_BYTES:
        raise ValueError("File is too large for IDE save.")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")


def rename_workspace_file(project_id: str, generated_projects_dir: Path, old_path: str, new_path: str) -> None:
    project_dir = project_dir_for(project_id, generated_projects_dir)
    source = resolve_workspace_path(project_dir, old_path)
    target = resolve_workspace_path(project_dir, new_path)
    if not source.is_file():
        raise FileNotFoundError("File not found.")
    target.parent.mkdir(parents=True, exist_ok=True)
    source.replace(target)


def delete_workspace_file(project_id: str, generated_projects_dir: Path, path: str) -> None:
    project_dir = project_dir_for(project_id, generated_projects_dir)
    target = resolve_workspace_path(project_dir, path)
    if not target.is_file():
        raise FileNotFoundError("File not found.")
    target.unlink()


def read_workspace_file(project_id: str, generated_projects_dir: Path, path: str) -> str:
    project_dir = project_dir_for(project_id, generated_projects_dir)
    target_path = resolve_workspace_path(project_dir, path)
    if not target_path.is_file():
        raise FileNotFoundError("File not found.")
    if target_path.stat().st_size > MAX_IDE_FILE_SIZE_BYTES:
        raise ValueError("File is too large to read in IDE.")
    return target_path.read_text(encoding="utf-8")


def list_workspace_files(project_id: str, generated_projects_dir: Path) -> list[str]:
    project_dir = project_dir_for(project_id, generated_projects_dir)
    if not project_dir.is_dir():
        raise FileNotFoundError("Generated project not found.")
    paths: list[str] = []
    for file_path in sorted(project_dir.rglob("*")):
        if file_path.is_file():
            paths.append(file_path.relative_to(project_dir).as_posix())
    return paths


def remove_project_workspace(project_id: str, generated_projects_dir: Path) -> None:
    project_dir = project_dir_for(project_id, generated_projects_dir)
    if project_dir.exists():
        shutil.rmtree(project_dir)


def _container_running(container_id: str) -> bool:
    if not container_id:
        return False
    result = run_docker_command(["inspect", "-f", "{{.State.Running}}", container_id])
    return result.returncode == 0 and result.stdout.strip().lower() == "true"


def generate_ide_password() -> str:
    return "123456"


def run_docker_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["docker", *args],
            capture_output=True,
            text=True,
            shell=False,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(DOCKER_UNAVAILABLE_MESSAGE) from exc


def docker_container_exists(container_name: str) -> bool:
    result = run_docker_command(["ps", "-a", "--filter", f"name=^{container_name}$", "--format", "{{.ID}}"])
    if result.returncode != 0:
        raise RuntimeError(normalize_docker_error(result.stderr.strip() or result.stdout.strip()))
    return bool(result.stdout.strip())


def remove_container_by_name(container_name: str) -> None:
    run_docker_command(["rm", "-f", container_name])


def wait_for_ide_health(url: str, timeout_seconds: int = 30) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1) as response:
                if 200 <= int(response.status) < 500:
                    return True
        except (OSError, URLError):
            time.sleep(0.5)
    return False


def cleanup_idle_ide_instances(max_idle_minutes: int = DEFAULT_IDLE_TIMEOUT_MINUTES) -> None:
    now = time.time()
    max_idle_seconds = max_idle_minutes * 60
    stale_ids = [
        project_id
        for project_id, instance in IDE_REGISTRY.items()
        if now - instance.last_accessed_at > max_idle_seconds
    ]
    for project_id in stale_ids:
        close_ide(project_id)


def normalize_docker_error(error_text: str) -> str:
    lowered = error_text.lower()
    if (
        "cannot connect to the docker daemon" in lowered
        or "error during connect" in lowered
        or "docker daemon" in lowered
        or "the system cannot find the file specified" in lowered
    ):
        return DOCKER_UNAVAILABLE_MESSAGE
    if "unable to find image" in lowered or "pull access denied" in lowered or "no such image" in lowered:
        return "IDE Docker image is missing. Build it with: docker build -f Dockerfile.ide -t project-agent-ide ."
    return error_text or "Could not start code-server container."
