from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from styles.presets import normalize_style


PRESET_SIZES = {
    "youtube_1080p": (1920, 1080, 60),
    "tiktok_reels": (1080, 1920, 60),
    "shorts": (1080, 1920, 60),
    "square": (1080, 1080, 30),
    "discord_720p": (1280, 720, 30),
    "cinematic_4k": (3840, 2160, 60),
}


def build_scene_prompt(
    prompt: str,
    *,
    duration: float = 8,
    preset: str = "shorts",
    style: str = "red_black_aegis",
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Build a self-contained cinematic motion-graphics sequence from a scene request."""
    style_key = normalize_style(style)
    width, height, fps = PRESET_SIZES.get(preset, PRESET_SIZES["shorts"])
    accent = "#ef4444" if style_key in {"red_black_aegis", "gaming_montage", "horror_glitch"} else "#6db5a5"
    background = "#050000" if style_key in {"red_black_aegis", "gaming_montage", "horror_glitch"} else "#05070d"
    title = _title_from_prompt(prompt)
    beat = max(duration / 4, 1.0)
    cursor = 0.0
    scenes = [
        _title_card("hype_open", cursor, min(beat, duration), title, "A cinematic reveal", width, height, accent, "premium_red_black"),
    ]
    cursor += scenes[-1]["duration"]
    if cursor < duration - 1.4:
        scenes.append(_feature_card("signal", cursor, min(beat, duration - cursor), "SCAN", "Finding launch blockers", width, height, accent))
        cursor += scenes[-1]["duration"]
    if cursor < duration - 1.2:
        scenes.append(_feature_card("impact", cursor, min(beat, duration - cursor), "FIX", "Runtime, security, and conflict checks", width, height, accent))
        cursor += scenes[-1]["duration"]
    if cursor < duration:
        scenes.append(_title_card("payoff", cursor, max(duration - cursor, 0.7), "READY TO LAUNCH", "Clean result. Faster troubleshooting.", width, height, accent, "cinematic_polish", outro=True))
    _retime(scenes, duration)

    project = {
        "metadata": {
            "phase8": {
                "sourcePrompt": prompt,
                "builder": "smart_scene_builder",
                "style": style_key,
                "motionGraphics": ["animated_background", "particle", "progress", "lower_third", "hud", "waveform"],
                "effectGraphs": sorted({scene.get("effectGraphPreset", "") for scene in scenes if scene.get("effectGraphPreset")}),
            }
        },
        "exportPreset": preset,
        "stylePreset": style_key if style_key in {"clean_cinematic", "gaming_montage", "red_black_aegis", "vaporwave", "minimal_tech", "horror_glitch", "luxury_promo"} else "clean_cinematic",
        "project": {"width": width, "height": height, "fps": fps, "duration": round(duration, 3), "background": background},
        "assets": {},
        "timeline": scenes,
        "audio": [],
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
    return project


def _title_card(
    scene_id: str,
    start: float,
    duration: float,
    title: str,
    subtitle: str,
    width: int,
    height: int,
    accent: str,
    graph: str,
    *,
    outro: bool = False,
) -> dict[str, Any]:
    return {
        "id": scene_id,
        "start": round(start, 3),
        "duration": round(duration, 3),
        "effectGraphPreset": graph,
        "layers": [
            {"type": "animated_background", "start": 0, "duration": duration, "color": accent, "opacity": 0.08, "speed": 120},
            {"type": "particle", "start": 0, "duration": duration, "color": "#ffffff", "opacity": 0.28, "count": 22},
            {
                "type": "text",
                "text": title,
                "x": "center",
                "y": int(height * (0.38 if not outro else 0.42)),
                "fontSize": int(width * 0.07),
                "color": "#ffffff",
                "strokeColor": "#000000",
                "strokeWidth": 4,
                "animation": {"in": "zoomIn", "out": "fade", "duration": 0.45},
            },
            {
                "type": "text",
                "text": subtitle,
                "x": "center",
                "y": int(height * 0.52),
                "fontSize": int(width * 0.035),
                "color": accent,
                "strokeColor": "#000000",
                "strokeWidth": 2,
                "animation": {"in": "slideUp", "out": "fade", "duration": 0.5},
            },
            {"type": "progress", "start": 0.2, "duration": max(duration - 0.4, 0.3), "x": "center", "y": int(height * 0.82), "width": int(width * 0.54), "height": 10, "color": accent},
        ],
        "transitionOut": {"type": "zoom", "duration": min(0.35, duration / 4)},
    }


def _feature_card(scene_id: str, start: float, duration: float, title: str, subtitle: str, width: int, height: int, accent: str) -> dict[str, Any]:
    return {
        "id": scene_id,
        "start": round(start, 3),
        "duration": round(duration, 3),
        "effectGraphPreset": "premium_red_black",
        "postProcessing": {"glow": 0.25, "vignette": 0.4},
        "layers": [
            {"type": "shape", "start": 0, "duration": duration, "x": int(width * 0.08), "y": int(height * 0.24), "width": int(width * 0.84), "height": int(height * 0.42), "color": "#05070d", "opacity": 0.68, "animation": {"in": "fade", "out": "fade", "duration": 0.25}},
            {"type": "hud", "start": 0.1, "duration": max(duration - 0.2, 0.2), "x": int(width * 0.09), "y": int(height * 0.08), "title": "SYSTEM CHECK", "subtitle": "local analysis", "boxColor": "#000000bb", "color": accent},
            {
                "type": "lower_third",
                "start": 0.2,
                "duration": max(duration - 0.3, 0.2),
                "x": int(width * 0.12),
                "y": int(height * 0.7),
                "width": int(width * 0.76),
                "height": int(height * 0.12),
                "title": title,
                "subtitle": subtitle,
                "boxColor": "#09090bcc",
                "color": "#ffffff",
                "subtitleColor": accent,
                "animation": {"in": "slideUp", "out": "fade", "duration": 0.35},
            },
            {"type": "waveform", "start": 0.15, "duration": max(duration - 0.3, 0.2), "x": int(width * 0.16), "y": int(height * 0.62), "height": int(height * 0.045), "color": accent, "bars": 34},
        ],
        "transitionOut": {"type": "crossfade", "duration": min(0.35, duration / 4)},
    }


def _title_from_prompt(prompt: str) -> str:
    words = [word.strip(".,!?;:") for word in prompt.split() if word.strip(".,!?;:")]
    if not words:
        return "CINEMATIC INTRO"
    if "hype" in prompt.lower():
        return "HYPE INTRO"
    return " ".join(words[:4]).upper()


def _retime(scenes: list[dict[str, Any]], duration: float) -> None:
    cursor = 0.0
    for index, scene in enumerate(scenes):
        scene["start"] = round(cursor, 3)
        if index == len(scenes) - 1:
            scene["duration"] = round(max(duration - cursor, 0.3), 3)
            scene.pop("transitionOut", None)
        cursor += float(scene["duration"])
