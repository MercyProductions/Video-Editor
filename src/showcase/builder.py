from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path
from typing import Any

from advanced import apply_advanced_cinematic_engine
from intelligence.beat_sync import analyze_audio
from showcase.analyzer import analyze_desktop_recording
from showcase.scoring import score_showcase
from showcase.spec import interpret_showcase_spec, load_manual_overrides
from showcase.styles import load_style_profile, resolve_showcase_style


def build_showcase_project(
    recording_path: Path,
    *,
    music_path: Path | None = None,
    logo_path: Path | None = None,
    style: str = "auto",
    style_profile: str | None = None,
    instructions: str = "",
    product_name: str | None = None,
    duration: float | None = None,
    manual_overrides: str | None = None,
    output_path: Path | None = None,
    analysis_output_path: Path | None = None,
    spec_output_path: Path | None = None,
    score_output_path: Path | None = None,
    advanced_output_path: Path | None = None,
) -> dict[str, Any]:
    recording_path = recording_path.resolve()
    music_path = music_path.resolve() if music_path else None
    logo_path = logo_path.resolve() if logo_path else None
    overrides = load_manual_overrides(manual_overrides)
    spec = interpret_showcase_spec(
        instructions,
        manual_overrides=overrides,
        product_name=product_name,
        requested_duration=duration,
        requested_style=style,
        music_available=music_path is not None,
    )
    style_overrides = load_style_profile(style_profile)
    profile_overrides = _profile_overrides_from_spec(spec, style_overrides)
    profile = resolve_showcase_style(str(spec.get("style") or style), instructions, profile_overrides)
    analysis = analyze_desktop_recording(recording_path, output_path=analysis_output_path)
    music_analysis = _safe_audio_analysis(music_path) if music_path and spec.get("musicSync", True) else None
    product = str(spec.get("productName") or product_name or _product_name_from_instructions(instructions) or recording_path.stem.replace("_", " ").replace("-", " ").title())
    target_width, target_height = _target_resolution(analysis)
    target_duration = _target_duration(float(analysis["duration"]), float(spec["duration"]) if spec.get("duration") else None, profile)
    segments = _select_segments(analysis, target_duration=target_duration, profile=profile, music_analysis=music_analysis, spec=spec)
    project = _project_from_segments(
        recording_path,
        segments,
        analysis=analysis,
        profile=profile,
        product_name=product,
        instructions=instructions,
        spec=spec,
        music_path=music_path,
        logo_path=logo_path,
        music_analysis=music_analysis,
        width=target_width,
        height=target_height,
    )
    advanced_result = apply_advanced_cinematic_engine(
        project,
        analysis=analysis,
        spec=spec,
        profile=profile,
        recording_path=recording_path,
        music_path=music_path,
        output_path=advanced_output_path,
    )
    project = advanced_result["project"]
    score = score_showcase(project, analysis, spec, profile, output_path=score_output_path)
    project.setdefault("metadata", {})["showcaseScore"] = score
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
    if spec_output_path:
        spec_output_path.parent.mkdir(parents=True, exist_ok=True)
        spec_output_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    return {
        "project": project,
        "analysis": analysis,
        "spec": spec,
        "score": score,
        "advancedReport": advanced_result["report"],
        "styleProfile": profile,
        "segments": segments,
        "musicAnalysis": music_analysis,
        "outputPath": str(output_path.resolve()) if output_path else None,
        "analysisPath": str(analysis_output_path.resolve()) if analysis_output_path else None,
        "specPath": str(spec_output_path.resolve()) if spec_output_path else None,
        "scorePath": str(score_output_path.resolve()) if score_output_path else None,
        "advancedPath": str(advanced_output_path.resolve()) if advanced_output_path else None,
    }


def _safe_audio_analysis(music_path: Path | None) -> dict[str, Any] | None:
    if not music_path:
        return None
    try:
        return analyze_audio(music_path)
    except Exception as exc:
        return {"audio": str(music_path), "beats": [], "bassDrops": [], "loudnessPeaks": [], "warnings": [str(exc)]}


