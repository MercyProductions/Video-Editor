from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from assets.intelligence import analyze_asset_library


def run_quality_check(project_path: Path, *, output_path: Path | None = None) -> dict[str, Any]:
    project_path = project_path.resolve()
    data = json.loads(project_path.read_text(encoding="utf-8"))
    assets = analyze_asset_library(project_path, project_data=data)
    issues = []
    settings = data.get("project", {})
    width = int(settings.get("width", 1920))
    height = int(settings.get("height", 1080))
    _check_assets(issues, assets, width, height)
    _check_audio(issues, data, assets)
    _check_text_and_captions(issues, data, width, height)
    _check_export_settings(issues, data)
    result = {
        "project": str(project_path),
        "passed": not any(issue["severity"] == "error" for issue in issues),
        "issueCount": len(issues),
        "issues": issues,
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def _check_assets(issues: list[dict[str, Any]], report: dict[str, Any], width: int, height: int) -> None:
    for asset in report.get("assets", []):
        if not asset.get("exists"):
            issues.append({"severity": "error", "asset": asset["key"], "message": "Missing asset."})
            continue
        resolution = asset.get("resolution") or {}
        if asset.get("type") in {"video", "image"} and resolution:
            if int(resolution.get("width", 0)) < width * 0.55 or int(resolution.get("height", 0)) < height * 0.55:
                issues.append({"severity": "warning", "asset": asset["key"], "message": "Asset resolution is low for the export size."})
        if asset.get("type") == "audio" and (asset.get("loudness") or {}).get("peak", 0) > 0.9:
            issues.append({"severity": "warning", "asset": asset["key"], "message": "Possible audio clipping detected."})


def _check_audio(issues: list[dict[str, Any]], project: dict[str, Any], assets: dict[str, Any]) -> None:
    if not project.get("audio"):
        issues.append({"severity": "info", "message": "Project has no music or sound effects."})
    video_assets = [asset for asset in assets.get("assets", []) if asset.get("type") == "video"]
    if video_assets and not project.get("audio"):
        issues.append({"severity": "warning", "message": "Video edit has no dedicated audio track."})


def _check_text_and_captions(issues: list[dict[str, Any]], project: dict[str, Any], width: int, height: int) -> None:
    background = project.get("project", {}).get("background", "#000000")
    for scene in project.get("timeline", []):
        for layer in scene.get("layers", []):
            if layer.get("type") == "text":
                _check_position(issues, scene, layer, width, height)
                if _contrast_ratio(str(layer.get("color", "#ffffff")), str(background)) < 3.0:
                    issues.append({"severity": "warning", "scene": scene.get("id"), "message": "Text contrast may be unreadable."})
            if layer.get("type") in {"caption", "captions"}:
                for item in layer.get("items", []):
                    duration = float(item.get("duration", max(float(item.get("end", 0)) - float(item.get("start", 0)), 0.01)) or 0.01)
                    words = len(str(item.get("text", "")).split())
                    if words / duration > 4.5:
                        issues.append({"severity": "warning", "scene": scene.get("id"), "message": "Caption is too fast to read."})


def _check_position(issues: list[dict[str, Any]], scene: dict[str, Any], layer: dict[str, Any], width: int, height: int) -> None:
    x = layer.get("x")
    y = layer.get("y")
    if isinstance(x, (int, float)) and not (width * 0.05 <= float(x) <= width * 0.95):
        issues.append({"severity": "warning", "scene": scene.get("id"), "message": "Text x position is outside the title safe zone."})
    if isinstance(y, (int, float)) and not (height * 0.05 <= float(y) <= height * 0.95):
        issues.append({"severity": "warning", "scene": scene.get("id"), "message": "Text y position is outside the title safe zone."})


def _check_export_settings(issues: list[dict[str, Any]], project: dict[str, Any]) -> None:
    settings = project.get("project", {})
    if int(settings.get("fps", 30)) > 120:
        issues.append({"severity": "warning", "message": "FPS is unusually high for social export."})
    if int(settings.get("width", 0)) % 2 or int(settings.get("height", 0)) % 2:
        issues.append({"severity": "error", "message": "Export width and height must be even numbers for H.264."})
    preset = project.get("exportPreset")
    if preset == "discord_720p" and int(settings.get("width", 0)) > 1280:
        issues.append({"severity": "warning", "message": "Discord preset should stay at or below 720p."})


def _contrast_ratio(foreground: str, background: str) -> float:
    fg = _luminance(_hex_to_rgb(foreground))
    bg = _luminance(_hex_to_rgb(background))
    lighter = max(fg, bg)
    darker = min(fg, bg)
    return (lighter + 0.05) / (darker + 0.05)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    clean = value.strip().lstrip("#")[:6]
    if len(clean) != 6:
        return (255, 255, 255)
    return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))


def _luminance(rgb: tuple[int, int, int]) -> float:
    channels = []
    for value in rgb:
        normalized = value / 255
        channels.append(normalized / 12.92 if normalized <= 0.03928 else ((normalized + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
