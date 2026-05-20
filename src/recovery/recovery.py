from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from repair.repairer import repair_project_file


def autosave_project(project_path: Path, text: str, *, recovery_dir: Path | None = None) -> dict[str, Any]:
    root = _root(project_path, recovery_dir)
    autosaves = root / "autosaves"
    autosaves.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = hashlib.sha1(str(project_path.resolve()).encode("utf-8")).hexdigest()[:10]
    path = autosaves / f"{project_path.stem}.{key}.{stamp}.json"
    path.write_text(text, encoding="utf-8")
    return {"type": "autosave", "path": str(path.resolve()), "timestamp": stamp, "projectPath": str(project_path.resolve())}


def backup_project(project_path: Path, *, recovery_dir: Path | None = None) -> dict[str, Any]:
    root = _root(project_path, recovery_dir)
    backups = root / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = backups / f"{project_path.stem}.{stamp}.json"
    shutil.copy2(project_path, path)
    return {"type": "backup", "path": str(path.resolve()), "timestamp": stamp, "projectPath": str(project_path.resolve())}


def create_restore_point(project_path: Path, label: str = "manual", *, recovery_dir: Path | None = None) -> dict[str, Any]:
    root = _root(project_path, recovery_dir)
    restore_points = root / "restore_points"
    restore_points.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_label = _safe_label(label)
    path = restore_points / f"{project_path.stem}.{safe_label}.{stamp}.json"
    shutil.copy2(project_path.resolve(), path)
    metadata = {
        "type": "restore_point",
        "label": label,
        "path": str(path.resolve()),
        "timestamp": stamp,
        "projectPath": str(project_path.resolve()),
        "sha256": _sha256(path),
    }
    (path.with_suffix(".meta.json")).write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def list_recovery_points(project_path: Path, *, recovery_dir: Path | None = None) -> list[dict[str, Any]]:
    root = _root(project_path, recovery_dir)
    points = []
    for folder, kind in (
        (root / "autosaves", "autosave"),
        (root / "backups", "backup"),
        (root / "restore_points", "restore_point"),
        (root / "render_sessions", "render_session"),
    ):
        if not folder.exists():
            continue
        for item in folder.glob("*"):
            if item.is_file() and item.suffix.lower() == ".json" and not item.name.endswith(".meta.json"):
                point = {"type": kind, "path": str(item.resolve()), "timestamp": _timestamp(item), "size": item.stat().st_size}
                meta_path = item.with_suffix(".meta.json")
                if meta_path.exists():
                    try:
                        point.update(json.loads(meta_path.read_text(encoding="utf-8")))
                    except json.JSONDecodeError:
                        point["metadataWarning"] = "metadata sidecar is unreadable"
                points.append(point)
    return sorted(points, key=lambda item: item["timestamp"], reverse=True)


def restore_recovery_point(source_path: Path, target_path: Path) -> dict[str, Any]:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path.resolve(), target_path.resolve())
    return {"restoredFrom": str(source_path.resolve()), "target": str(target_path.resolve())}


def cleanup_recovery_points(project_path: Path, *, keep: int = 12, recovery_dir: Path | None = None) -> dict[str, Any]:
    root = _root(project_path, recovery_dir)
    keep = max(1, keep)
    deleted = []
    for folder in (root / "autosaves", root / "backups", root / "restore_points", root / "render_sessions"):
        if not folder.exists():
            continue
        files = sorted(
            [item for item in folder.glob("*.json") if not item.name.endswith(".meta.json")],
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for item in files[keep:]:
            meta = item.with_suffix(".meta.json")
            try:
                item.unlink()
                deleted.append(str(item.resolve()))
                if meta.exists():
                    meta.unlink()
            except OSError:
                continue
    return {"projectPath": str(project_path.resolve()), "keep": keep, "deletedCount": len(deleted), "deleted": deleted}


def recover_corrupted_project(project_path: Path, output_path: Path | None = None, *, recovery_dir: Path | None = None) -> dict[str, Any]:
    output = output_path or project_path.with_name(f"{project_path.stem}.recovered.json")
    try:
        result = repair_project_file(project_path, output)
        return {
            "strategy": "repair",
            "output": str(output.resolve()),
            "valid": result.valid,
            "fixes": result.fixes,
            "errorsBefore": result.errors_before,
            "errorsAfter": result.errors_after,
        }
    except Exception as exc:
        points = list_recovery_points(project_path, recovery_dir=recovery_dir)
        if points:
            restore_recovery_point(Path(points[0]["path"]), output)
            return {
                "strategy": "latest_recovery_point",
                "output": str(output.resolve()),
                "valid": True,
                "restoredFrom": points[0]["path"],
                "originalError": str(exc),
            }
        fallback = {
            "project": {"width": 1920, "height": 1080, "fps": 30, "duration": 6, "background": "#000000"},
            "assets": {},
            "timeline": [
                {
                    "id": "recovered_placeholder",
                    "start": 0,
                    "duration": 6,
                    "layers": [
                        {
                            "type": "text",
                            "text": "Recovered Project",
                            "x": "center",
                            "y": "center",
                            "fontSize": 72,
                            "color": "#ffffff",
                        }
                    ],
                }
            ],
            "metadata": {"recovery": {"source": str(project_path.resolve()), "error": str(exc)}},
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(fallback, indent=2) + "\n", encoding="utf-8")
        return {"strategy": "minimal_placeholder", "output": str(output.resolve()), "valid": True, "originalError": str(exc)}


def _root(project_path: Path, recovery_dir: Path | None) -> Path:
    return recovery_dir or project_path.resolve().parent / ".ave_recovery"


def _timestamp(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def _safe_label(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "manual"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
