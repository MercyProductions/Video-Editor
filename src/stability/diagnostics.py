from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from metrics.store import default_metrics_path
from plugins.registry import list_plugins
from repair.repairer import repair_project_file
from schema.validator import ProjectValidationError, validate_project
from utils.media import ffmpeg_binary


def run_diagnostics(project_path: Path | None = None, *, output_path: Path | None = None) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    output = root / "output"
    disk = shutil.disk_usage(root)
    report = {
        "format": "automatic-video-editor-diagnostics",
        "createdAt": _now(),
        "root": str(root),
        "ffmpeg": _ffmpeg_check(),
        "disk": {"total": disk.total, "used": disk.used, "free": disk.free},
        "cache": _cache_report(output),
        "memory": _memory_report(),
        "plugins": _plugin_report(),
        "metrics": _metrics_report(),
        "project": _project_report(project_path) if project_path else None,
        "stabilityPolicy": {
            "renderSandboxing": "renders use isolated temporary folders per render",
            "pluginIsolation": "current plugins are manifest-only and are not executed as code",
            "watchdogs": "diagnostics report cache growth, failed metrics, and invalid project state",
        },
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def repair_project(project_path: Path, output_path: Path) -> dict[str, Any]:
    result = repair_project_file(project_path, output_path)
    return {
        "project": str(project_path.resolve()),
        "output": str(output_path.resolve()),
        "valid": result.valid,
        "fixes": result.fixes,
        "errorsBefore": result.errors_before,
        "errorsAfter": result.errors_after,
    }


def _ffmpeg_check() -> dict[str, Any]:
    try:
        binary = ffmpeg_binary()
        return {"ok": True, "binary": binary}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _cache_report(output: Path) -> dict[str, Any]:
    caches = []
    for path in output.rglob("*cache*") if output.exists() else []:
        if path.is_dir():
            caches.append({"path": str(path), "bytes": _dir_size(path)})
    return {"cacheCount": len(caches), "totalBytes": sum(item["bytes"] for item in caches), "caches": caches[:20]}


def _plugin_report() -> dict[str, Any]:
    valid = []
    invalid = []
    plugin_root = Path(__file__).resolve().parents[2] / "plugins"
    for path in plugin_root.glob("*/plugin.json") if plugin_root.exists() else []:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            valid.append({"id": data.get("id"), "type": data.get("type"), "path": str(path.parent.resolve())})
        except Exception as exc:
            invalid.append({"path": str(path), "error": str(exc)})
    discovered = list_plugins(plugin_root)
    return {"validCount": len(valid), "invalidCount": len(invalid), "valid": valid, "invalid": invalid, "discoveredCount": len(discovered)}


def _metrics_report() -> dict[str, Any]:
    path = default_metrics_path()
    if not path.exists():
        return {"path": str(path), "exists": False, "failedRenderEvents": 0}
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {
        "path": str(path),
        "exists": True,
        "eventCount": len(rows),
        "failedRenderEvents": sum(1 for row in rows if row.get("event") == "render" and int(row.get("outputSize") or 0) <= 0),
    }


def _memory_report() -> dict[str, Any]:
    pid = os.getpid()
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            fields = [part.strip().strip('"') for part in result.stdout.strip().split(",")]
            memory = fields[4] if len(fields) >= 5 else None
            return {"pid": pid, "workingSet": memory, "source": "tasklist", "leakCheck": "single-snapshot baseline"}
    except Exception:
        pass
    return {"pid": pid, "workingSet": None, "source": "unavailable", "leakCheck": "single-snapshot baseline"}


def _project_report(project_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(project_path.read_text(encoding="utf-8"))
        validate_project(data)
        return {"path": str(project_path.resolve()), "valid": True, "sceneCount": len(data.get("timeline", [])), "assetCount": len(data.get("assets", {}))}
    except ProjectValidationError as exc:
        return {"path": str(project_path.resolve()), "valid": False, "error": str(exc)}
    except Exception as exc:
        return {"path": str(project_path.resolve()), "valid": False, "error": str(exc)}


def _dir_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
