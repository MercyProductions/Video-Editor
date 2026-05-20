from __future__ import annotations

from collections import Counter
from typing import Any


def suggest_scene_improvements(project: dict[str, Any]) -> dict[str, Any]:
    suggestions: list[dict[str, Any]] = []
    timeline = project.get("timeline", [])
    if not timeline:
        suggestions.append(_suggest("timeline", "Add scenes before rendering.", "error"))
    transition_counts = Counter()
    durations = [float(scene.get("duration", 0) or 0) for scene in timeline]
    average_duration = sum(durations) / len(durations) if durations else 0
    text_word_total = 0
    text_layer_count = 0
    for scene in timeline:
        layers = scene.get("layers", [])
        text_layers = [layer for layer in layers if layer.get("type") in {"text", "caption", "captions"}]
        media_layers = [layer for layer in layers if layer.get("type") in {"video", "image"}]
        transition = scene.get("transitionOut")
        if isinstance(transition, dict):
            transition_counts[str(transition.get("type", "cut"))] += 1
        if not text_layers and float(scene.get("duration", 0) or 0) >= 2.5:
            suggestions.append(_suggest(scene["id"], "Add a concise overlay or caption so this scene has a clear point.", "medium", "Scenes without text can feel visually empty unless the footage has an obvious payoff."))
        if not media_layers:
            suggestions.append(_suggest(scene["id"], "Add footage, image, or b-roll to avoid an empty title-card-only section.", "medium", "Title-only scenes work best as quick beats, not extended sections."))
        scene_duration = float(scene.get("duration", 0) or 0)
        if scene_duration > max(6, average_duration * 1.8):
            suggestions.append(_suggest(scene["id"], "Consider splitting this long scene or adding a zoom/beat hit.", "low", "The scene is much longer than the project rhythm, which can create dead space."))
        if scene_duration < 0.7:
            suggestions.append(_suggest(scene["id"], "Scene is extremely short; check whether captions and transitions remain readable.", "medium", "Very short scenes can feel like accidental flashes."))
        for layer in text_layers:
            text = str(layer.get("text", ""))
            text_word_total += len(text.split())
            text_layer_count += 1
            if len(text.split()) > 12:
                suggestions.append(_suggest(scene["id"], "Caption/text is wordy; split it for short-form readability.", "medium", "Short-form viewers need fewer words per beat, especially on vertical exports."))
            for item in layer.get("items", []) if isinstance(layer.get("items"), list) else []:
                words = len(str(item.get("text", "")).split())
                duration = float(item.get("duration", 0) or 0)
                if duration > 0 and words / duration > 4.2:
                    suggestions.append(_suggest(scene["id"], "Caption timing is likely too fast.", "medium", "The caption exceeds a comfortable words-per-second target."))
    repeated = [name for name, count in transition_counts.items() if count >= 4 and name != "cut"]
    for name in repeated:
        suggestions.append(_suggest("transitions", f"Transition '{name}' repeats often; mix in cuts or a softer crossfade.", "low", "Repeated transition language can make AI edits feel mechanical."))
    if durations:
        variance = sum((duration - average_duration) ** 2 for duration in durations) / len(durations)
        if average_duration > 4.5 and len(timeline) >= 3:
            suggestions.append(_suggest("pacing", "Average scene length is slow for short-form or showcase edits.", "medium", "Try shorter scenes or visible movement every 2-4 seconds."))
        if variance < 0.08 and len(timeline) >= 4:
            suggestions.append(_suggest("pacing", "Scene durations are very uniform; add one short accent beat or one longer payoff.", "low", "Intentional rhythm usually has a little variation."))
    if text_layer_count and text_word_total / text_layer_count > 10:
        suggestions.append(_suggest("text", "Project is text-heavy; consider splitting overlays and using fewer words per card.", "medium", "Dense text reduces cinematic feel and hurts readability."))
    if not suggestions:
        suggestions.append(_suggest("project", "No obvious empty sections found. Run a preview render to judge pacing.", "info", "Automated analysis passed the common structural checks."))
    return {
        "suggestionCount": len(suggestions),
        "suggestions": suggestions,
        "analysis": {
            "sceneCount": len(timeline),
            "averageSceneDuration": round(average_duration, 3),
            "transitionCounts": dict(transition_counts),
            "textLayerCount": text_layer_count,
        },
    }


def _suggest(target: str, message: str, severity: str, reason: str = "") -> dict[str, Any]:
    return {"target": target, "severity": severity, "message": message, "reason": reason}
