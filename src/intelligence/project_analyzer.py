from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from intelligence.beat_sync import analyze_audio
from utils.media import media_duration


def analyze_project(project_path: Path, *, rendered_video: Path | None = None, output_path: Path | None = None) -> dict[str, Any]:
    project = json.loads(project_path.read_text(encoding="utf-8"))
    timeline = project.get("timeline", [])
    duration = float(project.get("project", {}).get("duration", 0) or 0)
    scene_durations = [float(scene.get("duration", 0) or 0) for scene in timeline]
    transitions = Counter(_transition_type(scene) for scene in timeline if scene.get("transitionOut"))
    caption_words = _caption_word_count(project)
    effects = Counter(_layer_effects(project))
    boring = _boring_sections(timeline)
    audio_report = _audio_analysis(project_path, project)
    rendered_duration = media_duration(rendered_video) if rendered_video and rendered_video.exists() else None

    report = {
        "project": str(project_path.resolve()),
        "renderedVideo": str(rendered_video.resolve()) if rendered_video else None,
        "duration": duration,
        "renderedDuration": round(rendered_duration, 3) if rendered_duration else None,
        "sceneCount": len(timeline),
        "pacing": {
            "averageSceneDuration": round(sum(scene_durations) / len(scene_durations), 3) if scene_durations else 0,
            "shortSceneCount": sum(1 for value in scene_durations if value < 1.0),
            "longSceneCount": sum(1 for value in scene_durations if value > 6.0),
            "score": _pacing_score(scene_durations),
        },
        "captions": {
            "wordCount": caption_words,
            "wordsPerSecond": round(caption_words / max(duration, 0.001), 2),
            "density": _caption_density_label(caption_words, duration),
        },
        "transitions": {
            "counts": dict(transitions),
            "spamRisk": _transition_spam_risk(transitions, len(timeline)),
        },
        "effects": dict(effects),
        "audio": audio_report,
        "boringSections": boring,
        "warnings": _warnings(scene_durations, caption_words, duration, transitions, boring, rendered_duration),
        "recommendations": _recommendations(scene_durations, caption_words, duration, transitions, boring),
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _transition_type(scene: dict[str, Any]) -> str:
    transition = scene.get("transitionOut")
    if isinstance(transition, dict):
        return str(transition.get("type", "cut"))
    return "cut"


def _caption_word_count(project: dict[str, Any]) -> int:
    count = 0
    for item in project.get("captions", []):
        count += len(str(item.get("text", "")).split())
    for scene in project.get("timeline", []):
        for layer in scene.get("layers", []):
            if layer.get("type") in {"caption", "captions"}:
                if layer.get("items"):
                    count += sum(len(str(item.get("text", "")).split()) for item in layer.get("items", []))
                else:
                    count += len(str(layer.get("text", "")).split())
    return count


def _layer_effects(project: dict[str, Any]) -> list[str]:
    names = []
    for scene in project.get("timeline", []):
        if scene.get("effectGraphPreset"):
            names.append(f"effectGraph:{scene['effectGraphPreset']}")
        if scene.get("postProcessing"):
            names.extend(f"post:{key}" for key in scene["postProcessing"].keys())
        for layer in scene.get("layers", []):
            names.append(f"layer:{layer.get('type')}")
            effects = layer.get("effects")
            if isinstance(effects, str):
                names.append(effects)
            elif isinstance(effects, list):
                names.extend(str(effect) for effect in effects)
            camera = layer.get("camera")
            if isinstance(camera, dict):
                names.append(f"camera:{camera.get('mode', camera.get('type', 'cinematic_sway'))}")
    return names


def _boring_sections(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections = []
    for scene in timeline:
        duration = float(scene.get("duration", 0) or 0)
        layers = scene.get("layers", [])
        has_media = any(layer.get("type") in {"video", "image"} for layer in layers)
        has_text = any(layer.get("type") in {"text", "caption", "captions", "lower_third", "hud"} for layer in layers)
        has_motion_graphics = any(layer.get("type") in {"animated_background", "particle", "progress", "waveform"} for layer in layers)
        if duration >= 4 and not (has_media or has_text):
            sections.append({"scene": scene.get("id"), "reason": "long empty section", "duration": duration})
        elif duration >= 5.5 and not has_motion_graphics and not scene.get("transitionOut"):
            sections.append({"scene": scene.get("id"), "reason": "long static section", "duration": duration})
    return sections


def _audio_analysis(project_path: Path, project: dict[str, Any]) -> dict[str, Any] | None:
    audio = project.get("audio") or []
    assets = project.get("assets") or {}
    if not audio:
        return None
    first = audio[0]
    asset = assets.get(first.get("asset"))
    if not asset:
        return None
    path = Path(asset)
    if not path.is_absolute():
        path = project_path.parent / path
    if not path.exists():
        return {"warning": f"Audio asset missing: {path}"}
    try:
        analysis = analyze_audio(path)
    except Exception as exc:
        return {"warning": str(exc)}
    return {
        "bpm": analysis.get("bpm"),
        "averageLoudness": analysis.get("averageLoudness"),
        "peakLoudness": analysis.get("peakLoudness"),
        "beatCount": len(analysis.get("beats", [])),
        "bassDropCount": len(analysis.get("bassDrops", [])),
    }


def _pacing_score(scene_durations: list[float]) -> int:
    if not scene_durations:
        return 0
    average = sum(scene_durations) / len(scene_durations)
    penalty = 0
    penalty += sum(12 for value in scene_durations if value > 7)
    penalty += sum(8 for value in scene_durations if value < 0.45)
    if average > 5.5:
        penalty += 15
    if average < 0.8:
        penalty += 10
    return max(0, min(100, 92 - penalty))


def _caption_density_label(words: int, duration: float) -> str:
    rate = words / max(duration, 0.001)
    if rate > 4.0:
        return "dense"
    if rate > 2.4:
        return "balanced"
    return "light"


def _transition_spam_risk(transitions: Counter[str], scene_count: int) -> str:
    if not transitions or scene_count < 4:
        return "low"
    most_common = transitions.most_common(1)[0]
    if most_common[1] / max(scene_count - 1, 1) > 0.75 and most_common[0] != "cut":
        return "high"
    if most_common[1] / max(scene_count - 1, 1) > 0.55:
        return "medium"
    return "low"


def _warnings(
    durations: list[float],
    words: int,
    duration: float,
    transitions: Counter[str],
    boring: list[dict[str, Any]],
    rendered_duration: float | None,
) -> list[str]:
    warnings = []
    if any(value > 8 for value in durations):
        warnings.append("One or more scenes are very long; pacing may drag.")
    if words / max(duration, 0.001) > 4.2:
        warnings.append("Caption density is high; viewers may not read everything.")
    if _transition_spam_risk(transitions, len(durations)) == "high":
        warnings.append("A single transition style dominates the edit.")
    if boring:
        warnings.append("Potential boring/static sections detected.")
    if rendered_duration and duration and abs(rendered_duration - duration) > 0.25:
        warnings.append("Rendered video duration differs from project duration.")
    return warnings


def _recommendations(
    durations: list[float],
    words: int,
    duration: float,
    transitions: Counter[str],
    boring: list[dict[str, Any]],
) -> list[str]:
    recs = []
    if any(value > 6 for value in durations):
        recs.append("Split long scenes or add camera movement to preserve energy.")
    if words / max(duration, 0.001) > 3.5:
        recs.append("Break captions into shorter phrases and emphasize fewer keywords.")
    if _transition_spam_risk(transitions, len(durations)) != "low":
        recs.append("Mix hard cuts with a few motivated cinematic transitions.")
    if boring:
        recs.append("Add overlays, b-roll, or progress graphics to static sections.")
    if not recs:
        recs.append("No major pacing or readability issues detected.")
    return recs
