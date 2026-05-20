from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def default_workspace_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "output" / "workspaces"


def create_workspace(name: str, *, workspace_path: Path | None = None) -> dict[str, Any]:
    path = workspace_path or default_workspace_dir() / f"{_slug(name)}.workspace.json"
    workspace = {
        "format": "automatic-video-editor-workspace",
        "version": 1,
        "name": name,
        "createdAt": _now(),
        "updatedAt": _now(),
        "projects": [],
        "layout": default_layout(),
        "profiles": [],
        "multiMonitor": {"enabled": True, "monitors": [], "lastKnownBounds": []},
    }
    _write(path, workspace)
    workspace["path"] = str(path.resolve())
    return workspace


def list_workspaces(root: Path | None = None) -> list[dict[str, Any]]:
    root = root or default_workspace_dir()
    rows = []
    for path in sorted(root.glob("*.workspace.json")):
        try:
            data = _read(path)
        except Exception:
            continue
        rows.append({"name": data.get("name", path.stem), "projectCount": len(data.get("projects", [])), "updatedAt": data.get("updatedAt"), "path": str(path.resolve())})
    return rows


def describe_workspace(path: Path) -> dict[str, Any]:
    data = _read(path)
    data["path"] = str(path.resolve())
    return data


def open_project(workspace_path: Path, project_path: Path) -> dict[str, Any]:
    workspace = _read_or_create(workspace_path)
    resolved = str(project_path.resolve())
    projects = workspace.setdefault("projects", [])
    if not any(item.get("path") == resolved for item in projects):
        projects.append({"path": resolved, "openedAt": _now(), "active": True})
    for project in projects:
        project["active"] = project.get("path") == resolved
    workspace["updatedAt"] = _now()
    _write(workspace_path, workspace)
    workspace["path"] = str(workspace_path.resolve())
    return workspace


def close_project(workspace_path: Path, project_path: Path) -> dict[str, Any]:
    workspace = _read_or_create(workspace_path)
    resolved = str(project_path.resolve())
    workspace["projects"] = [item for item in workspace.get("projects", []) if item.get("path") != resolved]
    if workspace["projects"] and not any(item.get("active") for item in workspace["projects"]):
        workspace["projects"][0]["active"] = True
    workspace["updatedAt"] = _now()
    _write(workspace_path, workspace)
    workspace["path"] = str(workspace_path.resolve())
    return workspace


def save_layout(workspace_path: Path, layout: dict[str, Any] | str) -> dict[str, Any]:
    workspace = _read_or_create(workspace_path)
    if isinstance(layout, str):
        layout = preset_layout(layout)
    workspace["layout"] = layout
    workspace["updatedAt"] = _now()
    _write(workspace_path, workspace)
    workspace["path"] = str(workspace_path.resolve())
    return workspace


def add_workspace_profile(workspace_path: Path, name: str, settings: dict[str, Any] | None = None) -> dict[str, Any]:
    workspace = _read_or_create(workspace_path)
    profiles = workspace.setdefault("profiles", [])
    profile = {
        "name": name,
        "createdAt": _now(),
        "settings": settings or {
            "defaultLayout": workspace.get("layout", {}).get("name", "editing"),
            "preferredMode": "beginner",
            "renderQuality": "preview",
        },
    }
    profiles[:] = [item for item in profiles if item.get("name") != name]
    profiles.append(profile)
    workspace["updatedAt"] = _now()
    _write(workspace_path, workspace)
    workspace["path"] = str(workspace_path.resolve())
    return workspace


def list_workspace_profiles(workspace_path: Path) -> list[dict[str, Any]]:
    workspace = _read_or_create(workspace_path)
    return list(workspace.get("profiles", []))


def default_layout() -> dict[str, Any]:
    return preset_layout("editing")


def preset_layout(name: str) -> dict[str, Any]:
    key = name.strip().lower().replace("-", "_").replace(" ", "_")
    presets = {
        "editing": {
            "name": "editing",
            "panels": {
                "dashboard": {"visible": True, "dock": "left", "width": 280},
                "timeline": {"visible": True, "dock": "bottom", "height": 260},
                "preview": {"visible": True, "dock": "center"},
                "assets": {"visible": True, "dock": "right", "width": 320},
                "json": {"visible": False, "dock": "right", "width": 420},
                "render": {"visible": True, "dock": "right", "tab": "render"},
            },
            "detachablePanels": ["preview", "timeline", "assets", "json", "render"],
        },
        "review": {
            "name": "review",
            "panels": {
                "preview": {"visible": True, "dock": "center"},
                "timeline": {"visible": True, "dock": "bottom", "height": 220},
                "review": {"visible": True, "dock": "right", "width": 360},
                "assets": {"visible": False, "dock": "right"},
                "json": {"visible": False, "dock": "right"},
            },
            "detachablePanels": ["preview", "review"],
        },
        "advanced": {
            "name": "advanced",
            "panels": {
                "json": {"visible": True, "dock": "right", "width": 480},
                "timeline": {"visible": True, "dock": "bottom", "height": 300},
                "preview": {"visible": True, "dock": "center"},
                "assets": {"visible": True, "dock": "left", "width": 300},
                "logs": {"visible": True, "dock": "bottom", "tab": "logs"},
            },
            "detachablePanels": ["preview", "timeline", "json", "logs", "assets"],
        },
    }
    return presets.get(key, presets["editing"])


def _read_or_create(path: Path) -> dict[str, Any]:
    if not path.exists():
        return create_workspace(path.stem.replace(".workspace", ""), workspace_path=path)
    return _read(path)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "workspace"
