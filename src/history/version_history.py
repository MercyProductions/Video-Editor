from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def record_ai_edit(
    project_path: Path,
    old_project: dict[str, Any],
    new_project: dict[str, Any],
    change_summary: dict[str, Any],
) -> dict[str, Any]:
    history_dir = _history_dir(project_path)
    version_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    version_dir = history_dir / version_id
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_json(version_dir / "old_project.json", old_project)
    _write_json(version_dir / "new_project.json", new_project)
    summary = {
        "id": version_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "projectPath": str(project_path.resolve()),
        **change_summary,
    }
    _write_json(version_dir / "change_summary.json", summary)
    return summary


def list_versions(project_path: Path) -> list[dict[str, Any]]:
    history_dir = _history_dir(project_path)
    if not history_dir.exists():
        return []
    versions = []
    for summary_path in history_dir.glob("*/change_summary.json"):
        with summary_path.open("r", encoding="utf-8") as handle:
            versions.append(json.load(handle))
    return sorted(versions, key=lambda item: item.get("timestamp", ""), reverse=True)


def rollback_version(project_path: Path, version_id: str, *, output_path: Path | None = None) -> Path:
    version_dir = _history_dir(project_path) / version_id
    old_path = version_dir / "old_project.json"
    if not old_path.exists():
        raise FileNotFoundError(f"Version not found: {version_id}")
    target = output_path or project_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(old_path.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def _history_dir(project_path: Path) -> Path:
    return project_path.resolve().parent / ".ave_history"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