def _profile_overrides_from_spec(spec: dict[str, Any], style_overrides: dict[str, Any] | None) -> dict[str, Any] | None:
    overrides = dict(style_overrides or {})
    if spec.get("pace"):
        overrides["pace"] = spec["pace"]
    lighting = spec.get("lighting")
    if isinstance(lighting, dict):
        overrides.setdefault("lighting", lighting)
        if lighting.get("intensity") is not None:
            overrides["lightingIntensity"] = lighting["intensity"]
        if lighting.get("theme") == "red_black":
            overrides.setdefault("accent", "#ef4444")
            overrides.setdefault("effectGraphPreset", "premium_red_black")
            overrides.setdefault("background", "#050000")
    audio = spec.get("audio")
    if isinstance(audio, dict) and audio.get("musicMood") == "subtle":
        overrides.setdefault("audioVolume", 0.24)
    return overrides or None


def _target_resolution(analysis: dict[str, Any]) -> tuple[int, int]:
    source = analysis.get("source", {})
    width = int(source.get("width") or 1920)
    height = int(source.get("height") or 1080)
    aspect = width / max(height, 1)
    if aspect < 0.8:
        return 1080, 1920
    if aspect < 1.2:
        return 1080, 1080
    return 1920 if width >= 1600 else 1280, 1080 if width >= 1600 else 720


def _target_duration(raw_duration: float, requested: float | None, profile: dict[str, Any]) -> float:
    if requested and requested > 0:
        return round(min(requested, max(raw_duration + 6, 8)), 3)
    pace = str(profile.get("pace", "medium"))
    ratio = {"slow": 0.78, "medium": 0.66, "medium_fast": 0.58, "fast": 0.48}.get(pace, 0.6)
    return round(max(8.0, min(45.0, raw_duration * ratio + 4.8)), 3)


def _select_segments(
    analysis: dict[str, Any],
    *,
    target_duration: float,
    profile: dict[str, Any],
    music_analysis: dict[str, Any] | None,
    spec: dict[str, Any],
) -> list[dict[str, Any]]:
    raw_duration = float(analysis.get("duration", 0) or 0)
    intro_outro = 4.6
    main_duration = max(2.0, min(raw_duration, target_duration - intro_outro))
    scene_duration = float(profile.get("sceneDuration", 3.8) or 3.8)
    scene_count = max(1, min(10, int(math.ceil(main_duration / max(scene_duration, 1.2)))))
    event_times = _event_times(analysis, music_analysis, spec)
    candidates = []
    for index, event in enumerate(event_times):
        start = max(0.0, float(event["time"]) - scene_duration * 0.38)
        end = min(raw_duration, start + scene_duration)
        if end - start < 0.7:
            continue
        if _overlaps_dead_time(start, end, analysis):
            start, end = _nudge_from_idle(start, end, analysis, raw_duration)
        if _overlaps_mistake_removal(start, end, analysis, spec):
            continue
        candidates.append({"start": round(start, 3), "end": round(end, 3), "focus": event, "score": float(event.get("score", 0.3))})

    if not candidates:
        step = raw_duration / scene_count if scene_count else raw_duration
        candidates = [
            {
                "start": round(index * step, 3),
                "end": round(min(index * step + scene_duration, raw_duration), 3),
                "focus": _nearest_focus(analysis, index * step + step * 0.5),
                "score": 0.2,
            }
            for index in range(scene_count)
        ]

    selected: list[dict[str, Any]] = []
    for candidate in sorted(candidates, key=lambda item: (-float(item["score"]), float(item["start"]))):
        if any(_overlap_ratio(candidate["start"], candidate["end"], item["start"], item["end"]) > 0.45 for item in selected):
            continue
        selected.append(candidate)
        if len(selected) >= scene_count:
            break
    selected.sort(key=lambda item: item["start"])

    selected = _trim_segments_to_duration(selected, main_duration)
    selected = _enforce_must_show_count(selected, analysis, spec, scene_count)

    for index, item in enumerate(selected, start=1):
        item["id"] = f"showcase_{index:02d}"
        item["duration"] = round(max(float(item["end"]) - float(item["start"]), 0.5), 3)
        item["role"] = _scene_role(index, len(selected), item)
        item["title"] = _segment_title(index, item, analysis, spec)
        item["caption"] = _segment_caption(index, item, analysis, spec)
        item["benefit"] = _segment_benefit(index, item, spec)
    return selected


