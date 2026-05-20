from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

from color.pipeline import apply_color_pipeline
from content.suggestions import suggest_scene_improvements
from styles.presets import apply_style, list_styles, normalize_style


POLISH_PRESETS: dict[str, dict[str, Any]] = {
    "clean_cinematic": {
        "style": "clean_cinematic",
        "color": "clean_cinematic",
        "camera": {"mode": "cinematic_sway", "intensity": 0.16, "zoom": 1.024, "easing": "easeInOutCubic"},
        "transition": {"type": "crossfade", "duration": 0.42},
        "caption": {"fontSizeScale": 0.052, "maxWords": 7},
    },
    "premium_red_black": {
        "style": "red_black_aegis",
        "color": "premium_red_black",
        "camera": {"mode": "parallax", "intensity": 0.22, "zoom": 1.038, "easing": "easeInOutCubic"},
        "transition": {"type": "fadeToBlack", "duration": 0.32},
        "caption": {"fontSizeScale": 0.055, "maxWords": 6},
    },
    "social_punch": {
        "style": "gaming_montage",
        "color": "social_punch",
        "camera": {"mode": "handheld", "intensity": 0.3, "zoom": 1.055, "easing": "easeOutQuart"},
        "transition": {"type": "zoom", "duration": 0.22},
        "caption": {"fontSizeScale": 0.06, "maxWords": 5},
    },
    "soft_luxury": {
        "style": "luxury_promo",
        "color": "soft_luxury",
        "camera": {"mode": "cinematic_sway", "intensity": 0.12, "zoom": 1.018, "easing": "easeInOutSine"},
        "transition": {"type": "crossfade", "duration": 0.62},
        "caption": {"fontSizeScale": 0.045, "maxWords": 8},
    },
}


def list_polish_presets() -> list[str]:
    return sorted(POLISH_PRESETS)


def refine_project(project: dict[str, Any], preset: str = "clean_cinematic") -> dict[str, Any]:
    key = preset.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in POLISH_PRESETS:
        if normalize_style(key) in list_styles():
            key = "clean_cinematic"
        else:
            valid = ", ".join(list_polish_presets())
            raise ValueError(f"Unknown refinement preset '{preset}'. Valid presets: {valid}")
    config = POLISH_PRESETS[key]
    refined = apply_style(deepcopy(project), config["style"])
    refined = apply_color_pipeline(refined, config["color"])
    _normalize_timeline(refined)
    _tune_scenes(refined, config)
    _tune_audio(refined)
    _add_markers(refined)
    suggestions = suggest_scene_improvements(refined)
    refined.setdefault("metadata", {}).setdefault("phase11", {}).update(
        {
            "refinementPreset": key,
            "focus": [
                "motion smoothness",
                "readable captions",
                "consistent transitions",
                "Rec.709-safe color grade",
                "balanced audio defaults",
            ],
            "suggestionCount": suggestions["suggestionCount"],
            "suggestions": suggestions["suggestions"][:10],
        }
    )
    return refined


def _normalize_timeline(project: dict[str, Any]) -> None:
    timeline = project.get("timeline", [])
    cursor = 0.0
    for scene in timeline:
        scene["start"] = round(cursor, 3)
        scene["duration"] = max(round(float(scene.get("duration", 1) or 1), 3), 0.25)
        cursor += float(scene["duration"])
    project.setdefault("project", {})["duration"] = round(cursor, 3)


def _tune_scenes(project: dict[str, Any], config: dict[str, Any]) -> None:
    settings = project.get("project", {})
    width = int(settings.get("width", 1920) or 1920)
    height = int(settings.get("height", 1080) or 1080)
    timeline = project.get("timeline", [])
    transition_counter: Counter[str] = Counter()
    for index, scene in enumerate(timeline):
        duration = float(scene.get("duration", 1) or 1)
        scene.setdefault("nestedScene", False)
        scene.setdefault("group", _scene_group(scene, index))
        scene.setdefault("timelineMarkers", _scene_markers(scene))
        post = scene.setdefault("postProcessing", {})
        post.setdefault("vignette", 0.22)
        post.setdefault("glow", 0.08)
        post.setdefault("exposure", 0)
        if index < len(timeline) - 1:
            transition = _transition_for_duration(duration, config["transition"], transition_counter)
            scene["transitionOut"] = transition
            transition_counter[transition["type"]] += 1
        else:
            scene.pop("transitionOut", None)
        for layer in scene.get("layers", []):
            _tune_layer(layer, scene, width, height, config)


def _transition_for_duration(duration: float, base: dict[str, Any], counter: Counter[str]) -> dict[str, Any]:
    if duration <= 1.4:
        return {"type": "cut", "duration": 0}
    transition = dict(base)
    if duration <= 2.4:
        transition["duration"] = min(float(transition.get("duration", 0.25) or 0.25), 0.24)
    if counter.get(str(transition.get("type")), 0) >= 3:
        return {"type": "crossfade", "duration": min(float(transition.get("duration", 0.35) or 0.35), 0.35)}
    return transition


