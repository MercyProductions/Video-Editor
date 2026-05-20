from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from assets.intelligence import analyze_asset_library
from ai.generator import generate_project_from_prompt
from content.thumbnails import generate_thumbnail_set
from parser.project_parser import ProjectParser
from preview.realtime import generate_realtime_preview
from preview.reporter import generate_preview
from renderer.renderer import VideoRenderer
from stability.performance import performance_dashboard_report


def profile_workflow(project_path: Path, *, output_path: Path | None = None, include_render: bool = False) -> dict[str, Any]:
    project_path = project_path.resolve()
    timings: list[dict[str, Any]] = []
    parser_holder: dict[str, Any] = {}

    def load_project() -> None:
        parser_holder["project"] = ProjectParser().load(project_path)

    timings.append(_time_step("parse_validate_timeline", load_project))
    project = parser_holder["project"]
    timings.append(_time_step("preview_report", lambda: generate_preview(project, output_dir=Path(__file__).resolve().parents[2] / "output" / "profile_preview")))
    timings.append(_time_step("asset_analysis", lambda: analyze_asset_library(project_path, project_data=project.raw)))
    timings.append(_time_step("realtime_preview_draft", lambda: generate_realtime_preview(project, timestamp=0.5, output_dir=Path(__file__).resolve().parents[2] / "output" / "profile_realtime", quality_mode="draft")))
    timings.append(_time_step("local_prompt_generation", lambda: generate_project_from_prompt("Create a 12 second clean product promo with captions")))
    video_asset = _first_video_asset(project_path, project.raw)
    if video_asset:
        timings.append(_time_step("thumbnail_generation", lambda: generate_thumbnail_set(video_asset, title="Profile Test", output_dir=Path(__file__).resolve().parents[2] / "output" / "profile_thumbnails")))
    if include_render:
        render_output = Path(__file__).resolve().parents[2] / "output" / "profile_render.mp4"
        timings.append(_time_step("preview_render", lambda: VideoRenderer(project, output_path=render_output, quality="preview", use_cache=True, resume=True).render()))

    dashboard = performance_dashboard_report()
    report = {
        "format": "automatic-video-editor-performance-profile",
        "createdAt": _now(),
        "project": str(project_path),
        "includeRender": include_render,
        "timings": timings,
        "slowest": sorted(timings, key=lambda item: item["seconds"], reverse=True)[:5],
        "dashboard": {
            "cpu": dashboard.get("cpu"),
            "memory": dashboard.get("memory"),
            "gpu": dashboard.get("gpu"),
            "cache": dashboard.get("cache"),
            "bottlenecks": dashboard.get("bottlenecks"),
        },
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _time_step(name: str, fn: Callable[[], Any]) -> dict[str, Any]:
    started = time.perf_counter()
    error = None
    try:
        fn()
    except Exception as exc:
        error = str(exc)
    return {"name": name, "seconds": round(time.perf_counter() - started, 4), "ok": error is None, "error": error}


def _first_video_asset(project_path: Path, project: dict[str, Any]) -> Path | None:
    for value in project.get("assets", {}).values():
        raw = Path(str(value))
        resolved = raw if raw.is_absolute() else project_path.parent / raw
        if resolved.exists() and resolved.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}:
            return resolved
    return None


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
