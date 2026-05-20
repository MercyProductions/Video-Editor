from __future__ import annotations

from copy import deepcopy
from typing import Any


PRESETS: dict[str, dict[str, Any]] = {
    "cinematic_polish": {
        "graph": "cinematic_polish",
        "camera": {"mode": "cinematic_sway", "intensity": 0.28, "zoom": 1.045},
        "accent": "#6db5a5",
        "transition": {"type": "crossfade", "duration": 0.42},
    },
    "premium_red_black": {
        "graph": "premium_red_black",
        "camera": {"mode": "parallax", "intensity": 0.36, "zoom": 1.07},
        "accent": "#ef4444",
        "transition": {"type": "zoom", "duration": 0.28},
    },
    "hype_montage": {
        "graph": "premium_red_black",
        "camera": {"mode": "handheld", "intensity": 0.46, "zoom": 1.09},
        "accent": "#f43f5e",
        "transition": {"type": "zoom", "duration": 0.22},
    },
}


def list_cinematic_presets() -> list[str]:
    return sorted(PRESETS)


def apply_cinematic_enhancement(project: dict[str, Any], preset: str = "cinematic_polish") -> dict[str, Any]:
    key = preset.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in PRESETS:
        valid = ", ".join(list_cinematic_presets())
        raise ValueError(f"Unknown cinematic preset '{preset}'. Valid presets: {valid}")

    enhanced = deepcopy(project)
    settings = enhanced.get("project", {})
    width = int(settings.get("width", 1920))
    height = int(settings.get("height", 1080))
    config = PRESETS[key]
    accent = config["accent"]

    enhanced.setdefault("metadata", {}).setdefault("phase8", {})["cinematicEnhancement"] = {
        "preset": key,
        "graph": config["graph"],
        "camera": config["camera"],
    }

    timeline = enhanced.get("timeline", [])
    for index, scene in enumerate(timeline):
        scene.setdefault("effectGraphPreset", config["graph"])
        scene.setdefault("postProcessing", {"vignette": 0.32, "glow": 0.18})
        if index < len(timeline) - 1:
            scene["transitionOut"] = dict(config["transition"])
        _enhance_layers(scene, width, height, config, accent, index)

    for track in enhanced.get("audio", []):
        track.setdefault("compressor", True)
        track.setdefault("limiter", True)
        if key in {"premium_red_black", "hype_montage"}:
            track.setdefault("bassEmphasis", 3)
    return enhanced


def _enhance_layers(scene: dict[str, Any], width: int, height: int, config: dict[str, Any], accent: str, scene_index: int) -> None:
    duration = float(scene.get("duration", 1) or 1)
    layers = scene.setdefault("layers", [])
    has_media = False
    has_progress = any(layer.get("type") == "progress" for layer in layers)
    has_hud = any(layer.get("type") == "hud" for layer in layers)

    for layer in layers:
        if layer.get("type") in {"video", "image"}:
            has_media = True
            layer.setdefault("camera", dict(config["camera"]))
            layer.setdefault("width", width)
            layer.setdefault("height", height)
        if layer.get("type") in {"text", "caption", "captions"}:
            layer.setdefault("shadowColor", "#000000")
            layer.setdefault("strokeColor", "#000000")
            layer.setdefault("strokeWidth", 2)

    if has_media and not has_hud:
        layers.append(
            {
                "type": "hud",
                "start": 0.1,
                "duration": max(duration - 0.2, 0.2),
                "x": int(width * 0.055),
                "y": int(height * 0.06),
                "title": f"SCENE {scene_index + 1:02d}",
                "subtitle": "cinematic pass",
                "color": accent,
                "boxColor": "#00000099",
            }
        )
    if not has_progress:
        layers.append(
            {
                "type": "progress",
                "start": 0,
                "duration": duration,
                "x": int(width * 0.08),
                "y": int(height * 0.93),
                "width": int(width * 0.84),
                "height": 8,
                "color": accent,
                "backgroundColor": "#00000066",
                "opacity": 0.72,
            }
        )
    if not has_media:
        layers.insert(0, {"type": "animated_background", "start": 0, "duration": duration, "color": accent, "opacity": 0.08, "speed": 90})