def _tune_layer(layer: dict[str, Any], scene: dict[str, Any], width: int, height: int, config: dict[str, Any]) -> None:
    layer_type = layer.get("type")
    if layer_type in {"video", "image"}:
        layer.setdefault("width", width)
        layer.setdefault("height", height)
        layer.setdefault("autoFit", "cover")
        camera = dict(config["camera"])
        camera.setdefault("duration", scene.get("duration", 1))
        layer["camera"] = {**camera, **(layer.get("camera") if isinstance(layer.get("camera"), dict) else {})}
        layer.setdefault("motionBlur", 0.08)
    if layer_type == "text":
        layer.setdefault("box", True)
        layer.setdefault("boxColor", "#00000099")
        layer.setdefault("boxPadding", 14)
        layer.setdefault("strokeColor", "#000000")
        layer.setdefault("strokeWidth", 2)
        layer.setdefault("shadowColor", "#000000")
        layer.setdefault("shadowX", 2)
        layer.setdefault("shadowY", 3)
        _keep_text_safe(layer, width, height)
    if layer_type in {"caption", "captions"}:
        _refine_caption_layer(layer, width, height, config["caption"])


def _refine_caption_layer(layer: dict[str, Any], width: int, height: int, config: dict[str, Any]) -> None:
    vertical = height > width
    font_size = max(34, int((height if vertical else width) * float(config["fontSizeScale"])))
    layer["fontSize"] = min(font_size, 74 if vertical else 58)
    layer.setdefault("x", "center")
    layer["y"] = int(height * (0.76 if vertical else 0.82))
    layer["box"] = True
    layer["boxColor"] = "#000000bb"
    layer["boxPadding"] = max(12, int(layer["fontSize"] * 0.28))
    layer["strokeColor"] = "#000000"
    layer["strokeWidth"] = max(2, int(layer["fontSize"] * 0.07))
    layer["shadowColor"] = "#000000"
    layer["safeZone"] = "title"
    layer["readability"] = {"maxWords": config["maxWords"], "minDurationPerWord": 0.24, "safeZone": "title"}
    for item in layer.get("items", []):
        text = str(item.get("text", ""))
        words = text.split()
        if len(words) > config["maxWords"]:
            item["text"] = _balance_caption(words, int(config["maxWords"]))
        duration = float(item.get("duration", 0) or 0)
        min_duration = max(0.85, len(words) * 0.24)
        if duration and duration < min_duration:
            item["duration"] = round(min_duration, 3)
        item.setdefault("emphasisWords", _emphasis_words(text))
        item.setdefault("highlightColor", "#ef4444")


def _tune_audio(project: dict[str, Any]) -> None:
    for track in project.get("audio", []):
        track.setdefault("volume", 0.42)
        track.setdefault("fadeIn", 0.25)
        track.setdefault("fadeOut", 1.1)
        track.setdefault("compressor", True)
        track.setdefault("limiter", True)
        track.setdefault("normalize", True)
        track.setdefault("autoBalance", True)


def _add_markers(project: dict[str, Any]) -> None:
    markers = []
    for scene in project.get("timeline", []):
        markers.append({"sceneId": scene.get("id"), "time": scene.get("start", 0), "type": "scene_start", "label": scene.get("id")})
        if scene.get("transitionOut"):
            markers.append(
                {
                    "sceneId": scene.get("id"),
                    "time": round(float(scene.get("start", 0)) + float(scene.get("duration", 0)), 3),
                    "type": "transition",
                    "label": scene["transitionOut"].get("type", "transition"),
                }
            )
    project.setdefault("metadata", {}).setdefault("timeline", {})["markers"] = markers


def _keep_text_safe(layer: dict[str, Any], width: int, height: int) -> None:
    if isinstance(layer.get("x"), (int, float)):
        layer["x"] = min(max(float(layer["x"]), width * 0.06), width * 0.94)
    if isinstance(layer.get("y"), (int, float)):
        layer["y"] = min(max(float(layer["y"]), height * 0.08), height * 0.9)


def _scene_group(scene: dict[str, Any], index: int) -> str:
    text = " ".join(str(layer.get("text", "")) for layer in scene.get("layers", [])).lower()
    if index == 0 or "intro" in str(scene.get("id", "")).lower():
        return "intro"
    if "cta" in text or "subscribe" in text or "follow" in text:
        return "outro"
    if scene.get("transitionOut"):
        return "sequence"
    return "main"


def _scene_markers(scene: dict[str, Any]) -> list[dict[str, Any]]:
    markers = [{"time": 0, "type": "start", "label": "scene"}]
    for layer in scene.get("layers", []):
        if layer.get("type") in {"caption", "captions"} and layer.get("items"):
            for item in layer["items"][:3]:
                markers.append({"time": item.get("start", 0), "type": "caption", "label": str(item.get("text", ""))[:28]})
    return markers


def _balance_caption(words: list[str], max_words: int) -> str:
    if len(words) <= max_words:
        return " ".join(words)
    midpoint = min(max_words, max(2, len(words) // 2))
    return " ".join(words[:midpoint]) + "\n" + " ".join(words[midpoint:])


def _emphasis_words(text: str) -> list[str]:
    stop = {"this", "that", "with", "from", "your", "into", "about", "have", "will", "then", "they"}
    words = [word.strip(".,!?:;\"'()[]").lower() for word in text.split()]
    return [word for word in words if len(word) >= 5 and word not in stop][:3]
