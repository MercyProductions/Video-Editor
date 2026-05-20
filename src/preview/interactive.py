from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from assets.resolver import AssetResolver
from parser.models import ProjectConfig
from parser.project_parser import ProjectParser
from preview.realtime import generate_realtime_preview
from preview.reporter import generate_preview
from renderer.renderer import VideoRenderer
from utils.media import run_ffmpeg


QUALITY_TARGETS = {
    "draft": {"width": 480, "fps": 15},
    "proxy": {"width": 540, "fps": 24},
    "balanced": {"width": 960, "fps": 30},
    "high": {"width": 1280, "fps": 60},
    "final_sim": {"width": None, "fps": None},
}


def generate_interactive_preview(
    project: ProjectConfig,
    *,
    output_dir: Path | None = None,
    quality_mode: str = "balanced",
    scope: str = "full",
    scene_id: str | None = None,
    generate_placeholders: bool = False,
) -> dict[str, Any]:
    """Render a cached low-res review video plus metadata for the desktop preview UI."""

    output_dir = output_dir or (Path(__file__).resolve().parents[2] / "output" / "interactive_preview")
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / ".interactive_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    selected_scene_id = scene_id if scope == "scene" else None
    preview_data = _preview_project_data(project, quality_mode=quality_mode, scene_id=selected_scene_id)
    cache_key = _cache_key(project, preview_data, quality_mode=quality_mode, scope=scope, scene_id=selected_scene_id)
    preview_project_path = cache_dir / f"{cache_key}.project.json"
    preview_video_path = cache_dir / f"{cache_key}.mp4"
    was_cached = preview_video_path.exists()

    if not was_cached:
        with preview_project_path.open("w", encoding="utf-8") as handle:
            json.dump(preview_data, handle, indent=2)
            handle.write("\n")
        preview_project = ProjectParser().load(preview_project_path)
        VideoRenderer(
            preview_project,
            output_path=preview_video_path,
            quality="preview",
            generate_placeholders=generate_placeholders,
            use_cache=True,
            resume=True,
        ).render()
    elif not preview_project_path.exists():
        with preview_project_path.open("w", encoding="utf-8") as handle:
            json.dump(preview_data, handle, indent=2)
            handle.write("\n")

    parsed_preview = ProjectParser().load(preview_project_path)
    timeline = generate_preview(parsed_preview, output_dir=output_dir, generate_placeholders=generate_placeholders)
    thumbnails = _scene_thumbnails(project, output_dir, quality_mode=quality_mode)
    waveform_path = _waveform_preview(project, output_dir, generate_placeholders=generate_placeholders)
    duration = _estimated_duration(parsed_preview)

    report_path = output_dir / "interactive_preview.json"
    report = {
        "project": str(project.path),
        "previewProject": str(preview_project_path.resolve()),
        "previewVideo": str(preview_video_path.resolve()),
        "reportPath": str(report_path.resolve()),
        "timelineSummaryPath": str(timeline.summary_path.resolve()),
        "renderPlanPath": str(timeline.plan_path.resolve()),
        "sceneThumbnails": thumbnails,
        "waveformPath": str(waveform_path.resolve()) if waveform_path else None,
        "qualityMode": quality_mode,
        "scope": "scene" if selected_scene_id else "full",
        "selectedSceneId": selected_scene_id,
        "duration": duration,
        "estimatedFinalDuration": _estimated_duration(project),
        "fps": parsed_preview.settings.fps,
        "resolution": {
            "width": parsed_preview.settings.width,
            "height": parsed_preview.settings.height,
        },
        "safeZones": {
            "titleInsetPercent": 8,
            "actionInsetPercent": 5,
        },
        "supports": [
            "captions",
            "text overlays",
            "title cards",
            "zooms",
            "transitions",
            "lighting effects",
            "music timing",
            "beat sync metadata",
            "safe-zone overlays",
            "cursor spotlight/focus effects",
        ],
        "cached": was_cached,
        "notes": [
            "Interactive preview renders a cached low-quality MP4 and review assets without exporting the final video.",
            "Use final_sim when the user needs a slower but closer preview of final timing and framing.",
        ],
    }
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    return report


def _preview_project_data(project: ProjectConfig, *, quality_mode: str, scene_id: str | None) -> dict[str, Any]:
    data = copy.deepcopy(project.raw)
    data["assets"] = _absolute_assets(project)
    data["project"] = _scaled_project_settings(project, data.get("project", {}), quality_mode)
    scale_x = data["project"]["width"] / max(project.settings.width, 1)
    scale_y = data["project"]["height"] / max(project.settings.height, 1)
    data["timeline"] = [_scaled_scene(scene, scale_x, scale_y) for scene in data.get("timeline", [])]

    if scene_id:
        source_scene = next((scene for scene in project.timeline if scene.id == scene_id), None)
        if source_scene is None:
            raise KeyError(f"Scene not found: {scene_id}")
        selected = [scene for scene in data["timeline"] if scene.get("id") == scene_id]
        if not selected:
            raise KeyError(f"Scene not found: {scene_id}")
        selected[0]["start"] = 0
        data["timeline"] = selected
        data["project"]["duration"] = float(selected[0].get("duration", source_scene.duration))
        data["audio"] = _shift_audio_for_scene(data.get("audio", []), source_scene.start, source_scene.duration)
    else:
        data["project"]["duration"] = _estimated_duration(project)

    data.setdefault("metadata", {})
    data["metadata"]["interactivePreview"] = {
        "qualityMode": quality_mode,
        "sceneId": scene_id,
        "sourceProject": str(project.path.resolve()),
    }
    return data