def _trim_segments_to_duration(segments: list[dict[str, Any]], target_duration: float) -> list[dict[str, Any]]:
    selected = [dict(item) for item in segments]
    total = sum(float(item["end"]) - float(item["start"]) for item in selected)
    for item in reversed(selected):
        if total <= target_duration:
            break
        duration = float(item["end"]) - float(item["start"])
        reducible = max(duration - 0.8, 0)
        reduction = min(reducible, total - target_duration)
        if reduction > 0:
            item["end"] = round(float(item["end"]) - reduction, 3)
            total -= reduction
    while total > target_duration and len(selected) > 1:
        removed = min(selected, key=lambda item: (float(item.get("score", 0)), float(item["duration"]) if "duration" in item else float(item["end"]) - float(item["start"])))
        selected.remove(removed)
        total = sum(float(item["end"]) - float(item["start"]) for item in selected)
    return sorted(selected, key=lambda item: item["start"])


def _enforce_must_show_count(selected: list[dict[str, Any]], analysis: dict[str, Any], spec: dict[str, Any], scene_count: int) -> list[dict[str, Any]]:
    targets = spec.get("mustShow", [])
    if not targets or len(selected) >= min(len(targets), scene_count):
        return selected
    raw_duration = float(analysis.get("duration", 0) or 0)
    needed = min(len(targets), scene_count) - len(selected)
    step = raw_duration / max(needed + len(selected), 1)
    for index in range(needed):
        center = min(raw_duration, step * (index + 1))
        focus = _nearest_focus(analysis, center)
        duration = min(2.8, max(0.9, raw_duration - center))
        selected.append({"start": round(max(0, center - duration / 2), 3), "end": round(min(raw_duration, center + duration / 2), 3), "focus": {**focus, "target": targets[index]}, "score": 0.5})
    return sorted(selected, key=lambda item: item["start"])


def _scene_role(index: int, total: int, segment: dict[str, Any]) -> str:
    reason = str(segment.get("focus", {}).get("reason", "")).lower()
    if index == 1:
        return "feature_reveal"
    if "click" in reason or "control" in reason or "hover" in reason:
        return "interaction_highlight"
    if index == total:
        return "result_moment"
    return "transition"


def _event_times(analysis: dict[str, Any], music_analysis: dict[str, Any] | None, spec: dict[str, Any]) -> list[dict[str, Any]]:
    events = [dict(item) for item in analysis.get("importantUiFocusAreas", [])]
    for item in analysis.get("uiImportanceDetection", {}).get("clickedButtons", [])[:12]:
        events.append({"time": item["time"], "score": 0.72, "x": _rect_center(item.get("rect", {}), "x", analysis), "y": _rect_center(item.get("rect", {}), "y", analysis), "reason": "clicked button/control"})
    for item in analysis.get("cursorIntent", {}).get("slowHover", [])[:12]:
        events.append({"time": item["start"], "score": 0.5, "x": item.get("x", 0.5), "y": item.get("y", 0.5), "reason": "slow hover / important control"})
    for change in analysis.get("sceneChanges", [])[:12]:
        events.append({"time": change["time"], "score": 0.44, "x": 0.5, "y": 0.5, "reason": "scene change"})
    for click in analysis.get("clickTiming", [])[:16]:
        events.append({"time": click["time"], "score": 0.62, "x": click.get("x", 0.5), "y": click.get("y", 0.5), "reason": "click"})
    if music_analysis:
        for drop in music_analysis.get("bassDrops", [])[:10]:
            events.append({"time": drop["time"], "score": 0.38, "x": 0.5, "y": 0.5, "reason": "bass drop"})
        for peak in music_analysis.get("loudnessPeaks", [])[:10]:
            events.append({"time": peak["time"], "score": 0.28, "x": 0.5, "y": 0.5, "reason": "music peak"})
    for index, target in enumerate(spec.get("mustShow", [])[:6]):
        if events:
            source = events[min(index, len(events) - 1)]
            events.append({**source, "score": max(float(source.get("score", 0.3)), 0.66), "reason": f"manual focus target: {target}", "target": target})
    events = sorted(events, key=lambda item: (float(item.get("time", 0)), -float(item.get("score", 0))))
    deduped = []
    for item in events:
        if deduped and abs(float(item["time"]) - float(deduped[-1]["time"])) < 0.45:
            if float(item.get("score", 0)) > float(deduped[-1].get("score", 0)):
                deduped[-1] = item
            continue
        deduped.append(item)
    return deduped


