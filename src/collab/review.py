from __future__ import annotations

import json
import time
import uuid
from difflib import unified_diff
from pathlib import Path
from typing import Any


MARKER_TYPES = {"needs_cut", "too_slow", "too_fast", "bad_caption", "bad_zoom", "bad_transition", "audio_issue", "keep"}
SCENE_STATUSES = {"needs_review", "approved", "locked", "regenerated", "excluded"}
ROLE_NAMES = {"owner", "editor", "reviewer", "viewer"}


def review_path_for_project(project_path: Path) -> Path:
    return project_path.parent / ".ave_review" / f"{project_path.stem}.review.json"


def load_review(project_path: Path) -> dict[str, Any]:
    path = review_path_for_project(project_path)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {
            "format": "automatic-video-editor-review",
            "version": 1,
            "project": str(project_path.resolve()),
            "createdAt": _now(),
            "updatedAt": _now(),
            "comments": [],
            "markers": [],
            "sceneApprovals": {},
            "assetLocks": {},
            "roles": {},
        }
    data["path"] = str(path.resolve())
    return data


def save_review(project_path: Path, data: dict[str, Any]) -> dict[str, Any]:
    path = review_path_for_project(project_path)
    data = {key: value for key, value in data.items() if key != "path"}
    data["updatedAt"] = _now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    data["path"] = str(path.resolve())
    return data


def add_comment(project_path: Path, *, scene_id: str, body: str, author: str = "local_user", timestamp: float | None = None) -> dict[str, Any]:
    data = load_review(project_path)
    data.setdefault("comments", []).append(
        {
            "id": _id("comment"),
            "sceneId": scene_id,
            "timestamp": timestamp,
            "author": author,
            "body": body,
            "createdAt": _now(),
            "resolved": False,
        }
    )
    return save_review(project_path, data)


def add_marker(project_path: Path, *, scene_id: str, marker_type: str, timestamp: float, note: str = "", author: str = "local_user") -> dict[str, Any]:
    if marker_type not in MARKER_TYPES:
        raise ValueError(f"Unsupported marker '{marker_type}'. Expected one of: {', '.join(sorted(MARKER_TYPES))}")
    data = load_review(project_path)
    data.setdefault("markers", []).append(
        {
            "id": _id("marker"),
            "sceneId": scene_id,
            "timestamp": round(timestamp, 3),
            "type": marker_type,
            "note": note,
            "author": author,
            "createdAt": _now(),
        }
    )
    return save_review(project_path, data)


def set_scene_status(project_path: Path, *, scene_id: str, status: str, author: str = "local_user") -> dict[str, Any]:
    if status not in SCENE_STATUSES:
        raise ValueError(f"Unsupported scene status '{status}'. Expected one of: {', '.join(sorted(SCENE_STATUSES))}")
    data = load_review(project_path)
    data.setdefault("sceneApprovals", {})[scene_id] = {"status": status, "author": author, "updatedAt": _now()}
    return save_review(project_path, data)


def lock_asset(project_path: Path, *, asset: str, owner: str = "local_user", reason: str = "") -> dict[str, Any]:
    data = load_review(project_path)
    data.setdefault("assetLocks", {})[asset] = {"owner": owner, "reason": reason, "lockedAt": _now()}
    return save_review(project_path, data)


def set_role(project_path: Path, *, user: str, role: str) -> dict[str, Any]:
    if role not in ROLE_NAMES:
        raise ValueError(f"Unsupported role '{role}'. Expected one of: {', '.join(sorted(ROLE_NAMES))}")
    data = load_review(project_path)
    data.setdefault("roles", {})[user] = {"role": role, "updatedAt": _now()}
    return save_review(project_path, data)


def export_review_report(project_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    data = load_review(project_path)
    report = {
        "project": data["project"],
        "reviewPath": data["path"],
        "commentCount": len(data.get("comments", [])),
        "unresolvedCommentCount": sum(1 for item in data.get("comments", []) if not item.get("resolved")),
        "markerCount": len(data.get("markers", [])),
        "sceneApprovals": data.get("sceneApprovals", {}),
        "assetLocks": data.get("assetLocks", {}),
        "roles": data.get("roles", {}),
        "comments": data.get("comments", []),
        "markers": data.get("markers", []),
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def compare_projects(left_path: Path, right_path: Path, *, output_path: Path | None = None) -> dict[str, Any]:
    left = json.loads(left_path.read_text(encoding="utf-8"))
    right = json.loads(right_path.read_text(encoding="utf-8"))
    left_scenes = {str(scene.get("id")): scene for scene in left.get("timeline", [])}
    right_scenes = {str(scene.get("id")): scene for scene in right.get("timeline", [])}
    added = sorted(set(right_scenes) - set(left_scenes))
    removed = sorted(set(left_scenes) - set(right_scenes))
    changed = []
    for scene_id in sorted(set(left_scenes) & set(right_scenes)):
        if left_scenes[scene_id] != right_scenes[scene_id]:
            changed.append(
                {
                    "sceneId": scene_id,
                    "leftDuration": left_scenes[scene_id].get("duration"),
                    "rightDuration": right_scenes[scene_id].get("duration"),
                    "leftLayerCount": len(left_scenes[scene_id].get("layers", [])),
                    "rightLayerCount": len(right_scenes[scene_id].get("layers", [])),
                }
            )
    diff = list(
        unified_diff(
            json.dumps(left, indent=2, sort_keys=True).splitlines(),
            json.dumps(right, indent=2, sort_keys=True).splitlines(),
            fromfile=str(left_path),
            tofile=str(right_path),
            lineterm="",
        )
    )
    report = {
        "left": str(left_path.resolve()),
        "right": str(right_path.resolve()),
        "summary": {
            "addedScenes": added,
            "removedScenes": removed,
            "changedSceneCount": len(changed),
            "lineDiffCount": len(diff),
        },
        "changedScenes": changed,
        "jsonDiff": diff[:1000],
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
