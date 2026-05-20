from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from assets.resolver import AssetResolver
from parser.models import ProjectConfig, Scene
from renderer.filters import escape_text, ffmpeg_color
from utils.media import run_ffmpeg


def generate_realtime_preview(
    project: ProjectConfig,
    *,
    timestamp: float | None = None,
    scene_id: str | None = None,
    output_dir: Path | None = None,
    quality_mode: str = "balanced",
    layer_mode: str = "all",
) -> dict[str, Any]:
    output_dir = output_dir or (Path(__file__).resolve().parents[2] / "output" / "realtime_preview")
    cache_dir = output_dir / ".frame_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    scene = _select_scene(project, timestamp=timestamp, scene_id=scene_id)
    frame_time = float(timestamp if timestamp is not None else scene.start + scene.duration / 2)
    local_time = max(frame_time - scene.start, 0)
    cache_key = _cache_key(project, scene, local_time, quality_mode, layer_mode)
    frame_path = cache_dir / f"{cache_key}.png"
    if not frame_path.exists():
        _render_frame(project, scene, local_time, frame_path, quality_mode=quality_mode, layer_mode=layer_mode)

    report = {
        "project": str(project.path),
        "timestamp": round(frame_time, 3),
        "sceneId": scene.id,
        "sceneStart": scene.start,
        "sceneDuration": scene.duration,
        "localTime": round(local_time, 3),
        "frame": str(frame_path.resolve()),
        "cached": frame_path.exists(),
        "qualityMode": quality_mode,
        "layerMode": layer_mode,
        "effects": _scene_effects(scene),
        "transitionPreview": scene.transition_out or {"type": "cut", "duration": 0},
        "notes": [
            "Realtime preview renders a cached representative frame without exporting the full project.",
            "Scene/effect/transition metadata is included so the desktop scrubber can update instantly."
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "realtime_preview.json"
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    report["reportPath"] = str(report_path)
    return report


def _select_scene(project: ProjectConfig, *, timestamp: float | None, scene_id: str | None) -> Scene:
    if scene_id:
        for scene in project.timeline:
            if scene.id == scene_id:
                return scene
        raise KeyError(f"Scene not found: {scene_id}")
    time = float(timestamp or 0)
    for scene in project.timeline:
        if scene.start <= time < scene.start + scene.duration:
            return scene
    return project.timeline[-1]


def _render_frame(project: ProjectConfig, scene: Scene, local_time: float, output: Path, *, quality_mode: str, layer_mode: str) -> None:
    resolver = AssetResolver(project, generate_missing=True)
    quality_widths = {"draft": 480, "proxy": 540, "balanced": 960, "high": 1280, "final_sim": min(project.settings.width, 1920)}
    width = min(project.settings.width, quality_widths.get(quality_mode, 960))
    height = max(int(width * project.settings.height / project.settings.width), 1)
    media = None if layer_mode == "text" else next((layer for layer in scene.layers if layer.type in {"video", "image"} and layer.raw.get("asset")), None)
    text = None if layer_mode == "media" else next((layer for layer in scene.layers if layer.type in {"text", "caption", "captions"}), None)
    vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
    if quality_mode in {"draft", "proxy"}:
        vf += ",fps=12"
    if text:
        label = str(text.raw.get("text") or _caption_text(text.raw) or scene.id)
        color = str(text.raw.get("color", "#ffffff"))
        vf += (
            f",drawtext=text='{escape_text(label)}':"
            f"x=(w-text_w)/2:y=h-text_h-48:fontsize=34:"
            f"fontcolor={color}:box=1:boxcolor=black@0.55:boxborderw=12"
        )

    if media:
        asset = resolver.resolve(str(media.raw["asset"]), media.type)
        if media.type == "image":
            args = ["-y", "-hide_banner", "-loglevel", "error", "-i", str(asset)]
        else:
            trim_start = float(media.raw.get("trimStart", 0) or 0)
            layer_start = float(media.raw.get("start", 0) or 0)
            args = ["-y", "-hide_banner", "-loglevel", "error", "-ss", str(max(trim_start + local_time - layer_start, 0)), "-i", str(asset)]
        result = run_ffmpeg(args + ["-frames:v", "1", "-vf", vf, str(output)])
        if result.returncode == 0:
            return

    result = run_ffmpeg(
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c={ffmpeg_color(project.settings.background)}:s={width}x{height}",
            "-frames:v",
            "1",
            "-vf",
            vf,
            str(output),
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())


def _caption_text(layer: dict[str, Any]) -> str:
    items = layer.get("items") or []
    if items and isinstance(items, list):
        return str(items[0].get("text", ""))
    return str(layer.get("text", ""))


def _scene_effects(scene: Scene) -> list[dict[str, Any]]:
    effects = []
    for layer in scene.layers:
        if layer.raw.get("animation"):
            effects.append({"layer": layer.type, "animation": layer.raw.get("animation")})
        if layer.raw.get("effects"):
            effects.append({"layer": layer.type, "effects": layer.raw.get("effects")})
    return effects


def _cache_key(project: ProjectConfig, scene: Scene, local_time: float, quality_mode: str, layer_mode: str) -> str:
    source = json.dumps(
        {
            "project": str(project.path),
            "mtime": project.path.stat().st_mtime if project.path.exists() else 0,
            "scene": scene.raw,
            "time": round(local_time, 2),
            "size": [project.settings.width, project.settings.height],
            "quality": quality_mode,
            "layers": layer_mode,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:24]