def _rect_center(rect: dict[str, Any], axis: str, analysis: dict[str, Any]) -> float:
    source = analysis.get("source", {})
    denom = float(source.get("width" if axis == "x" else "height") or 1)
    start = float(rect.get(axis, 0) or 0)
    size = float(rect.get("width" if axis == "x" else "height", 0) or 0)
    return round(max(0.0, min(1.0, (start + size / 2) / denom)), 4)


def _overlaps_dead_time(start: float, end: float, analysis: dict[str, Any]) -> bool:
    duration = max(end - start, 0.001)
    for idle in analysis.get("idleMoments", []):
        overlap = max(0.0, min(end, float(idle["end"])) - max(start, float(idle["start"])))
        if overlap / duration > 0.55:
            return True
    return False


def _overlaps_mistake_removal(start: float, end: float, analysis: dict[str, Any], spec: dict[str, Any]) -> bool:
    requested = " ".join(str(item).lower() for item in spec.get("cutOut", []))
    if not requested:
        return False
    removal_terms = ("desktop idle", "long pauses", "loading", "failed clicks", "repeated attempts", "wrong window", "alt-tabbing")
    if not any(term in requested for term in removal_terms):
        return False
    duration = max(end - start, 0.001)
    for item in analysis.get("mistakeRemoval", {}).get("recommendedRemovals", []):
        overlap = max(0.0, min(end, float(item.get("end", start))) - max(start, float(item.get("start", end))))
        if overlap / duration > 0.45:
            return True
    return False


def _nudge_from_idle(start: float, end: float, analysis: dict[str, Any], raw_duration: float) -> tuple[float, float]:
    duration = end - start
    for idle in analysis.get("idleMoments", []):
        idle_start = float(idle["start"])
        idle_end = float(idle["end"])
        if min(end, idle_end) - max(start, idle_start) <= 0:
            continue
        if idle_end + duration <= raw_duration:
            return idle_end, idle_end + duration
        if idle_start - duration >= 0:
            return idle_start - duration, idle_start
    return start, end


def _project_from_segments(
    recording_path: Path,
    segments: list[dict[str, Any]],
    *,
    analysis: dict[str, Any],
    profile: dict[str, Any],
    product_name: str,
    instructions: str,
    spec: dict[str, Any],
    music_path: Path | None,
    logo_path: Path | None,
    music_analysis: dict[str, Any] | None,
    width: int,
    height: int,
) -> dict[str, Any]:
    assets: dict[str, str] = {"recording": str(recording_path)}
    if music_path:
        assets["music"] = str(music_path)
    elif analysis.get("source", {}).get("audioPresence"):
        assets["source_audio"] = str(recording_path)
    if logo_path:
        assets["logo"] = str(logo_path)

    timeline = []
    cursor = 0.0
    intro = _intro_scene(product_name, profile, logo_path is not None, width, height)
    intro["start"] = cursor
    timeline.append(intro)
    cursor += float(intro["duration"])

    for index, segment in enumerate(segments):
        scene = _feature_scene(segment, analysis=analysis, profile=profile, width=width, height=height, index=index)
        scene["start"] = round(cursor, 3)
        timeline.append(scene)
        cursor += float(scene["duration"])

    outro = _outro_scene(product_name, profile, logo_path is not None, width, height)
    outro["start"] = round(cursor, 3)
    timeline.append(outro)
    cursor += float(outro["duration"])

    audio = []
    if music_path:
        audio.append(
            {
                "asset": "music",
                "start": 0,
                "volume": float(profile.get("audioVolume", 0.32) or 0.32),
                "fadeIn": 0.4,
                "fadeOut": 1.2,
                "loop": True,
                "normalize": True,
                "limiter": True,
                "ducking": True,
            }
        )
    elif "source_audio" in assets:
        audio.append({"asset": "source_audio", "start": intro["duration"], "volume": 0.7, "trimStart": 0, "duration": max(cursor - intro["duration"], 0.1), "limiter": True})

    captions = _top_level_captions(timeline)
    return {
        "metadata": {
            "mode": "cinematic_auto_showcase",
            "productName": product_name,
            "instructions": instructions,
            "showcaseStyle": profile,
            "showcaseSpec": spec,
            "desktopAnalysisSummary": analysis.get("summary", {}),
            "uiImportanceSummary": _importance_summary(analysis),
            "automaticShowcaseTimeline": _timeline_summary(timeline),
            "deadTimeRemoval": analysis.get("deadTimeRemoval", {}),
            "mistakeRemoval": analysis.get("mistakeRemoval", {}),
            "audioReactive": _audio_reactive_metadata(music_analysis),
            "visualEnhancementPass": spec.get("visualEnhancement", {}),
            "sourceRecording": str(recording_path),
            "createdAt": _now(),
        },
        "exportPreset": "youtube_1080p" if width >= height else "shorts",
        "project": {
            "width": width,
            "height": height,
            "fps": 30,
            "duration": round(cursor, 3),
            "background": profile.get("background", "#05070d"),
            "crf": 18,
        },
        "assets": assets,
        "timeline": timeline,
        "audio": audio,
        "captions": captions,
    }


