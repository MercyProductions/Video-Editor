from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from finalization.audit import architecture_audit
from finalization.profiler import profile_workflow
from plugins.registry import audit_plugins
from recovery.integrity import check_project_integrity
from schema.validator import validate_project
from stability.dependencies import offline_dependency_report


def release_candidate_check(*, output_path: Path | None = None, include_render_profile: bool = False) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    checks: list[dict[str, Any]] = []
    examples = [root / "examples" / "project.json", *sorted((root / "examples" / "demos").glob("*.json"))]
    for project in examples:
        checks.append(_validate_json_check(project))
        checks.append(_integrity_check(project))
    dependencies = offline_dependency_report()
    plugin_report = audit_plugins()
    architecture = architecture_audit()
    profile = profile_workflow(root / "examples" / "project.json", include_render=include_render_profile)

    checks.append({"name": "ffmpeg_available", "ok": bool(dependencies.get("ffmpeg", {}).get("installed")), "details": dependencies.get("ffmpeg", {})})
    checks.append({"name": "plugin_audit", "ok": not any(item.get("severity") == "error" for item in plugin_report["warnings"]), "details": {"warnings": plugin_report["warnings"]}})
    checks.append({"name": "architecture_warning_budget", "ok": architecture["summary"]["warningCount"] <= 3, "details": architecture["warnings"]})
    checks.append({"name": "profile_steps", "ok": all(item["ok"] for item in profile["timings"]), "details": profile["timings"]})

    failed = [check for check in checks if not check["ok"]]
    report = {
        "format": "automatic-video-editor-release-candidate-check",
        "createdAt": _now(),
        "versionTarget": "0.9.0",
        "localFirst": True,
        "checkCount": len(checks),
        "failedCount": len(failed),
        "ready": not failed,
        "checks": checks,
        "dependencySummary": dependencies.get("readiness", {}),
        "architectureSummary": architecture.get("summary", {}),
        "profileSummary": profile.get("slowest", []),
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _validate_json_check(project_path: Path) -> dict[str, Any]:
    try:
        validate_project(json.loads(project_path.read_text(encoding="utf-8")))
        return {"name": f"validate:{project_path.name}", "ok": True, "project": str(project_path.resolve())}
    except Exception as exc:
        return {"name": f"validate:{project_path.name}", "ok": False, "project": str(project_path.resolve()), "error": str(exc)}


def _integrity_check(project_path: Path) -> dict[str, Any]:
    report = check_project_integrity(project_path)
    return {"name": f"integrity:{project_path.name}", "ok": bool(report["valid"]), "project": str(project_path.resolve()), "details": {"issues": report["issues"]}}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
