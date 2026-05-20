from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from schema.validator import validate_project
from utils.media import media_duration


STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "clean": {
        "background": "#070b12",
        "accent": "#38bdf8",
        "titleColor": "#ffffff",
        "mutedColor": "#cbd5e1",
        "boxColor": "#020617cc",
        "brightness": 0.01,
        "contrast": 1.06,
        "transition": {"type": "crossfade", "duration": 0.55},
    },
    "cinematic": {
        "background": "#04060a",
        "accent": "#f8fafc",
        "titleColor": "#ffffff",
        "mutedColor": "#d1d5db",
        "boxColor": "#000000b8",
        "brightness": -0.015,
        "contrast": 1.12,
        "transition": {"type": "crossfade", "duration": 0.7},
    },
    "red_black": {
        "background": "#050000",
        "accent": "#ef4444",
        "titleColor": "#ffffff",
        "mutedColor": "#fecaca",
        "boxColor": "#160000cc",
        "brightness": -0.02,
        "contrast": 1.16,
        "transition": {"type": "fadeToBlack", "duration": 0.55},
    },
}


def create_quick_project(
    recording: Path,
    *,
    music: Path | None = None,
    logo: Path | None = None,
    title: str = "Automatic Edit",
    caption: str = "Generated from local media.",
    instructions: str = "",
    style: str = "clean",
    duration: float | None = None,
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
    output_path: Path | None = None,
) -> dict[str, Any]:
    recording = recording.resolve()
    if not recording.exists():
        raise FileNotFoundError(f"Recording not found: {recording}")
    if recording.suffix.lower() != ".mp4":
        raise ValueError("MVP 0.1 quick-create accepts one .mp4 recording. Broader import support comes after the core pipeline is stable.")

    music = music.resolve() if music else None
    logo = logo.resolve() if logo else None
    if music and not music.exists():
        raise FileNotFoundError(f"Music file not found: {music}")
    if logo and not logo.exists():
        raise FileNotFoundError(f"Logo file not found: {logo}")

    style_config = _style(style)
    source_duration = media_duration(recording)
    target_duration = _target_duration(duration, source_duration)
    intro_duration = 2.2 if logo else 1.8
    main_duration = max(target_duration - intro_duration, 1.0)

    assets: dict[str, str] = {"recording": str(recording)}
    if music:
        assets["music"] = str(music)
    if logo:
        assets["logo"] = str(logo)

    project = {
        "metadata": {
            "mode": "mvp_0_1_quick_create",
            "instructions": instructions,
            "sourceRecording": str(recording),
            "createdAt": _now(),
            "milestone": {
                "version": "0.1",
                "phase": "core_render_pipeline",
                "features": [
                    "json_generation",
                    "schema_validation",
                    "asset_loading",
                    "text_overlay",
                    "image_overlay" if logo else "image_overlay_optional",
                    "video_trim",
                    "simple_zoom",
                    "transition",
                    "audio" if music else "audio_optional",
                    "basic_color_grade",
                    "manual_caption",
                ],
            },
        },
        "project": {
            "width": width,
            "height": height,
            "fps": fps,
            "duration": round(target_duration, 3),
            "background": style_config["background"],
            "crf": 18,
        },
        "assets": assets,
        "timeline": [
            _intro_scene(title, caption, bool(logo), intro_duration, width, height, style_config),
            _main_scene(main_duration, intro_duration, source_duration, width, height, style_config, title, caption),
        ],
        "audio": _audio_tracks(music is not None, target_duration),
        "captions": [
            {"text": caption, "start": round(intro_duration + 0.45, 3), "duration": min(3.0, max(main_duration - 0.7, 0.8))}
        ],
    }

    validate_project(project)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
    return project


def _style(style: str) -> dict[str, Any]:
    key = style.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in STYLE_PRESETS:
        valid = ", ".join(sorted(STYLE_PRESETS))
        raise ValueError(f"Unknown MVP style '{style}'. Expected one of: {valid}")
    return STYLE_PRESETS[key]


def _target_duration(requested: float | None, source_duration: float) -> float:
    if requested and requested > 0:
        return max(4.0, min(float(requested), max(source_duration + 2.2, 4.0)))
    if source_duration > 0:
        return max(5.0, min(source_duration + 2.2, 12.0))
    return 8.0


