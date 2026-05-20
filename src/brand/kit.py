from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


def create_brand_kit(output_path: Path) -> dict[str, Any]:
    kit = {
        "name": "Aegis Brand Kit",
        "logo": "assets/logo.png",
        "colors": {
            "primary": "#e11d48",
            "secondary": "#111827",
            "text": "#ffffff",
            "background": "#050505"
        },
        "fonts": {
            "heading": "Arial",
            "body": "Arial"
        },
        "intro": {
            "enabled": True,
            "text": "Aegis",
            "duration": 2
        },
        "outro": {
            "enabled": True,
            "text": "Follow for more",
            "duration": 2
        },
        "watermark": {
            "enabled": True,
            "asset": "brand_logo",
            "scale": 0.12,
            "x": "right",
            "y": "top",
            "opacity": 0.65
        },
        "captionStyle": {
            "fontSize": 52,
            "color": "#ffffff",
            "strokeColor": "#000000",
            "strokeWidth": 4,
            "box": True,
            "boxColor": "#00000099"
        },
        "defaultTransition": {
            "type": "crossfade",
            "duration": 0.35
        }
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(kit, indent=2) + "\n", encoding="utf-8")
    return kit


def apply_brand_kit(project: dict[str, Any], brand_kit: dict[str, Any]) -> dict[str, Any]:
    branded = copy.deepcopy(project)
    branded["brandKit"] = brand_kit
    branded.setdefault("metadata", {})["brandKitName"] = brand_kit.get("name")
    colors = brand_kit.get("colors", {}) if isinstance(brand_kit.get("colors"), dict) else {}
    if colors.get("background"):
        branded.setdefault("project", {})["background"] = colors["background"]
    if brand_kit.get("logo"):
        branded.setdefault("assets", {})["brand_logo"] = str(brand_kit["logo"])
    _apply_default_transitions(branded, brand_kit.get("defaultTransition"))
    _apply_text_and_caption_style(branded, brand_kit)
    _add_intro_outro(branded, brand_kit)
    _add_watermark(branded, brand_kit.get("watermark"))
    _retime(branded)
    return branded


def _apply_default_transitions(project: dict[str, Any], transition: Any) -> None:
    if not isinstance(transition, dict):
        return
    timeline = project.get("timeline", [])
    for scene in timeline[:-1]:
        scene.setdefault("transitionOut", copy.deepcopy(transition))


def _apply_text_and_caption_style(project: dict[str, Any], brand_kit: dict[str, Any]) -> None:
    colors = brand_kit.get("colors", {}) if isinstance(brand_kit.get("colors"), dict) else {}
    fonts = brand_kit.get("fonts", {}) if isinstance(brand_kit.get("fonts"), dict) else {}
    caption_style = brand_kit.get("captionStyle", {}) if isinstance(brand_kit.get("captionStyle"), dict) else {}
    for scene in project.get("timeline", []):
        for layer in scene.get("layers", []):
            if layer.get("type") == "text":
                layer.setdefault("color", colors.get("text", "#ffffff"))
                layer.setdefault("fontFamily", fonts.get("heading", "Arial"))
            if layer.get("type") in {"caption", "captions"}:
                for key, value in caption_style.items():
                    layer.setdefault(key, value)


def _add_intro_outro(project: dict[str, Any], brand_kit: dict[str, Any]) -> None:
    timeline = project.setdefault("timeline", [])
    intro = brand_kit.get("intro", {})
    outro = brand_kit.get("outro", {})
    if isinstance(intro, dict) and intro.get("enabled"):
        duration = float(intro.get("duration", 2))
        timeline.insert(0, _brand_scene("brand_intro", str(intro.get("text", brand_kit.get("name", "Intro"))), duration))
    if isinstance(outro, dict) and outro.get("enabled"):
        duration = float(outro.get("duration", 2))
        timeline.append(_brand_scene("brand_outro", str(outro.get("text", "Thanks for watching")), duration))


def _brand_scene(scene_id: str, text: str, duration: float) -> dict[str, Any]:
    return {
        "id": scene_id,
        "start": 0,
        "duration": duration,
        "layers": [
            {
                "type": "text",
                "text": text,
                "layout": "center",
                "fontSize": 72,
                "color": "#ffffff",
                "strokeColor": "#000000",
                "strokeWidth": 3,
                "animation": {"in": "fade", "out": "fade", "duration": 0.45}
            }
        ],
        "transitionOut": {"type": "crossfade", "duration": 0.35}
    }


def _add_watermark(project: dict[str, Any], watermark: Any) -> None:
    if not isinstance(watermark, dict) or not watermark.get("enabled"):
        return
    layer = {
        "type": "image",
        "asset": watermark.get("asset", "brand_logo"),
        "x": watermark.get("x", "right"),
        "y": watermark.get("y", "top"),
        "scale": watermark.get("scale", 0.12),
        "opacity": watermark.get("opacity", 0.65)
    }
    for scene in project.get("timeline", []):
        if scene.get("id") in {"brand_intro", "brand_outro"}:
            continue
        scene.setdefault("layers", []).append(copy.deepcopy(layer))


def _retime(project: dict[str, Any]) -> None:
    cursor = 0.0
    for scene in project.get("timeline", []):
        scene["start"] = round(cursor, 3)
        cursor += float(scene.get("duration", 0))
    project.setdefault("project", {})["duration"] = round(cursor, 3)
