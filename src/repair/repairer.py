from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from schema.validator import get_validation_errors, validate_project


@dataclass(slots=True)
class RepairResult:
    data: dict[str, Any]
    valid: bool
    errors_before: list[str] = field(default_factory=list)
    errors_after: list[str] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)


VALID_TOP_LEVEL = {"project", "assets", "timeline", "audio", "captions", "metadata", "exportPreset", "stylePreset"}
VALID_LAYER_TYPES = {"video", "image", "text", "caption", "captions", "solid"}
VALID_TRANSITIONS = {"cut", "crossfade", "fade", "fadeToBlack", "slide", "zoom"}
VALID_ANIMATIONS = {
    "fade",
    "slideUp",
    "slideDown",
    "slideLeft",
    "slideRight",
    "zoomIn",
    "zoomOut",
    "shake",
    "pulse",
    "typewriter",
}
VALID_PRESETS = {"youtube_1080p", "tiktok_reels", "shorts", "square", "discord_720p", "cinematic_4k"}
VALID_STYLES = {
    "clean_cinematic",
    "gaming_montage",
    "red_black_aegis",
    "blue_black_cyber",
    "vaporwave",
    "minimal_tech",
    "horror_glitch",
    "luxury_promo",
}


def _error_lines(data: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for error in get_validation_errors(data):
        path = "$"
        for part in error.absolute_path:
            path += f"[{part}]" if isinstance(part, int) else f".{part}"
        lines.append(f"{path}: {error.message}")
    return lines


def repair_project_file(path: Path, output_path: Path | None = None, *, in_place: bool = False) -> RepairResult:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    result = repair_project_data(data)
    target = path if in_place else output_path
    if target:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            json.dump(result.data, handle, indent=2)
            handle.write("\n")
    return result


def repair_project_data(data: dict[str, Any]) -> RepairResult:
    repaired = json.loads(json.dumps(data))
    result = RepairResult(data=repaired, valid=False, errors_before=_error_lines(repaired))

    if not isinstance(repaired, dict):
        repaired = {}
        result.data = repaired
        result.fixes.append("Replaced non-object JSON root with a project object.")

    _remove_unknown_top_level(repaired, result)
    _ensure_project(repaired, result)
    _ensure_assets(repaired, result)
    _ensure_timeline(repaired, result)
    _repair_audio(repaired, result)
    _repair_captions(repaired, result)
    _repair_preset(repaired, result)
    _repair_style(repaired, result)

    try:
        validate_project(repaired)
        result.valid = True
    except Exception:
        result.errors_after = _error_lines(repaired)
        result.valid = False
    return result


def _remove_unknown_top_level(data: dict[str, Any], result: RepairResult) -> None:
    for key in list(data):
        if key not in VALID_TOP_LEVEL:
            data.setdefault("metadata", {})[key] = data.pop(key)
            result.fixes.append(f"Moved unknown top-level field '{key}' into metadata.")


def _ensure_project(data: dict[str, Any], result: RepairResult) -> None:
    project = data.get("project")
    if not isinstance(project, dict):
        project = {}
        data["project"] = project
        result.fixes.append("Added missing project settings.")

    defaults = {"width": 1920, "height": 1080, "fps": 30, "duration": 10, "background": "#000000"}
    for key, value in defaults.items():
        if key not in project or not isinstance(project[key], (int, float, str)):
            project[key] = value
            result.fixes.append(f"Set project.{key} to {value}.")

    for key in ("width", "height", "fps"):
        try:
            project[key] = max(int(project[key]), 16 if key != "fps" else 1)
        except (TypeError, ValueError):
            project[key] = defaults[key]
            result.fixes.append(f"Converted project.{key} to a valid integer.")
    try:
        project["duration"] = max(float(project["duration"]), 1)
    except (TypeError, ValueError):
        project["duration"] = defaults["duration"]
        result.fixes.append("Converted project.duration to a valid number.")


def _ensure_assets(data: dict[str, Any], result: RepairResult) -> None:
    assets = data.get("assets")
    if not isinstance(assets, dict):
        data["assets"] = {}
        result.fixes.append("Added missing assets map.")
        return
    for key, value in list(assets.items()):
        if not isinstance(value, str) or not value:
            assets[key] = f"assets/{key}.mp4"
            result.fixes.append(f"Replaced invalid asset path for '{key}'.")


def _ensure_timeline(data: dict[str, Any], result: RepairResult) -> None:
    timeline = data.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        data["timeline"] = [
            {
                "id": "scene_1",
                "start": 0,
                "duration": data["project"]["duration"],
                "layers": [{"type": "text", "text": "Placeholder Scene", "x": "center", "y": "center"}],
            }
        ]
        result.fixes.append("Added a placeholder timeline scene.")
        return

    current_start = 0.0
    for index, scene in enumerate(timeline):
        if not isinstance(scene, dict):
            timeline[index] = scene = {}
            result.fixes.append(f"Replaced invalid scene at index {index}.")
        scene.setdefault("id", f"scene_{index + 1}")
        scene["id"] = str(scene["id"]) or f"scene_{index + 1}"
        scene["start"] = _number(scene.get("start"), current_start)
        scene["duration"] = max(_number(scene.get("duration"), 3), 0.1)
        current_start = float(scene["start"]) + float(scene["duration"])
        layers = scene.get("layers")
        if not isinstance(layers, list):
            layers = []
            scene["layers"] = layers
            result.fixes.append(f"Added missing layers list to scene '{scene['id']}'.")
        if not layers:
            layers.append({"type": "text", "text": "Placeholder Text", "x": "center", "y": "center"})
            result.fixes.append(f"Added placeholder text layer to scene '{scene['id']}'.")
        for layer_index, layer in enumerate(layers):
            _repair_layer(data, scene, layer, layer_index, result)
        _repair_transition(scene, result)


def _repair_layer(
    data: dict[str, Any],
    scene: dict[str, Any],
    layer: Any,
    layer_index: int,
    result: RepairResult,
) -> None:
    if not isinstance(layer, dict):
        scene["layers"][layer_index] = layer = {"type": "text", "text": "Placeholder Text"}
        result.fixes.append(f"Replaced invalid layer {layer_index} in scene '{scene['id']}'.")
    layer_type = str(layer.get("type", "text"))
    if layer_type not in VALID_LAYER_TYPES:
        layer_type = "text"
        result.fixes.append(f"Changed unknown layer type in scene '{scene['id']}' to text.")
    layer["type"] = layer_type

    if layer_type == "text":
        if "text" not in layer:
            result.fixes.append(f"Added missing text to a text layer in scene '{scene['id']}'.")
        layer.setdefault("text", "Placeholder Text")
    if layer_type in {"video", "image"}:
        if not layer.get("asset"):
            result.fixes.append(f"Added missing asset to {layer_type} layer in scene '{scene['id']}'.")
        asset_key = str(layer.get("asset") or f"{layer_type}_{scene['id']}_{layer_index + 1}")
        layer["asset"] = asset_key
        suffix = ".png" if layer_type == "image" else ".mp4"
        data.setdefault("assets", {}).setdefault(asset_key, f"assets/{asset_key}{suffix}")
    if layer_type in {"caption", "captions"} and not layer.get("items") and not layer.get("text"):
        layer["items"] = [{"text": "Placeholder caption", "start": 0, "duration": min(2, scene["duration"])}]

    if "animation" in layer:
        layer["animation"] = _repair_animation(layer["animation"], result)
    if "duration" in layer:
        layer["duration"] = max(_number(layer["duration"], scene["duration"]), 0.1)
    if "start" in layer:
        layer["start"] = max(_number(layer["start"], 0), 0)


def _repair_transition(scene: dict[str, Any], result: RepairResult) -> None:
    transition = scene.get("transitionOut")
    if transition is None:
        return
    if not isinstance(transition, dict):
        scene["transitionOut"] = {"type": "cut", "duration": 0}
        result.fixes.append(f"Replaced invalid transition in scene '{scene['id']}'.")
        return
    if transition.get("type") not in VALID_TRANSITIONS:
        transition["type"] = "cut"
        result.fixes.append(f"Changed unknown transition in scene '{scene['id']}' to cut.")
    transition["duration"] = max(_number(transition.get("duration"), 0), 0)


def _repair_animation(value: Any, result: RepairResult) -> Any:
    if isinstance(value, str):
        if value in VALID_ANIMATIONS:
            return value
        result.fixes.append("Changed unknown animation to fade.")
        return "fade"
    if isinstance(value, dict):
        for key in ("in", "out"):
            if key in value and value[key] not in VALID_ANIMATIONS:
                value[key] = "fade"
                result.fixes.append(f"Changed unknown animation.{key} to fade.")
        return value
    result.fixes.append("Removed invalid animation value.")
    return "fade"


def _repair_audio(data: dict[str, Any], result: RepairResult) -> None:
    audio = data.get("audio", [])
    if audio is None:
        data["audio"] = []
        return
    if not isinstance(audio, list):
        data["audio"] = []
        result.fixes.append("Replaced invalid audio value with an empty list.")
        return
    for index, track in enumerate(audio):
        if not isinstance(track, dict):
            audio[index] = track = {}
            result.fixes.append(f"Replaced invalid audio track at index {index}.")
        if not track.get("asset"):
            result.fixes.append(f"Added missing asset to audio track {index}.")
        asset = str(track.get("asset") or f"music_{index + 1}")
        track["asset"] = asset
        track["start"] = max(_number(track.get("start"), 0), 0)
        track["volume"] = max(_number(track.get("volume"), 1), 0)
        data.setdefault("assets", {}).setdefault(asset, f"assets/{asset}.wav")


def _repair_captions(data: dict[str, Any], result: RepairResult) -> None:
    captions = data.get("captions", [])
    if captions is None:
        data["captions"] = []
    elif not isinstance(captions, list):
        data["captions"] = []
        result.fixes.append("Replaced invalid captions value with an empty list.")


def _repair_preset(data: dict[str, Any], result: RepairResult) -> None:
    preset = data.get("exportPreset")
    if preset is not None and preset not in VALID_PRESETS:
        data["exportPreset"] = "youtube_1080p"
        result.fixes.append("Changed unknown exportPreset to youtube_1080p.")


def _repair_style(data: dict[str, Any], result: RepairResult) -> None:
    style = data.get("stylePreset")
    if style is not None and style not in VALID_STYLES:
        data["stylePreset"] = "clean_cinematic"
        result.fixes.append("Changed unknown stylePreset to clean_cinematic.")


def _number(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)
