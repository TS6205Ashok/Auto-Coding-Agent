from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from .file_service import (
    SYSTEM_FILENAMES,
    build_file_tree_from_paths,
    build_required_docs,
    ensure_within_directory,
    sanitize_relative_path,
    slugify,
)


def create_project_zip(preview: dict[str, Any], generated_dir: Path) -> dict[str, str]:
    generated_dir.mkdir(parents=True, exist_ok=True)

    project_name = str(preview.get("projectName") or "Generated Project")
    slug = slugify(project_name)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    unique_suffix = uuid4().hex[:8]
    bundle_name = f"{slug}-{timestamp}-{unique_suffix}"

    project_dir = generated_dir / bundle_name
    project_dir.mkdir(parents=True, exist_ok=False)

    _write_project_source_files(project_dir, preview)
    bundle_info: dict[str, Any] = {}

    actual_paths = [
        path.relative_to(project_dir).as_posix()
        for path in sorted(project_dir.rglob("*"))
        if path.is_file()
    ]
    bundle_info["actualFileTree"] = build_file_tree_from_paths(actual_paths)

    required_docs = build_required_docs(preview, bundle_info)
    full_paths = sorted(set(actual_paths + list(required_docs.keys())))
    bundle_info["actualFileTree"] = build_file_tree_from_paths(full_paths)
    required_docs = build_required_docs(preview, bundle_info)
    for doc_name, content in required_docs.items():
        target_path = project_dir / doc_name
        _write_text_file(project_dir, target_path, content)

    zip_path = generated_dir / f"{bundle_name}.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zip_file:
        for file_path in sorted(project_dir.rglob("*")):
            if file_path.is_file():
                arcname = Path(bundle_name) / file_path.relative_to(project_dir)
                zip_file.write(file_path, arcname=arcname)

    return {
        "filename": zip_path.name,
        "downloadUrl": f"/downloads/{zip_path.name}",
    }


def _write_project_source_files(project_dir: Path, preview: dict[str, Any]) -> None:
    written_paths: set[Path] = set()
    for file_entry in preview.get("files", []):
        relative_path = sanitize_relative_path(str(file_entry.get("path", "")))
        if relative_path in written_paths or (
            relative_path.name in SYSTEM_FILENAMES and relative_path.parent == Path(".")
        ):
            continue

        content = str(file_entry.get("content", ""))
        target_path = project_dir / relative_path
        _write_text_file(project_dir, target_path, content)
        written_paths.add(relative_path)


def _write_text_file(project_dir: Path, target_path: Path, content: str) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if not ensure_within_directory(project_dir, target_path):
        raise ValueError(f"Refusing to write outside the generated project folder: {target_path}")
    target_path.write_text(content, encoding="utf-8")