def _intro_scene(product_name: str, profile: dict[str, Any], has_logo: bool, width: int, height: int) -> dict[str, Any]:
    accent = profile["accent"]
    layers: list[dict[str, Any]] = [
        {"type": "animated_background", "color": accent, "opacity": min(float(profile.get("lightingIntensity", 0.3)) * 0.35, 0.22), "speed": 70},
        {"type": "shape", "x": 0, "y": 0, "width": width, "height": height, "color": "#000000", "opacity": 0.2},
    ]
    if has_logo:
        layers.append({"type": "image", "asset": "logo", "x": "center", "y": max(96, int(height * 0.18)), "scale": 0.24, "animation": {"in": "zoomIn", "out": "fade", "duration": 0.55}})
    layers.extend(
        [
            _text_layer(product_name, "center", int(height * 0.48), int(height * 0.074), profile, animation={"in": "typewriter", "out": "fade", "duration": 0.55}),
            _text_layer("Cinematic product showcase", "center", int(height * 0.6), int(height * 0.034), profile, color=profile.get("mutedText"), animation={"in": "slideUp", "out": "fade", "duration": 0.45}),
        ]
    )
    return {
        "id": "showcase_intro",
        "start": 0,
        "duration": 2.2,
        "layers": layers,
        "effectGraphPreset": profile.get("effectGraphPreset"),
        "postProcessing": _post_processing(profile),
        "transitionOut": dict(profile["transition"]),
    }