def _absolute_assets(project: ProjectConfig) -> dict[str, str]:
    assets: dict[str, str] = {}
    for key, raw_path in project.assets.items():
        path = Path(raw_path)
        assets[key] = str(path if path.is_absolute() else (project.root_dir / path).resolve())
    return assets


def _scaled_project_settings(project: ProjectConfig, settings: dict[str, Any], quality_mode: str) -> dict[str, Any]:
    scaled = dict(settings)
    target = QUALITY_TARGETS.get(quality_mode, QUALITY_TARGETS["balanced"])
    if target["width"] is None:
        scaled["width"] = project.settings.width
        scaled["height"] = project.settings.height
        scaled["fps"] = project.settings.fps
        return scaled

    width = min(int(target["width"] or project.settings.width), project.settings.width)
    height = max(int(round(width * project.settings.height / max(project.settings.width, 1))), 1)
    scaled["width"] = width
    scaled["height"] = height
    scaled["fps"] = min(int(target["fps"] or project.settings.fps), project.settings.fps)
    scaled["crf"] = max(int(scaled.get("crf", 24) or 24), 30)
    return scaled


def _scaled_scene(scene: dict[str, Any], scale_x: float, scale_y: float) -> dict[str, Any]:
    scaled = copy.deepcopy(scene)
    for layer in scaled.get("layers", []):
        _scale_numeric(layer, "x", scale_x)
        _scale_numeric(layer, "y", scale_y)
        _scale_numeric(layer, "width", scale_x)
        _scale_numeric(layer, "height", scale_y)
        _scale_numeric(layer, "fontSize", min(scale_x, scale_y))
        _scale_numeric(layer, "strokeWidth", min(scale_x, scale_y))
        _scale_numeric(layer, "boxBorderWidth", min(scale_x, scale_y))
        _scale_numeric(layer, "boxPadding", min(scale_x, scale_y))
        shadow = layer.get("shadow")
        if isinstance(shadow, dict):
            _scale_numeric(shadow, "x", scale_x)
            _scale_numeric(shadow, "y", scale_y)
            _scale_numeric(shadow, "blur", min(scale_x, scale_y))
        box = layer.get("box")
        if isinstance(box, dict):
            _scale_numeric(box, "padding", min(scale_x, scale_y))
            _scale_numeric(box, "radius", min(scale_x, scale_y))
    return scaled


def _scale_numeric(target: dict[str, Any], key: str, scale: float) -> None:
    value = target.get(key)
    if isinstance(value, (int, float)):
        target[key] = round(float(value) * scale, 3)


def _shift_audio_for_scene(audio_tracks: list[dict[str, Any]], scene_start: float, scene_duration: float) -> list[dict[str, Any]]:
    shifted: list[dict[str, Any]] = []
    for track in audio_tracks:
        start = float(track.get("start", 0) or 0)
        track_duration = track.get("duration")
        end = float(track_duration) + start if track_duration is not None else scene_start + scene_duration
        if end < scene_start or start > scene_start + scene_duration:
            continue
        copy_track = copy.deepcopy(track)
        copy_track["start"] = max(start - scene_start, 0)
        if start < scene_start:
            copy_track["trimStart"] = float(copy_track.get("trimStart", 0) or 0) + (scene_start - start)
        copy_track["duration"] = min(float(copy_track.get("duration", scene_duration) or scene_duration), scene_duration)
        shifted.append(copy_track)
    return shifted


def _scene_thumbnails(project: ProjectConfig, output_dir: Path, *, quality_mode: str) -> list[dict[str, Any]]:
    thumb_dir = output_dir / "scene_thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    thumbnails = []
    for scene in project.timeline:
        result = generate_realtime_preview(
            project,
            timestamp=scene.start + scene.duration / 2,
            scene_id=scene.id,
            output_dir=thumb_dir,
            quality_mode=quality_mode,
            layer_mode="all",
        )
        thumbnails.append(
            {
                "sceneId": scene.id,
                "start": scene.start,
                "duration": scene.duration,
                "frame": result["frame"],
            }
        )
    return thumbnails


def _waveform_preview(project: ProjectConfig, output_dir: Path, *, generate_placeholders: bool) -> Path | None:
    if not project.audio:
        return None
    resolver = AssetResolver(project, generate_missing=generate_placeholders)
    try:
        audio_path = resolver.resolve(project.audio[0].asset, "audio")
    except Exception:
        return None
    waveform = output_dir / "waveform.png"
    result = run_ffmpeg(
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(audio_path),
            "-filter_complex",
            "aformat=channel_layouts=mono,showwavespic=s=1600x180:colors=0xD85050",
            "-frames:v",
            "1",
            str(waveform),
        ]
    )
    return waveform if result.returncode == 0 and waveform.exists() else None


def _estimated_duration(project: ProjectConfig) -> float:
    timeline_duration = max((scene.start + scene.duration for scene in project.timeline), default=0.0)
    return round(max(float(project.settings.duration or 0), timeline_duration), 3)


def _cache_key(project: ProjectConfig, data: dict[str, Any], *, quality_mode: str, scope: str, scene_id: str | None) -> str:
    source = json.dumps(
        {
            "project": str(project.path.resolve()),
            "mtime": project.path.stat().st_mtime if project.path.exists() else 0,
            "quality": quality_mode,
            "scope": scope,
            "sceneId": scene_id,
            "data": data,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:24]
