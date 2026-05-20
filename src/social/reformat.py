from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from presets.export_presets import get_export_preset


TARGETS = {
    "youtube": "youtube_1080p",
    "youtube_landscape": "youtube_1080p",
    "youtube_shorts": "shorts",
    "tiktok": "tiktok_reels",
    "instagram_reels": "tiktok_reels",
    "instagram_square": "square",
    "shorts": "shorts",
    "discord": "discord_720p",
    "x_twitter": "youtube_1080p",
}


def reformat_project(project_path: Path, targets: list[str], output_dir: Path) -> dict[str, Any]:
    data = json.loads(project_path.resolve().read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    if targets == ["all"]:
        targets = list(TARGETS)
    outputs = []
    for target in targets:
        preset_key = TARGETS[target]
        preset = get_export_preset(preset_key)
        if not preset:
            continue
        formatted = copy.deepcopy(data)
        formatted["exportPreset"] = preset.key
        formatted.setdefault("metadata", {})["socialReformatTarget"] = target
        formatted["project"] = {
            **formatted.get("project", {}),
            "width": preset.width,
            "height": preset.height,
            "fps": preset.fps,
            "crf": preset.crf,
            "duration": formatted.get("project", {}).get("duration", 1),
        }
        _adapt_layers(formatted, preset.width, preset.height)
        _relocate_assets_for_output(formatted, project_path, output_dir / f"{project_path.stem}.{target}.json")
        output = output_dir / f"{project_path.stem}.{target}.json"
        output.write_text(json.dumps(formatted, indent=2) + "\n", encoding="utf-8")
        outputs.append({"target": target, "preset": preset.key, "path": str(output.resolve())})
    return {"source": str(project_path.resolve()), "outputs": outputs}


def _adapt_layers(project: dict[str, Any], width: int, height: int) -> None:
    vertical = height > width
    square = height == width
    for scene in project.get("timeline", []):
        for layer in scene.get("layers", []):
            if layer.get("type") in {"video", "image"}:
                layer["x"] = 0
                layer["y"] = 0
                layer["width"] = width
                layer["height"] = height
                layer["autoFit"] = "cover" if vertical or square else "contain"
            if layer.get("type") in {"text", "caption", "captions"}:
                layer["x"] = "center"
                if vertical:
                    layer.setdefault("layout", "lower_third")
                    layer["fontSize"] = min(float(layer.get("fontSize", 56)), 68)
                elif square:
                    layer.setdefault("layout", "lower_third")


def _relocate_assets_for_output(data: dict[str, Any], source_project_path: Path, output_path: Path) -> None:
    if source_project_path.parent.resolve() == output_path.parent.resolve():
        return
    for key, value in list((data.get("assets", {}) or {}).items()):
        raw = Path(str(value))
        if not raw.is_absolute():
            data["assets"][key] = str((source_project_path.parent / raw).resolve())
