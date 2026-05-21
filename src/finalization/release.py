from __future__ import annotations

import compileall
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from finalization.audit import architecture_audit
from finalization.profiler import profile_workflow
from media.compat import analyze_media
from parser.project_parser import ProjectParser
from plugins.registry import audit_plugins
from quality.checker import run_quality_check
from recovery.integrity import check_project_integrity
from renderer.renderer import VideoRenderer
from schema.validator import validate_project
from stability.dependencies import offline_dependency_report


def release_candidate_check(*, output_path: Path | None = None, include_render_profile: bool = False) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    checks: list[dict[str, Any]] = []
    examples = [root / "examples" / "project.json", *sorted((root / "examples" / "demos").glob("*.json"))]
    for project in examples:
        checks.append(_validate_json_check(project))
        checks.append(_integrity_check(project))
    checks.append(_python_compile_check(root))
    checks.append(_python_tests_check(root))
    dependencies = offline_dependency_report()
    plugin_report = audit_plugins()
    architecture = architecture_audit()
    profile = profile_workflow(root / "examples" / "project.json", include_render=include_render_profile)

    checks.append({"name": "ffmpeg_available", "ok": bool(dependencies.get("ffmpeg", {}).get("installed")), "details": dependencies.get("ffmpeg", {})})
    checks.append({"name": "plugin_audit", "ok": not any(item.get("severity") == "error" for item in plugin_report["warnings"]), "details": {"warnings": plugin_report["warnings"]}})
    checks.append({"name": "architecture_warning_budget", "ok": architecture["summary"]["warningCount"] <= 3, "details": architecture["warnings"]})
    checks.append({"name": "profile_steps", "ok": all(item["ok"] for item in profile["timings"]), "details": profile["timings"]})
    checks.append(_quality_check(root / "examples" / "project.json", root / "output" / "release_check_quality.json"))
    checks.append(_render_check(root / "examples" / "project.json", root / "output" / "release_check_preview.mp4", quality="preview"))
    checks.append(_render_check(root / "examples" / "project.json", root / "output" / "release_check_final.mp4", quality="final"))
    checks.extend(_desktop_checks(root))

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


def _python_compile_check(root: Path) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        src_ok = compileall.compile_dir(root / "src", quiet=1)
        entry_ok = compileall.compile_file(root / "render.py", quiet=1)
        return {
            "name": "python_compile",
            "ok": bool(src_ok and entry_ok),
            "seconds": round(time.perf_counter() - started, 4),
            "details": {"src": bool(src_ok), "renderPy": bool(entry_ok)},
        }
    except Exception as exc:
        return {"name": "python_compile", "ok": False, "seconds": round(time.perf_counter() - started, 4), "error": str(exc)}


def _python_tests_check(root: Path) -> dict[str, Any]:
    return _run_command("python:smoke_tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=root, timeout_seconds=180)


def _quality_check(project_path: Path, output_path: Path) -> dict[str, Any]:
    try:
        report = run_quality_check(project_path, output_path=output_path)
        return {
            "name": "quality_check:project.json",
            "ok": bool(report.get("passed")),
            "project": str(project_path.resolve()),
            "details": {
                "output": str(output_path.resolve()),
                "issueCount": report.get("issueCount", 0),
                "issues": report.get("issues", []),
            },
        }
    except Exception as exc:
        return {"name": "quality_check:project.json", "ok": False, "project": str(project_path.resolve()), "error": str(exc)}


def _render_check(project_path: Path, output_path: Path, *, quality: str) -> dict[str, Any]:
    started = time.perf_counter()
    name = f"{quality}_render:project.json"
    try:
        project = ProjectParser().load(project_path)
        rendered = VideoRenderer(project, output_path=output_path, quality=quality, use_cache=True, resume=True).render()
        size = rendered.stat().st_size if rendered.exists() else 0
        media = analyze_media(rendered) if rendered.exists() else {}
        actual_duration = float(media.get("duration") or 0)
        expected_duration = project.settings.duration
        duration_delta = abs(actual_duration - expected_duration) if actual_duration else None
        duration_ok = duration_delta is not None and duration_delta <= 0.4
        return {
            "name": name,
            "ok": rendered.exists() and size > 0 and duration_ok,
            "project": str(project_path.resolve()),
            "seconds": round(time.perf_counter() - started, 4),
            "details": {
                "output": str(rendered.resolve()),
                "bytes": size,
                "quality": quality,
                "expectedDuration": expected_duration,
                "actualDuration": actual_duration,
                "durationDelta": round(duration_delta, 3) if duration_delta is not None else None,
                "durationTolerance": 0.4,
            },
        }
    except Exception as exc:
        return {
            "name": name,
            "ok": False,
            "project": str(project_path.resolve()),
            "seconds": round(time.perf_counter() - started, 4),
            "error": str(exc),
        }


def _desktop_checks(root: Path) -> list[dict[str, Any]]:
    desktop = root / "desktop-app"
    package_json = desktop / "package.json"
    if not package_json.exists():
        return [{"name": "desktop:available", "ok": False, "error": f"Missing desktop app package: {package_json}"}]

    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        return [{"name": "desktop:npm", "ok": False, "error": "npm was not found on PATH."}]

    return [
        _run_command("desktop:typecheck", [npm, "run", "typecheck"], cwd=desktop, timeout_seconds=240),
        _run_command("desktop:unit_tests", [npm, "run", "test:unit"], cwd=desktop, timeout_seconds=180),
        _run_command("desktop:build", [npm, "run", "build"], cwd=desktop, timeout_seconds=300),
    ]


def _run_command(name: str, command: list[str], *, cwd: Path, timeout_seconds: int) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
        )
        return {
            "name": name,
            "ok": result.returncode == 0,
            "seconds": round(time.perf_counter() - started, 4),
            "details": {
                "command": _display_command(command),
                "cwd": str(cwd.resolve()),
                "exitCode": result.returncode,
                "stdoutTail": _tail(result.stdout),
                "stderrTail": _tail(result.stderr),
            },
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "name": name,
            "ok": False,
            "seconds": round(time.perf_counter() - started, 4),
            "error": f"Command timed out after {timeout_seconds}s.",
            "details": {"command": _display_command(command), "stdoutTail": _tail(exc.stdout), "stderrTail": _tail(exc.stderr)},
        }
    except Exception as exc:
        return {"name": name, "ok": False, "seconds": round(time.perf_counter() - started, 4), "error": str(exc), "details": {"command": _display_command(command)}}


def _display_command(command: list[str]) -> str:
    return " ".join(Path(part).name if index == 0 else part for index, part in enumerate(command))


def _tail(value: str | bytes | None, *, lines: int = 30) -> str:
    if value is None:
        return ""
    text = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value
    return "\n".join(text.splitlines()[-lines:])


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