def _intro_scene(title: str, caption: str, has_logo: bool, duration: float, width: int, height: int, style: dict[str, Any]) -> dict[str, Any]:
    layers: list[dict[str, Any]] = [
        {"type": "shape", "x": 0, "y": 0, "width": width, "height": height, "color": style["background"], "opacity": 1},
        {"type": "shape", "x": 0, "y": int(height * 0.82), "width": width, "height": int(height * 0.18), "color": style["accent"], "opacity": 0.1},
    ]
    if has_logo:
        layers.append(
            {
                "type": "image",
                "asset": "logo",
                "x": "center",
                "y": int(height * 0.18),
                "scale": 0.22,
                "animation": {"in": "zoomIn", "out": "fade", "duration": 0.45},
            }
        )
    layers.extend(
        [
            {
                "type": "text",
                "text": title,
                "x": "center",
                "y": int(height * (0.48 if has_logo else 0.42)),
                "fontSize": int(height * 0.075),
                "color": style["titleColor"],
                "strokeColor": "#000000",
                "strokeWidth": 2,
                "shadowColor": "#000000",
                "shadowX": 3,
                "shadowY": 3,
                "animation": {"in": "typewriter", "out": "fade", "duration": 0.45},
            },
            {
                "type": "text",
                "text": caption,
                "x": "center",
                "y": int(height * 0.62),
                "fontSize": int(height * 0.037),
                "color": style["mutedColor"],
                "strokeColor": "#000000",
                "strokeWidth": 2,
                "box": True,
                "boxColor": style["boxColor"],
                "boxPadding": 12,
                "animation": {"in": "slideUp", "out": "fade", "duration": 0.4},
            },
        ]
    )
    return {
        "id": "mvp_intro",
        "start": 0,
        "duration": round(duration, 3),
        "layers": layers,
        "transitionOut": dict(style["transition"]),
    }


def _main_scene(
    duration: float,
    start: float,
    source_duration: float,
    width: int,
    height: int,
    style: dict[str, Any],
    title: str,
    caption: str,
) -> dict[str, Any]:
    trim_end = min(max(duration, 0.5), source_duration) if source_duration > 0 else duration
    return {
        "id": "mvp_main_clip",
        "start": round(start, 3),
        "duration": round(duration, 3),
        "layers": [
            {
                "type": "video",
                "asset": "recording",
                "x": 0,
                "y": 0,
                "width": width,
                "height": height,
                "trimStart": 0,
                "trimEnd": round(trim_end, 3),
                "brightness": style["brightness"],
                "contrast": style["contrast"],
                "camera": {
                    "mode": "dynamic_zoom",
                    "zoom": 1.08,
                    "duration": round(duration, 3),
                    "intensity": 0.22,
                },
            },
            {
                "type": "text",
                "text": title,
                "x": int(width * 0.05),
                "y": int(height * 0.08),
                "fontSize": int(height * 0.047),
                "color": style["titleColor"],
                "strokeColor": "#000000",
                "strokeWidth": 2,
                "box": True,
                "boxColor": style["boxColor"],
                "boxPadding": 14,
                "duration": min(3.0, duration),
                "animation": {"in": "slideRight", "out": "fade", "duration": 0.35},
            },
            {
                "type": "caption",
                "x": "center",
                "y": int(height * 0.86),
                "fontSize": int(height * 0.045),
                "color": "#ffffff",
                "strokeColor": "#000000",
                "strokeWidth": 2,
                "box": True,
                "boxColor": "#000000a8",
                "boxPadding": 12,
                "items": [{"text": caption, "start": 0.45, "duration": min(max(duration - 0.8, 0.8), 3.5)}],
            },
        ],
    }


def _audio_tracks(has_music: bool, duration: float) -> list[dict[str, Any]]:
    if not has_music:
        return []
    return [
        {
            "asset": "music",
            "start": 0,
            "duration": round(duration, 3),
            "volume": 0.38,
            "fadeIn": 0.35,
            "fadeOut": 0.9,
            "loop": True,
        }
    ]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
