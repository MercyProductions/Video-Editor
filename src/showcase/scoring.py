from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any


def score_showcase(project: dict[str, Any], analysis: dict[str, Any], spec: dict[str, Any], profile: dict[str, Any], *, output_path: Path | None = None) -> dict[str, Any]:
    timeline = project.get("timeline", [])
    scenes = [scene for scene in timeline if str(scene.get("id", "")).startswith("showcase_")]
    duration = float(project.get("project", {}).get("duration", 0) or 0)
    scores = {
        "pacing": _score_pacing(scenes, duration, spec),
        "readability": _score_readability(project, analysis),
        "focusClarity": _score_focus_clarity(project, analysis),
        "deadTime": _score_dead_time(analysis),
        "lightingStrength": _score_lighting(profile, spec),
        "transitionQuality": _score_transitions(timeline, profile),
        "brandConsistency": _score_brand(project, spec, profile),
    }
    overall = round(statistics.mean(scores.values()), 3) if scores else 0
    warnings = _warnings(scores, project, analysis, spec)
    report = {
        "format": "automatic-video-editor-showcase-score",
        "createdAt": _now(),
        "overall": overall,
        "scores": scores,
        "warnings": warnings,
        "readyForPreview": overall >= 0.62 and not any(item["severity"] == "error" for item in warnings),
        "summary": _summary(scores, warnings),
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _score_pacing(scenes: list[dict[str, Any]], duration: float, spec: dict[str, Any]) -> float:
    if not scenes or duration <= 0:
        return 0.4
    target = float(spec.get("duration") or duration)
    durations = [float(scene.get("duration", 0) or 0) for scene in scenes]
    avg_scene = statistics.mean(durations)
    pace = str(spec.get("pace", "medium_fast"))
    ideal = {"fast": 2.6, "medium_fast": 3.4, "medium": 4.2, "slow": 5.0}.get(pace, 3.6)
    scene_score = max(0.0, 1 - abs(avg_scene - ideal) / max(ideal, 1))
    duration_score = max(0.0, 1 - abs(duration - target) / max(target, 1))
    return round(scene_score * 0.58 + duration_score * 0.42, 3)


def _score_readability(project: dict[str, Any], analysis: dict[str, Any]) -> float:
    text_layers = []
    caption_layers = []
    for scene in project.get("timeline", []):
        for layer in scene.get("layers", []):
            if layer.get("type") == "text":
                text_layers.append(layer)
            if layer.get("type") == "caption":
                caption_layers.append(layer)
    protected = sum(1 for layer in caption_layers if layer.get("box") and layer.get("strokeWidth", 0) >= 2)
    text_heavy_count = int(analysis.get("summary", {}).get("textHeavyCount", 0) or 0)
    base = 0.72 + min(0.18, protected * 0.04)
    if text_heavy_count > 8:
        base -= 0.14
    return round(max(0.0, min(1.0, base + min(len(text_layers), 6) * 0.012)), 3)


def _score_focus_clarity(project: dict[str, Any], analysis: dict[str, Any]) -> float:
    focus_count = int(analysis.get("summary", {}).get("focusEventCount", 0) or 0)
    focus_layers = 0
    for scene in project.get("timeline", []):
        for layer in scene.get("layers", []):
            if layer.get("type") == "shape" and float(layer.get("opacity", 0) or 0) <= 0.22:
                focus_layers += 1
    return round(min(1.0, 0.42 + min(focus_count, 8) * 0.055 + min(focus_layers, 8) * 0.035), 3)


def _score_dead_time(analysis: dict[str, Any]) -> float:
    duration = max(float(analysis.get("duration", 0) or 0), 1)
    idle = float(analysis.get("summary", {}).get("idleSeconds", 0) or 0)
    recommended = len(analysis.get("deadTimeRemoval", {}).get("recommendedCuts", []))
    score = 1 - min(0.55, idle / duration)
    if recommended:
        score -= min(0.18, recommended * 0.035)
    return round(max(0.0, min(1.0, score)), 3)


def _score_lighting(profile: dict[str, Any], spec: dict[str, Any]) -> float:
    requested = spec.get("lighting", {})
    intensity = float(profile.get("lightingIntensity", requested.get("intensity", 0.3)) or 0.3)
    target = float(requested.get("intensity", intensity) or intensity)
    score = 1 - abs(intensity - target) / 0.8
    if requested.get("theme") == "red_black" and str(profile.get("accent", "")).lower() not in {"#ef4444", "#dc2626", "#ff0000"}:
        score -= 0.2
    return round(max(0.0, min(1.0, score)), 3)


def _score_transitions(timeline: list[dict[str, Any]], profile: dict[str, Any]) -> float:
    transitions = [scene.get("transitionOut", {}) for scene in timeline[:-1] if scene.get("transitionOut")]
    if not transitions:
        return 0.55
    durations = [float(item.get("duration", 0) or 0) for item in transitions]
    avg = statistics.mean(durations)
    repetition = max((sum(1 for item in transitions if item.get("type") == kind) for kind in {str(item.get("type")) for item in transitions}), default=0) / max(len(transitions), 1)
    score = 0.82 - max(0, repetition - 0.75) * 0.32 - max(0, avg - 0.8) * 0.18
    if float(profile.get("transitionIntensity", 0.4) or 0.4) > 0.65 and any(item.get("type") == "zoom" for item in transitions):
        score += 0.08
    return round(max(0.0, min(1.0, score)), 3)


def _score_brand(project: dict[str, Any], spec: dict[str, Any], profile: dict[str, Any]) -> float:
    product = str(spec.get("productName") or project.get("metadata", {}).get("productName") or "")
    has_logo = "logo" in project.get("assets", {})
    accent = profile.get("accent")
    has_product_text = any(product and product in str(layer.get("text", "")) for scene in project.get("timeline", []) for layer in scene.get("layers", []))
    score = 0.55 + (0.18 if has_logo else 0) + (0.17 if has_product_text else 0) + (0.1 if accent else 0)
    return round(max(0.0, min(1.0, score)), 3)


def _warnings(scores: dict[str, float], project: dict[str, Any], analysis: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, str]]:
    warnings = []
    for key, value in scores.items():
        if value < 0.55:
            warnings.append({"severity": "warning", "area": key, "message": f"{key} score is low ({value}). Review before final export."})
    if spec.get("mustShow") and len(project.get("timeline", [])) < len(spec.get("mustShow", [])) + 2:
        warnings.append({"severity": "warning", "area": "mustShow", "message": "There may not be enough scenes to represent every required focus target."})
    if analysis.get("source", {}).get("issues"):
        warnings.append({"severity": "info", "area": "source", "message": "Source recording has analysis notes; inspect the desktop analysis report."})
    return warnings


def _summary(scores: dict[str, float], warnings: list[dict[str, str]]) -> str:
    weakest = min(scores.items(), key=lambda item: item[1])[0] if scores else "unknown"
    return f"Showcase score is strongest where scores are near 1.0; weakest area is {weakest}. Warnings: {len(warnings)}."


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