def _feature_scene(segment: dict[str, Any], *, analysis: dict[str, Any], profile: dict[str, Any], width: int, height: int, index: int) -> dict[str, Any]:
    source = analysis.get("source", {})
    source_w = int(source.get("width") or width)
    source_h = int(source.get("height") or height)
    focus = segment.get("focus", {})
    crop = _focus_crop(focus, source_w, source_h, width / max(height, 1), float(profile.get("zoomAggressiveness", 0.3) or 0.3))
    layers: list[dict[str, Any]] = [
        {
            "type": "video",
            "asset": "recording",
            "x": 0,
            "y": 0,
            "width": width,
            "height": height,
            "trimStart": segment["start"],
            "trimEnd": segment["end"],
            "crop": crop,
            "contrast": 1.04 + float(profile.get("cinematicIntensity", 0.5) or 0.5) * 0.16,
            "brightness": -0.015 if str(profile.get("key", "")).find("minimal") < 0 else 0.01,
            "camera": {
                "mode": profile.get("cameraMovement", "smooth_pan"),
                "intensity": float(profile.get("cinematicIntensity", 0.45) or 0.45),
                "zoom": 1.02 + float(profile.get("zoomAggressiveness", 0.25) or 0.25) * 0.18,
                "duration": segment["duration"],
                "panX": _pan_offset(float(focus.get("x", 0.5)), width, 0.04),
                "panY": _pan_offset(float(focus.get("y", 0.5)), height, 0.035),
            },
        },
        {"type": "shape", "x": 0, "y": 0, "width": width, "height": height, "color": "#000000", "opacity": min(float(profile.get("lightingIntensity", 0.25)) * 0.12, 0.08)},
        _focus_box_layer(focus, profile, width, height, segment["duration"]),
        _feature_title_card_layer(segment, profile, width, height),
        {
            "type": "lower_third",
            "title": segment["title"],
            "subtitle": _clean_reason(str(focus.get("reason", "focused interaction"))),
            "x": int(width * 0.055),
            "y": int(height * 0.74),
            "width": int(width * 0.5),
            "height": int(height * 0.12),
            "fontSize": int(height * 0.046),
            "subtitleSize": int(height * 0.027),
            "color": profile.get("textColor"),
            "subtitleColor": profile.get("mutedText"),
            "boxColor": profile.get("boxColor"),
            "start": 0.2,
            "duration": max(segment["duration"] - 0.4, 0.5),
            "animation": {"in": "slideRight", "out": "fade", "duration": 0.45},
        },
        {
            "type": "caption",
            "x": "center",
            "y": int(height * 0.88),
            "fontSize": int(height * 0.042),
            "color": "#ffffff" if str(profile.get("captionStyle")) != "clean" else profile.get("textColor"),
            "strokeColor": "#000000",
            "strokeWidth": 3 if str(profile.get("captionStyle")) == "bold" else 2,
            "box": True,
            "boxColor": "#00000099" if str(profile.get("captionStyle")) != "clean" else profile.get("boxColor"),
            "boxPadding": 12,
            "items": [{"text": segment["caption"], "start": 0.35, "duration": max(segment["duration"] - 0.7, 0.6)}],
        },
    ]
    scene: dict[str, Any] = {
        "id": segment["id"],
        "start": 0,
        "duration": segment["duration"],
        "layers": layers,
        "postProcessing": _post_processing(profile),
        "metadata": {
            "role": segment.get("role"),
            "titleCard": {"title": segment.get("title"), "benefit": segment.get("benefit")},
            "sourceRange": {"start": segment["start"], "end": segment["end"]},
            "focusReason": focus.get("reason"),
            "focusScore": focus.get("score"),
        },
        "effectGraphPreset": profile.get("effectGraphPreset"),
    }
    if index < 999:
        scene["transitionOut"] = _transition_for_segment(profile, focus)
    return scene


def _outro_scene(product_name: str, profile: dict[str, Any], has_logo: bool, width: int, height: int) -> dict[str, Any]:
    layers: list[dict[str, Any]] = [
        {"type": "animated_background", "color": profile["accent"], "opacity": min(float(profile.get("lightingIntensity", 0.25)) * 0.28, 0.18), "speed": 44},
    ]
    if has_logo:
        layers.append({"type": "image", "asset": "logo", "x": "center", "y": int(height * 0.22), "scale": 0.22, "animation": {"in": "fade", "out": "fade", "duration": 0.5}})
    layers.extend(
        [
            _text_layer("Built for speed. Polished for launch.", "center", int(height * 0.46), int(height * 0.052), profile, animation={"in": "slideUp", "out": "fade", "duration": 0.5}),
            _text_layer(f"Try {product_name}", "center", int(height * 0.58), int(height * 0.04), profile, color=profile.get("mutedText"), animation={"in": "fade", "out": "fade", "duration": 0.5}),
        ]
    )
    return {
        "id": "showcase_outro",
        "start": 0,
        "duration": 2.4,
        "layers": layers,
        "effectGraphPreset": profile.get("effectGraphPreset"),
        "postProcessing": _post_processing(profile),
    }


def _focus_crop(focus: dict[str, Any], source_w: int, source_h: int, target_aspect: float, zoom_aggression: float) -> dict[str, int]:
    x = float(focus.get("x", 0.5))
    y = float(focus.get("y", 0.5))
    zoom = max(1.0, min(1.75, 1.08 + zoom_aggression))
    crop_w = source_w / zoom
    crop_h = crop_w / target_aspect
    if crop_h > source_h:
        crop_h = source_h / zoom
        crop_w = crop_h * target_aspect
    crop_w = min(crop_w, source_w)
    crop_h = min(crop_h, source_h)
    left = x * source_w - crop_w / 2
    top = y * source_h - crop_h / 2
    left = max(0, min(left, source_w - crop_w))
    top = max(0, min(top, source_h - crop_h))
    return {"x": int(round(left)), "y": int(round(top)), "width": int(round(crop_w)), "height": int(round(crop_h))}


