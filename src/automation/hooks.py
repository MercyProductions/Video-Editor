from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from parser.project_parser import ProjectParser
from renderer.renderer import VideoRenderer
from schema.validator import validate_project


def process_queue_folder(queue_dir: Path, *, output_dir: Path, quality: str = "preview") -> dict[str, Any]:
    queue_dir = queue_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    jobs = []
    for project_path in sorted(queue_dir.glob("*.json")):
        if not _looks_like_project(project_path):
            continue
        jobs.append(_render_project(project_path, output_dir=output_dir, quality=quality))
    report = {"queue": str(queue_dir), "jobCount": len(jobs), "jobs": jobs}
    (output_dir / "queue_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def watch_project_folder(
    watch_dir: Path,
    *,
    output_dir: Path,
    quality: str = "preview",
    once: bool = True,
    poll_seconds: float = 2,
) -> dict[str, Any]:
    seen: dict[str, float] = {}
    runs: list[dict[str, Any]] = []
    while True:
        for project_path in sorted(watch_dir.glob("*.json")):
            if not _looks_like_project(project_path):
                continue
            mtime = project_path.stat().st_mtime
            if seen.get(str(project_path)) == mtime:
                continue
            seen[str(project_path)] = mtime
            runs.append(_render_project(project_path, output_dir=output_dir, quality=quality))
        if once:
            break
        time.sleep(max(poll_seconds, 0.5))
    report = {"watchDir": str(watch_dir.resolve()), "runCount": len(runs), "runs": runs}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "watch_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _render_project(project_path: Path, *, output_dir: Path, quality: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        data = json.loads(project_path.read_text(encoding="utf-8"))
        validate_project(data)
        project = ProjectParser().load(project_path)
        output = output_dir / f"{project_path.stem}.mp4"
        VideoRenderer(project, output_path=output, quality=quality, use_cache=True, resume=True).render()
        return {
            "project": str(project_path.resolve()),
            "output": str(output.resolve()),
            "ok": True,
            "seconds": round(time.perf_counter() - started, 3),
        }
    except Exception as exc:
        return {
            "project": str(project_path.resolve()),
            "ok": False,
            "error": str(exc),
            "seconds": round(time.perf_counter() - started, 3),
        }


def _looks_like_project(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return isinstance(data, dict) and all(key in data for key in ("project", "assets", "timeline"))
