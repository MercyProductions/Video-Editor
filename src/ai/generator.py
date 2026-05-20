from __future__ import annotations

import re
from typing import Any

from repair.repairer import repair_project_data
from templates.catalog import create_project_from_template


def generate_project_from_prompt(prompt: str, *, template: str | None = None, preset: str | None = None) -> dict[str, Any]:
    text = prompt.lower()
    selected_template = template or _choose_template(text)
    selected_preset = preset or _choose_preset(text, selected_template)
    project = create_project_from_template(selected_template, preset=selected_preset)

    duration = _duration_from_prompt(text)
    if duration:
        project["project"]["duration"] = duration
        _retime_scenes(project, duration)

    theme = _theme_from_prompt(text)
    if theme:
        project["project"]["background"] = theme["background"]
        _apply_theme(project, theme)

    if "fast cut" in text or "fast cuts" in text or "quick cut" in text:
        _make_fast_cuts(project)
    if "caption" in text or "captions" in text or "subtitle" in text:
        _ensure_captions(project, prompt)
    if "bass drop" in text or "drop" in text:
        _set_transitions(project, {"type": "zoom", "duration": 0.28})
    elif "slide" in text:
        _set_transitions(project, {"type": "slide", "duration": 0.45, "direction": "left"})

    project.setdefault("metadata", {})["aiPrompt"] = prompt
    project["metadata"]["aiGenerator"] = "local-rule-based-v1"

    repaired = repair_project_data(project)
    if not repaired.valid:
        raise ValueError("Generated JSON could not be repaired:\n" + "\n".join(repaired.errors_after))
    return repaired.data


def _choose_template(text: str) -> str:
    if "tiktok" in text or "reel" in text or "short" in text:
        return "tiktok_reels_short"
    if "gaming" in text or "montage" in text or "gameplay" in text:
        return "gaming_montage"
    if "product" in text or "promo" in text or "ad " in text:
        return "product_promo"
    if "lyric" in text or "song" in text:
        return "lyric_video"
    if "slideshow" in text or "photo" in text:
        return "slideshow"
    if "meme" in text:
        return "meme_edit"
    if "tutorial" in text or "how to" in text:
        return "tutorial_video"
    return "youtube_intro"


def _choose_preset(text: str, template: str) -> str | None:
    if "4k" in text or "cinematic" in text:
        return "cinematic_4k"
    if "discord" in text or "compressed" in text:
        return "discord_720p"
    if "square" in text:
        return "square"
    if "tiktok" in text or "reel" in text:
        return "tiktok_reels"
    if "shorts" in text:
        return "shorts"
    return None


def _duration_from_prompt(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(seconds|second|secs|sec|s)\b", text)
    if match:
        return float(match.group(1))
    match = re.search(r"(\d+(?:\.\d+)?)\s*(minutes|minute|mins|min)\b", text)
    if match:
        return float(match.group(1)) * 60
    return None


def _theme_from_prompt(text: str) -> dict[str, str] | None:
    themes = {
        "red": {"background": "#080000", "accent": "#ef4444"},
        "black": {"background": "#050505", "accent": "#ffffff"},
        "blue": {"background": "#020617", "accent": "#38bdf8"},
        "green": {"background": "#02140b", "accent": "#22c55e"},
        "purple": {"background": "#160022", "accent": "#c084fc"},
        "pink": {"background": "#220011", "accent": "#fb7185"},
        "gold": {"background": "#1f1600", "accent": "#f59e0b"},
    }
    for key, value in themes.items():
        if key in text:
            return value
    return None


def _apply_theme(project: dict[str, Any], theme: dict[str, str]) -> None:
    for scene in project.get("timeline", []):
        for layer in scene.get("layers", []):
            if layer.get("type") == "text" and layer.get("color") not in {"#ffffff", "#f8fafc"}:
                layer["color"] = theme["accent"]
            if layer.get("boxColor"):
                layer["boxColor"] = theme["background"] + "cc"


def _retime_scenes(project: dict[str, Any], duration: float) -> None:
    timeline = project.get("timeline", [])
    if not timeline:
        return
    per_scene = duration / len(timeline)
    cursor = 0.0
    for index, scene in enumerate(timeline):
        scene["start"] = round(cursor, 3)
        scene["duration"] = round(duration - cursor if index == len(timeline) - 1 else per_scene, 3)
        cursor += per_scene


def _make_fast_cuts(project: dict[str, Any]) -> None:
    timeline = project.get("timeline", [])
    duration = float(project.get("project", {}).get("duration", 12))
    video_assets = [
        key
        for key, path in project.get("assets", {}).items()
        if str(path).lower().endswith((".mp4", ".mov", ".mkv", ".webm"))
    ]
    if len(video_assets) < 3:
        video_assets.extend([f"clip{i}" for i in range(len(video_assets) + 1, 5)])
        for asset in video_assets:
            project.setdefault("assets", {}).setdefault(asset, f"assets/{asset}.mp4")

    cut_count = max(4, min(8, int(duration // 2)))
    cut_duration = duration / cut_count
    new_timeline = []
    for index in range(cut_count):
        asset = video_assets[index % len(video_assets)]
        new_timeline.append(
            {
                "id": f"fast_cut_{index + 1}",
                "start": round(index * cut_duration, 3),
                "duration": round(cut_duration, 3),
                "layers": [
                    {"type": "video", "asset": asset, "x": 0, "y": 0, "width": project["project"]["width"], "height": project["project"]["height"], "contrast": 1.15},
                    {"type": "text", "text": f"BEAT {index + 1}", "x": 80, "y": 80, "fontSize": 54, "color": "#ffffff", "strokeColor": "#000000", "strokeWidth": 3, "animation": {"in": "shake", "out": "fade", "duration": 0.25}},
                ],
                "transitionOut": {"type": "zoom", "duration": 0.2},
            }
        )
    new_timeline[-1].pop("transitionOut", None)
    project["timeline"] = new_timeline


def _ensure_captions(project: dict[str, Any], prompt: str) -> None:
    for scene in project.get("timeline", []):
        has_caption = any(layer.get("type") in {"caption", "captions"} for layer in scene.get("layers", []))
        if has_caption:
            continue
        scene.setdefault("layers", []).append(
            {
                "type": "caption",
                "x": "center",
                "y": "bottom",
                "fontSize": 44,
                "color": "#ffffff",
                "strokeColor": "#000000",
                "strokeWidth": 3,
                "box": True,
                "boxColor": "#00000099",
                "boxPadding": 14,
                "items": [{"text": _caption_text(prompt), "start": 0.4, "duration": max(float(scene.get("duration", 3)) - 0.8, 1)}],
            }
        )


def _caption_text(prompt: str) -> str:
    cleaned = prompt.strip().strip("\"'")
    if len(cleaned) <= 60:
        return cleaned
    return cleaned[:57].rstrip() + "..."


def _set_transitions(project: dict[str, Any], transition: dict[str, Any]) -> None:
    timeline = project.get("timeline", [])
    for scene in timeline[:-1]:
        scene["transitionOut"] = dict(transition)
