from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from assets.resolver import AssetResolver
from parser.models import ProjectConfig, Scene
from utils.media import run_ffmpeg


def generate_storyboard(project: ProjectConfig, *, output_dir: Path | None = None) -> dict[str, Any]:
    output_dir = output_dir or (Path(__file__).resolve().parents[2] / "output" / "storyboard")
    thumbnails_dir = output_dir / "thumbnails"
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    resolver = AssetResolver(project, generate_missing=False)

    scenes = []
    for index, scene in enumerate(project.timeline):
        thumbnail = thumbnails_dir / f"{index + 1:03d}_{_safe(scene.id)}.png"
        _thumbnail_for_scene(project, resolver, scene, thumbnail)
        scenes.append(
            {
                "id": scene.id,
                "start": scene.start,
                "duration": scene.duration,
                "thumbnail": str(thumbnail.resolve()),
                "summary": _scene_summary(scene),
                "layers": [
                    {
                        "type": layer.type,
                        "asset": layer.raw.get("asset"),
                        "text": layer.raw.get("text"),
                        "layout": layer.raw.get("layout"),
                    }
                    for layer in scene.layers
                ],
                "transitionOut": scene.transition_out or {"type": "cut", "duration": 0},
            }
        )

    storyboard = {
        "project": str(project.path),
        "duration": project.settings.duration,
        "timingMap": [{"scene": scene["id"], "start": scene["start"], "duration": scene["duration"]} for scene in scenes],
        "transitionMap": [{"scene": scene["id"], "transitionOut": scene["transitionOut"]} for scene in scenes],
        "scenes": scenes,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    storyboard_path = output_dir / "storyboard.json"
    text_path = output_dir / "storyboard.txt"
    with storyboard_path.open("w", encoding="utf-8") as handle:
        json.dump(storyboard, handle, indent=2)
        handle.write("\n")
    text_path.write_text(_storyboard_text(storyboard), encoding="utf-8")
    storyboard["storyboardPath"] = str(storyboard_path)
    storyboard["textPath"] = str(text_path)
    return storyboard


def _thumbnail_for_scene(project: ProjectConfig, resolver: AssetResolver, scene: Scene, output: Path) -> None:
    media_layer = next((layer for layer in scene.layers if layer.type in {"video", "image"} and layer.raw.get("asset")), None)
    if media_layer:
        try:
            asset = resolver.resolve(str(media_layer.raw["asset"]), media_layer.type)
            if media_layer.type == "image":
                args = ["-y", "-hide_banner", "-loglevel", "error", "-i", str(asset)]
            else:
                trim = float(media_layer.raw.get("trimStart", 0) or 0)
                args = ["-y", "-hide_banner", "-loglevel", "error", "-ss", str(trim), "-i", str(asset)]
            result = run_ffmpeg(
                args
                + [
                    "-frames:v",
                    "1",
                    "-vf",
                    f"scale={min(project.settings.width, 640)}:-2",
                    str(output),
                ]
            )
            if result.returncode == 0 and output.exists():
                return
        except Exception:
            pass
    run_ffmpeg(
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x1b1a16:s={min(project.settings.width, 640)}x{max(int(min(project.settings.width, 640) * project.settings.height / project.settings.width), 1)}",
            "-frames:v",
            "1",
            str(output),
        ]
    )


def _scene_summary(scene: Scene) -> str:
    text = next((str(layer.raw.get("text")) for layer in scene.layers if layer.raw.get("text")), None)
    media = [str(layer.raw.get("asset")) for layer in scene.layers if layer.raw.get("asset")]
    parts = [f"{scene.id}: {scene.duration:g}s"]
    if text:
        parts.append(f"text '{text}'")
    if media:
        parts.append("media " + ", ".join(media[:3]))
    return "; ".join(parts)


def _storyboard_text(storyboard: dict[str, Any]) -> str:
    lines = ["Storyboard", "=" * 20, f"Project: {storyboard['project']}", f"Duration: {storyboard['duration']}s", ""]
    for scene in storyboard["scenes"]:
        lines.append(f"{scene['id']} | {scene['start']}s - {scene['start'] + scene['duration']}s")
        lines.append(f"  Summary: {scene['summary']}")
        lines.append(f"  Thumbnail: {scene['thumbnail']}")
        lines.append(f"  Transition: {scene['transitionOut']}")
    return "\n".join(lines) + "\n"


def _safe(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value) or "scene"