def _focus_box_layer(focus: dict[str, Any], profile: dict[str, Any], width: int, height: int, duration: float) -> dict[str, Any]:
    box_w = int(width * 0.22)
    box_h = int(height * 0.15)
    x = int(float(focus.get("x", 0.5)) * width - box_w / 2)
    y = int(float(focus.get("y", 0.5)) * height - box_h / 2)
    x = max(0, min(x, width - box_w))
    y = max(0, min(y, height - box_h))
    return {
        "type": "shape",
        "x": x,
        "y": y,
        "width": box_w,
        "height": box_h,
        "color": profile.get("accent", "#38bdf8"),
        "opacity": min(0.18, 0.06 + float(profile.get("lightingIntensity", 0.25)) * 0.18),
        "start": 0.15,
        "duration": max(duration - 0.3, 0.3),
    }


def _feature_title_card_layer(segment: dict[str, Any], profile: dict[str, Any], width: int, height: int) -> dict[str, Any]:
    return {
        "type": "text",
        "text": str(segment.get("benefit") or segment.get("title") or "Feature highlight"),
        "x": int(width * 0.055),
        "y": int(height * 0.08),
        "fontSize": int(height * 0.036),
        "color": profile.get("textColor", "#ffffff"),
        "strokeColor": "#000000",
        "strokeWidth": 2,
        "box": True,
        "boxColor": profile.get("boxColor", "#000000aa"),
        "boxPadding": 14,
        "start": 0.2,
        "duration": max(0.4, min(float(segment.get("duration", 2.0)) - 0.3, 2.4)),
        "animation": {"in": "slideRight", "out": "fade", "duration": 0.42},
    }


def _post_processing(profile: dict[str, Any]) -> dict[str, Any]:
    lighting = float(profile.get("lightingIntensity", 0.25) or 0.25)
    return {
        "colorGrade": {"contrast": 1.04 + lighting * 0.18, "brightness": -0.01 * lighting, "saturation": 1.0 + lighting * 0.12},
        "vignette": min(0.56, 0.18 + lighting * 0.52),
        "glow": min(0.5, 0.08 + lighting * 0.48),
    }


def _transition_for_segment(profile: dict[str, Any], focus: dict[str, Any]) -> dict[str, Any]:
    transition = dict(profile.get("transition", {"type": "crossfade", "duration": 0.45}))
    if "click" in str(focus.get("reason", "")).lower() and float(profile.get("transitionIntensity", 0.4) or 0.4) > 0.5:
        transition = {"type": "zoom", "duration": min(0.32, float(transition.get("duration", 0.3) or 0.3))}
    return transition


def _text_layer(text: str, x: Any, y: Any, font_size: int, profile: dict[str, Any], *, color: str | None = None, animation: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "type": "text",
        "text": text,
        "x": x,
        "y": y,
        "fontSize": max(font_size, 18),
        "color": color or profile.get("textColor", "#ffffff"),
        "strokeColor": "#000000",
        "strokeWidth": 2,
        "shadowColor": "#000000",
        "shadowX": 3,
        "shadowY": 3,
        "animation": animation or {"in": "fade", "out": "fade", "duration": 0.5},
    }


