from __future__ import annotations

import json
import shutil
import time
import traceback
from pathlib import Path
from typing import Any

from metrics.store import metrics_from_project, record_metric
from parser.project_parser import ProjectParser
from renderer.renderer import VideoRenderer


def reliable_render_project(
    project_path: Path,
    *,
    output_path: Path | None = None,
    attempts: int = 2,
    quality: str = "final",
    use_cache: bool = True,
    resume: bool = True,
    gpu: bool = False,
    log_dir: Path | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    project_path = project_path.resolve()
    output = output_path.resolve() if output_path else project_path.with_suffix(".mp4")
    partial = output.with_name(f"{output.stem}.partial{output.suffix}")
    logs = log_dir or Path(__file__).resolve().parents[2] / "output" / "render_logs"
    logs.mkdir(parents=True, exist_ok=True)
    attempts = max(1, attempts)
    attempt_reports = []
    success = False
    final_error = None
    for attempt in range(1, attempts + 1):
        log_path = logs / f"{project_path.stem}.{int(time.time())}.attempt{attempt}.log"
        try:
            if partial.exists():
                partial.unlink()
            project = ProjectParser().load(project_path)
            renderer = VideoRenderer(project, output_path=partial, quality=quality, use_cache=use_cache, resume=resume, gpu=gpu)
            rendered = renderer.render()
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(rendered), str(output))
            log_path.write_text(f"attempt={attempt}\nstatus=completed\noutput={output}\n", encoding="utf-8")
            attempt_reports.append({"attempt": attempt, "status": "completed", "log": str(log_path.resolve())})
            record_metric(
                "render",
                {
                    **metrics_from_project(project.raw),
                    "project": str(project_path),
                    "output": str(output),
                    "outputSize": output.stat().st_size if output.exists() else 0,
                    "renderSeconds": round(time.perf_counter() - started, 3),
                    "quality": quality,
                    "reliable": True,
                    "attempt": attempt,
                    "gpu": gpu,
                    "cache": use_cache,
                },
            )
            success = True
            break
        except Exception as exc:
            final_error = str(exc)
            if partial.exists():
                try:
                    partial.unlink()
                except OSError:
                    pass
            log_path.write_text(
                f"attempt={attempt}\nstatus=failed\nproject={project_path}\nerror={exc}\n\n{traceback.format_exc()}",
                encoding="utf-8",
            )
            attempt_reports.append({"attempt": attempt, "status": "failed", "error": str(exc), "log": str(log_path.resolve())})
            time.sleep(0.2)
    report = {
        "format": "automatic-video-editor-reliable-render-report",
        "createdAt": _now(),
        "project": str(project_path),
        "output": str(output),
        "success": success,
        "attempts": attempt_reports,
        "attemptCount": len(attempt_reports),
        "quality": quality,
        "cache": use_cache,
        "resume": resume,
        "gpu": gpu,
        "renderSeconds": round(time.perf_counter() - started, 3),
        "error": final_error if not success else None,
    }
    report_path = logs / f"{project_path.stem}.reliable_render_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    report["reportPath"] = str(report_path.resolve())
    return report


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