def _top_level_captions(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    captions = []
    for scene in timeline:
        scene_start = float(scene.get("start", 0))
        for layer in scene.get("layers", []):
            if layer.get("type") != "caption":
                continue
            for item in layer.get("items", []):
                captions.append({"text": item["text"], "start": round(scene_start + float(item["start"]), 3), "duration": item.get("duration", 1.5)})
    return captions


def _audio_reactive_metadata(music_analysis: dict[str, Any] | None) -> dict[str, Any]:
    if not music_analysis:
        return {"enabled": False}
    return {
        "enabled": True,
        "bpm": music_analysis.get("bpm"),
        "beatCount": len(music_analysis.get("beats", [])),
        "bassDropCount": len(music_analysis.get("bassDrops", [])),
        "syncStrategy": "cuts and zoom intensity are biased toward beat, peak, and bass-drop candidates",
    }


def _segment_title(index: int, segment: dict[str, Any], analysis: dict[str, Any], spec: dict[str, Any]) -> str:
    target = segment.get("focus", {}).get("target")
    if target:
        return _title_case(str(target))
    title_cards = spec.get("titleCards", [])
    if index - 1 < len(title_cards):
        return str(title_cards[index - 1].get("title") or "Feature Reveal")
    reason = str(segment.get("focus", {}).get("reason", "")).lower()
    if "click" in reason or "cursor" in reason:
        return "Interaction Highlight"
    if "scene" in reason or "window" in reason:
        return "Feature Reveal"
    if "text" in reason:
        return "Key Detail"
    if index == 1:
        return "Focused Workflow"
    return "Showcase Moment"


def _segment_caption(index: int, segment: dict[str, Any], analysis: dict[str, Any], spec: dict[str, Any]) -> str:
    title_cards = spec.get("titleCards", [])
    if index - 1 < len(title_cards):
        return str(title_cards[index - 1].get("benefit") or "Keep the viewer focused on the product value.")
    reason = str(segment.get("focus", {}).get("reason", "motion focus"))
    if "click" in reason or "cursor" in reason:
        return "Every action is framed so the viewer knows exactly where to look."
    if "scene" in reason or "window" in reason:
        return "The edit lands on the moments where the product changes state."
    if "text" in reason:
        return "Important interface details stay readable while the camera moves."
    return "The strongest motion moments become clean cinematic beats."


def _segment_benefit(index: int, segment: dict[str, Any], spec: dict[str, Any]) -> str:
    title_cards = spec.get("titleCards", [])
    if index - 1 < len(title_cards):
        return str(title_cards[index - 1].get("benefit") or "")
    role = str(segment.get("role", "feature_reveal"))
    benefits = {
        "feature_reveal": "Reveal the product value instantly.",
        "interaction_highlight": "Show the exact action that matters.",
        "result_moment": "Make the payoff clear.",
        "transition": "Keep momentum without losing readability.",
    }
    return benefits.get(role, "Keep the viewer focused.")


def _nearest_focus(analysis: dict[str, Any], time_s: float) -> dict[str, Any]:
    events = analysis.get("importantUiFocusAreas", [])
    if not events:
        return {"time": time_s, "x": 0.5, "y": 0.5, "score": 0.2, "reason": "center fallback"}
    return dict(min(events, key=lambda item: abs(float(item.get("time", 0)) - time_s)))


def _overlap_ratio(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    overlap = max(0.0, min(a_end, b_end) - max(a_start, b_start))
    return overlap / max(a_end - a_start, 0.001)


def _pan_offset(value: float, size: int, scale: float) -> float:
    return round((0.5 - value) * size * scale, 3)


def _clean_reason(reason: str) -> str:
    return reason.replace("_", " ").strip().capitalize() or "Focused interaction"


def _importance_summary(analysis: dict[str, Any]) -> dict[str, int]:
    importance = analysis.get("uiImportanceDetection", {})
    return {key: len(value) for key, value in importance.items() if isinstance(value, list)}


def _timeline_summary(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for scene in timeline:
        rows.append(
            {
                "id": scene.get("id"),
                "role": scene.get("metadata", {}).get("role", "intro" if scene.get("id") == "showcase_intro" else "outro" if scene.get("id") == "showcase_outro" else "scene"),
                "start": scene.get("start"),
                "duration": scene.get("duration"),
                "transitionOut": scene.get("transitionOut", {}).get("type"),
            }
        )
    return rows


def _title_case(value: str) -> str:
    return " ".join(word.capitalize() for word in value.replace("_", " ").split())


def _product_name_from_instructions(instructions: str) -> str | None:
    match = re.search(r"(?:for|about)\s+([A-Z][A-Za-z0-9 _-]{2,48})", instructions)
    if match:
        return match.group(1).strip(" .")
    return None


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
