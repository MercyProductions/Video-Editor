from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import statistics
import subprocess
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from assets.intelligence import analyze_asset
from audio.intelligence import analyze_audio_intelligence
from utils.media import run_ffmpeg


def apply_advanced_cinematic_engine(
    project: dict[str, Any],
    *,
    analysis: dict[str, Any] | None = None,
    spec: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
    recording_path: Path | None = None,
    music_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Apply renderable advanced systems to a generated project.

    This is deliberately practical: it turns analysis into deterministic scene
    metadata, render graph nodes, camera keyframes, safer typography, audio
    mix settings, and explainable edit decisions that the existing FFmpeg
    backend can render today.
    """

    project = deepcopy(project)
    analysis = analysis or {}
    spec = spec or {}
    profile = profile or {}
    root = _project_root(project, recording_path)
    recording_path = recording_path.resolve() if recording_path else _recording_from_project(project, root)
    music_path = music_path.resolve() if music_path else _music_from_project(project, root)

    report: dict[str, Any] = {
        "format": "automatic-video-editor-advanced-cinematic-report",
        "createdAt": _now(),
        "localFirst": True,
        "recording": str(recording_path) if recording_path else None,
        "music": str(music_path) if music_path else None,
        "systems": {},
        "decisions": [],
        "warnings": [],
    }

    source_metadata = _capture_metadata(recording_path, analysis)
    report["systems"]["hardwareCaptureAwareness"] = source_metadata

    color_plan = _color_management_plan(project, source_metadata, profile)
    _apply_color_management(project, color_plan)
    report["systems"]["colorManagement"] = color_plan

    motion_plan = _advanced_motion_plan(analysis)
    semantic_plan = _semantic_scene_understanding(project, analysis, spec)
    direction_plan = _creative_direction_plan(project, analysis, spec, profile, motion_plan, semantic_plan)
    memory_plan = _temporal_editing_memory(project, direction_plan)
    overrides = _human_override_index(project)

    _apply_scene_intelligence(project, motion_plan, semantic_plan, direction_plan, memory_plan, overrides, report)
    report["systems"]["advancedMotionAnalysis"] = motion_plan
    report["systems"]["semanticSceneUnderstanding"] = semantic_plan
    report["systems"]["creativeDirection"] = direction_plan
    report["systems"]["temporalEditingMemory"] = memory_plan
    report["systems"]["humanOverrideSystem"] = overrides

    typography_plan = _typography_plan(project)
    _apply_typography(project, typography_plan, overrides)
    report["systems"]["professionalTypography"] = typography_plan

    audio_plan = _audio_intelligence_plan(music_path)
    _apply_audio_intelligence(project, audio_plan)
    report["systems"]["advancedAudioIntelligence"] = audio_plan

    render_graph = _render_graph_plan(project)
    project.setdefault("metadata", {})["renderGraph"] = render_graph
    report["systems"]["renderGraphArchitecture"] = render_graph

    gpu_plan = _gpu_vram_plan(project)
    project.setdefault("metadata", {})["hardwarePlan"] = gpu_plan
    report["systems"]["gpuVramManagement"] = gpu_plan

    asset_plan = _asset_scoring(project, root)
    project.setdefault("metadata", {})["assetScoring"] = asset_plan
    report["systems"]["intelligentAssetScoring"] = asset_plan

    deterministic = _deterministic_rendering(project)
    project.setdefault("metadata", {})["deterministicRendering"] = deterministic
    report["systems"]["deterministicRendering"] = deterministic

    license_plan = _asset_license_safety(project)
    project.setdefault("metadata", {})["licenseSafety"] = license_plan
    report["systems"]["assetLicenseSafety"] = license_plan
    report["warnings"].extend(license_plan.get("warnings", []))

    confidence = _confidence_explainability(project, report)
    project.setdefault("metadata", {})["aiExplainability"] = confidence
    report["systems"]["aiConfidenceExplainability"] = confidence

    project.setdefault("metadata", {})["advancedSystems"] = {
        "enabled": True,
        "createdAt": report["createdAt"],
        "colorWorkflow": color_plan["target"]["workflow"],
        "sceneUnderstandingCount": len(semantic_plan.get("workflowMoments", [])),
        "decisionCount": len(report["decisions"]),
        "warningCount": len(report["warnings"]),
    }

    report["projectFingerprint"] = _stable_digest(project)
    report["project"] = project
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return {"project": project, "report": report}


def _project_root(project: dict[str, Any], recording_path: Path | None) -> Path:
    if recording_path:
        return recording_path.resolve().parent
    metadata_root = project.get("metadata", {}).get("projectRoot")
    if metadata_root:
        return Path(str(metadata_root)).resolve()
    return Path.cwd()


def _recording_from_project(project: dict[str, Any], root: Path) -> Path | None:
    value = project.get("assets", {}).get("recording")
    if not value:
        return None
    path = Path(str(value))
    return path if path.is_absolute() else root / path


def _music_from_project(project: dict[str, Any], root: Path) -> Path | None:
    assets = project.get("assets", {})
    for track in project.get("audio", []):
        asset = track.get("asset")
        if asset and asset in assets:
            path = Path(str(assets[asset]))
            return path if path.is_absolute() else root / path
    return None


def _capture_metadata(path: Path | None, analysis: dict[str, Any]) -> dict[str, Any]:
    source = analysis.get("source", {}) if analysis else {}
    metadata: dict[str, Any] = {
        "available": path is not None and path.exists() if path else False,
        "width": int(source.get("width") or 0),
        "height": int(source.get("height") or 0),
        "fps": source.get("fps"),
        "codec": source.get("codec"),
        "audioPresence": bool(source.get("audioPresence")),
        "hdr": False,
        "colorSpace": "unknown",
        "transfer": "unknown",
        "pixelFormat": None,
        "variableFrameRateLikely": False,
        "ultrawide": False,
        "dpiScalingLikely": False,
        "obsArtifactsLikely": False,
        "compressionArtifactsRisk": "unknown",
        "multipleMonitorLikely": False,
        "warnings": [],
    }
    if path and path.exists():
        result = run_ffmpeg(["-hide_banner", "-i", str(path)])
        text = (result.stderr or "") + (result.stdout or "")
        width, height = _parse_resolution(text, metadata["width"], metadata["height"])
        metadata["width"] = width
        metadata["height"] = height
        metadata["codec"] = metadata["codec"] or _regex(text, r"Video:\s*([^,\s]+)")
        metadata["fps"] = metadata["fps"] or _float_regex(text, r"(\d+(?:\.\d+)?)\s*fps")
        metadata["avgFrameRate"] = _float_regex(text, r"(\d+(?:\.\d+)?)\s*tbr")
        metadata["pixelFormat"] = _regex(text, r"Video:[^\n,]+,\s*([^,\s]+)")
        lowered = text.lower()
        metadata["hdr"] = any(token in lowered for token in ("bt2020", "smpte2084", "arib-std-b67", "hlg", "pq"))
        metadata["colorSpace"] = "bt2020" if "bt2020" in lowered else "bt709" if "bt709" in lowered else "unknown"
        metadata["transfer"] = "pq" if "smpte2084" in lowered else "hlg" if "arib-std-b67" in lowered else "bt709" if "bt709" in lowered else "unknown"
        fps = float(metadata.get("fps") or 0)
        avg = float(metadata.get("avgFrameRate") or fps or 0)
        metadata["variableFrameRateLikely"] = bool(fps and avg and abs(fps - avg) > 0.2)
        metadata["compressionArtifactsRisk"] = _compression_risk(text)

    width = int(metadata.get("width") or 0)
    height = int(metadata.get("height") or 0)
    aspect = width / max(height, 1)
    metadata["ultrawide"] = aspect >= 2.05
    metadata["multipleMonitorLikely"] = aspect >= 2.8
    metadata["dpiScalingLikely"] = bool(width % 100 != 0 and width % 16 != 0) or bool(height % 100 != 0 and height % 16 != 0)
    metadata["obsArtifactsLikely"] = str(metadata.get("codec") or "").lower() in {"h264", "hevc", "av1"} and bool(metadata.get("variableFrameRateLikely"))
    if metadata["hdr"]:
        metadata["warnings"].append("HDR capture detected; tone mapping to Rec.709 SDR is recommended for social exports.")
    if metadata["variableFrameRateLikely"]:
        metadata["warnings"].append("Variable frame rate capture likely; normalize FPS during render to prevent sync drift.")
    if metadata["ultrawide"]:
        metadata["warnings"].append("Ultrawide capture detected; focus crops should protect menus and key UI.")
    return metadata


def _color_management_plan(project: dict[str, Any], capture: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    target = {
        "workflow": "Rec.709 SDR",
        "colorSpace": "bt709",
        "primaries": "bt709",
        "transfer": "bt709",
        "range": "tv",
        "gamma": 1.0,
        "exportTags": {"colorspace": "bt709", "color_primaries": "bt709", "color_trc": "bt709"},
    }
    lighting = float(profile.get("lightingIntensity", 0.3) or 0.3)
    nodes: list[dict[str, Any]] = [
        {"type": "setparams", **target["exportTags"], "range": "tv"},
        {"type": "color_grade", "brightness": round(-0.006 * lighting, 4), "contrast": round(1.025 + lighting * 0.045, 4), "saturation": round(1.0 + lighting * 0.035, 4), "gamma": 1.0},
    ]
    if capture.get("hdr"):
        nodes.insert(0, {"type": "tone_map", "mode": "hable", "desat": 0.2})
    if profile.get("accent"):
        nodes.append({"type": "tint", "color": profile["accent"], "opacity": round(min(0.035, lighting * 0.035), 4)})
    return {
        "source": {
            "hdr": bool(capture.get("hdr")),
            "colorSpace": capture.get("colorSpace", "unknown"),
            "transfer": capture.get("transfer", "unknown"),
            "pixelFormat": capture.get("pixelFormat"),
        },
        "target": target,
        "nodes": nodes,
        "lutStack": [],
        "monitorProfileAwareness": {
            "mode": "metadata-aware",
            "note": "Local monitor ICC transforms are not baked into exports; exports are normalized to Rec.709 tags for consistent playback.",
        },
        "exportValidation": {
            "checks": ["bt709 tags", "yuv420p compatibility", "SDR-safe brightness", "tone-mapped HDR sources"],
        },
    }


def _apply_color_management(project: dict[str, Any], plan: dict[str, Any]) -> None:
    for scene in project.get("timeline", []):
        graph = scene.setdefault("effectGraph", {})
        nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
        if not isinstance(nodes, list):
            nodes = []
        existing_keys = {_node_key(node) for node in nodes if isinstance(node, dict)}
        for node in plan.get("nodes", []):
            if _node_key(node) not in existing_keys:
                nodes.append(dict(node))
        scene["effectGraph"] = {"nodes": nodes}
        post = scene.setdefault("postProcessing", {})
        post["colorManagement"] = {
            "workflow": plan["target"]["workflow"],
            "exportColorSpace": plan["target"]["colorSpace"],
            "toneMapping": "enabled" if plan["source"]["hdr"] else "sdr-pass-through",
        }


def _advanced_motion_plan(analysis: dict[str, Any]) -> dict[str, Any]:
    samples = analysis.get("importantUiFocusAreas", [])
    vectors = []
    for left, right in zip(samples, samples[1:]):
        dt = max(float(right.get("time", 0)) - float(left.get("time", 0)), 0.001)
        dx = float(right.get("x", 0.5)) - float(left.get("x", 0.5))
        dy = float(right.get("y", 0.5)) - float(left.get("y", 0.5))
        vectors.append(
            {
                "start": left.get("time"),
                "end": right.get("time"),
                "dx": round(dx, 4),
                "dy": round(dy, 4),
                "speed": round(math.sqrt(dx * dx + dy * dy) / dt, 4),
                "direction": _direction(dx, dy),
            }
        )
    speeds = [float(item["speed"]) for item in vectors]
    average_speed = statistics.mean(speeds) if speeds else 0.0
    path = _smooth_camera_path(samples)
    return {
        "opticalFlowApproximation": {
            "method": "localized frame-difference flow from sampled desktop frames",
            "vectorCount": len(vectors),
            "averageSpeed": round(average_speed, 4),
            "motionVectors": vectors[:48],
        },
        "objectTracking": _object_tracks(samples),
        "cursorTrackingStabilization": {
            "enabled": True,
            "smoothing": "cubic smoothstep",
            "jitterThreshold": 0.012,
        },
        "predictivePanZoom": path,
        "cinematicTrackingBehavior": {
            "style": "ease-in-out focus preserving",
            "readabilityBias": 0.72,
            "maxZoom": 1.34,
        },
    }


def _smooth_camera_path(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    path = []
    previous_x = 0.5
    previous_y = 0.5
    for event in events[:24]:
        x = float(event.get("x", previous_x))
        y = float(event.get("y", previous_y))
        confidence = float(event.get("score", 0.45) or 0.45)
        smooth_x = previous_x * 0.45 + x * 0.55
        smooth_y = previous_y * 0.45 + y * 0.55
        path.append(
            {
                "time": event.get("time"),
                "x": round(smooth_x, 4),
                "y": round(smooth_y, 4),
                "zoom": round(1.06 + min(confidence, 1.0) * 0.18, 4),
                "easing": "smoothstep",
                "reason": event.get("reason", "focus tracking"),
            }
        )
        previous_x = smooth_x
        previous_y = smooth_y
    return path


def _semantic_scene_understanding(project: dict[str, Any], analysis: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    focus_words = " ".join(str(item) for item in spec.get("mustShow", [])).lower()
    instructions = str(spec.get("rawInstructions", "") or project.get("metadata", {}).get("instructions", "")).lower()
    timeline = project.get("timeline", [])
    moments = []
    for scene in timeline:
        if scene.get("id") in {"showcase_intro", "showcase_outro"}:
            kind = "intro" if scene.get("id") == "showcase_intro" else "outro"
        else:
            text = _scene_text(scene).lower() + " " + focus_words + " " + instructions
            kind = _semantic_kind(text, scene)
        moments.append(
            {
                "sceneId": scene.get("id"),
                "start": scene.get("start"),
                "duration": scene.get("duration"),
                "workflowState": kind,
                "importance": _semantic_importance(kind),
                "reason": _semantic_reason(kind),
            }
        )
    inferred = _infer_demonstration(moments, instructions, analysis)
    return {
        "detectedWorkflow": inferred,
        "workflowMoments": moments,
        "highlightCandidates": [item for item in moments if item["importance"] >= 0.72],
        "intent": "product showcase" if "showcase" in instructions or project.get("metadata", {}).get("mode") == "cinematic_auto_showcase" else "general edit",
    }


def _temporal_editing_memory(project: dict[str, Any], direction: dict[str, Any]) -> dict[str, Any]:
    timeline = project.get("timeline", [])
    transitions = [scene.get("transitionOut", {}).get("type", "cut") for scene in timeline if scene.get("transitionOut")]
    zooms = []
    lighting = []
    roles = []
    for scene in timeline:
        roles.append(scene.get("metadata", {}).get("role"))
        post = scene.get("postProcessing", {})
        if isinstance(post, dict):
            lighting.append(float(post.get("glow", 0) or 0) + float(post.get("vignette", 0) or 0))
        for layer in scene.get("layers", []):
            camera = layer.get("camera")
            if isinstance(camera, dict):
                zooms.append(float(camera.get("zoom", 1) or 1))
    repetitive = _repetition_warnings(transitions, zooms)
    return {
        "recentTransitions": transitions[-8:],
        "pacingRhythm": direction.get("pacingCurve", []),
        "zoomFrequency": len([value for value in zooms if value > 1.08]),
        "averageZoom": round(statistics.mean(zooms), 4) if zooms else 1.0,
        "lightingIntensityAverage": round(statistics.mean(lighting), 4) if lighting else 0,
        "visualRepetitionWarnings": repetitive,
        "roleSequence": roles,
        "preventionRules": ["limit identical transition runs", "vary zoom strength", "preserve readability on text-heavy moments"],
    }


def _creative_direction_plan(
    project: dict[str, Any],
    analysis: dict[str, Any],
    spec: dict[str, Any],
    profile: dict[str, Any],
    motion: dict[str, Any],
    semantic: dict[str, Any],
) -> dict[str, Any]:
    scenes = project.get("timeline", [])
    count = max(len(scenes), 1)
    pace = str(profile.get("pace") or spec.get("pace") or "medium")
    tension = []
    for index, scene in enumerate(scenes):
        normalized = index / max(count - 1, 1)
        base = 0.25 + math.sin(normalized * math.pi) * 0.55
        if scene.get("id") == "showcase_outro":
            base = 0.36
        if semantic.get("workflowMoments", [{}])[index].get("workflowState") in {"success_state", "result_payoff"} if index < len(semantic.get("workflowMoments", [])) else False:
            base += 0.12
        tension.append({"sceneId": scene.get("id"), "energy": round(min(base, 1.0), 3), "phase": _direction_phase(normalized)})
    return {
        "pace": pace,
        "pacingCurve": tension,
        "energyMapping": {
            "sourcePeakMotion": analysis.get("summary", {}).get("peakMotion", 0),
            "focusEventCount": analysis.get("summary", {}).get("focusEventCount", 0),
            "motionVectorCount": motion.get("opticalFlowApproximation", {}).get("vectorCount", 0),
        },
        "emotionalStructure": ["hook", "anticipation", "feature reveal", "payoff", "resolution"],
        "revealTiming": [item for item in tension if item["phase"] in {"anticipation", "reveal", "payoff"}],
        "visualCrescendo": "middle-weighted with a restrained outro",
    }


def _apply_scene_intelligence(
    project: dict[str, Any],
    motion: dict[str, Any],
    semantic: dict[str, Any],
    direction: dict[str, Any],
    memory: dict[str, Any],
    overrides: dict[str, Any],
    report: dict[str, Any],
) -> None:
    path = motion.get("predictivePanZoom", [])
    moments = {item["sceneId"]: item for item in semantic.get("workflowMoments", [])}
    energy = {item["sceneId"]: item for item in direction.get("pacingCurve", [])}
    transition_cycle = ["crossfade", "slide", "zoom", "fadeToBlack"]
    last_transition = None
    repeat_count = 0
    for index, scene in enumerate(project.get("timeline", [])):
        scene_id = str(scene.get("id"))
        if scene_id in overrides["lockedScenes"] or scene_id in overrides["aiDisabledScenes"]:
            report["decisions"].append(_decision(scene_id, "human_override", "Scene is locked or AI-disabled; advanced engine left it unchanged.", 1.0))
            continue

        scene.setdefault("metadata", {})["semantic"] = moments.get(scene_id, {})
        scene["metadata"]["creativeDirection"] = energy.get(scene_id, {})
        for layer in scene.get("layers", []):
            if layer.get("type") != "video" or layer.get("locked") or layer.get("aiDisabled"):
                continue
            camera = layer.setdefault("camera", {})
            scene_path = _path_for_scene(path, float(scene.get("start", 0)), float(scene.get("duration", 0)))
            if scene_path:
                camera["keyframes"] = scene_path
                camera["mode"] = "keyframed"
                camera["interpolation"] = "smoothstep"
                camera["zoom"] = round(max(float(item.get("zoom", 1.05)) for item in scene_path), 4)
                report["decisions"].append(_decision(scene_id, "camera_path", "Applied stabilized predictive pan/zoom keyframes around important UI focus.", 0.82))
        transition = scene.get("transitionOut")
        if isinstance(transition, dict) and not transition.get("locked") and scene_id not in overrides["lockedTransitions"]:
            kind = str(transition.get("type", "crossfade"))
            if kind == last_transition:
                repeat_count += 1
            else:
                repeat_count = 0
            if repeat_count >= 2:
                transition["type"] = transition_cycle[index % len(transition_cycle)]
                transition["duration"] = min(float(transition.get("duration", 0.45) or 0.45), 0.45)
                report["decisions"].append(_decision(scene_id, "transition_variation", f"Changed repeated {kind} transition to {transition['type']} for continuity.", 0.74))
                repeat_count = 0
            last_transition = str(transition.get("type", "cut"))

        if memory.get("zoomFrequency", 0) > 4:
            _soften_scene_zoom(scene, report)


def _typography_plan(project: dict[str, Any]) -> dict[str, Any]:
    scenes = project.get("timeline", [])
    text_layers = []
    for scene in scenes:
        for layer in scene.get("layers", []):
            if layer.get("type") in {"text", "caption", "captions", "lower_third"}:
                text_layers.append((scene, layer))
    return {
        "textLayerCount": len(text_layers),
        "kerning": "FFmpeg drawtext/freetype kerning enabled by selected font where available",
        "fontFallback": _font_fallbacks(),
        "safeZone": {"x": 0.08, "y": 0.08},
        "subtitleReadability": {
            "minStrokeWidth": 2,
            "boxWhenLowerThird": True,
            "maxCharactersPerLine": 34,
            "minimumSecondsPerWord": 0.18,
        },
        "gpuTextRendering": {"status": "not used in FFmpeg backend", "fallback": "deterministic CPU drawtext"},
    }


def _apply_typography(project: dict[str, Any], plan: dict[str, Any], overrides: dict[str, Any]) -> None:
    width = int(project.get("project", {}).get("width", 1920))
    height = int(project.get("project", {}).get("height", 1080))
    safe_x = int(width * plan["safeZone"]["x"])
    safe_y = int(height * plan["safeZone"]["y"])
    for scene in project.get("timeline", []):
        scene_id = str(scene.get("id"))
        if scene_id in overrides["lockedScenes"]:
            continue
        for layer in scene.get("layers", []):
            if layer.get("type") not in {"text", "caption", "captions", "lower_third"} or layer.get("locked"):
                continue
            _clamp_text_layer(layer, width, height, safe_x, safe_y)
            if layer.get("type") in {"text", "caption", "captions"}:
                if layer.get("text"):
                    layer["text"] = _balance_text(str(layer["text"]), int(layer.get("maxCharsPerLine", 34) or 34))
                for item in layer.get("items", []) or []:
                    if item.get("text"):
                        item["text"] = _balance_text(str(item["text"]), int(layer.get("maxCharsPerLine", 34) or 34))
                    words = len(str(item.get("text", "")).split())
                    if words and item.get("duration"):
                        item["duration"] = max(float(item["duration"]), round(words * plan["subtitleReadability"]["minimumSecondsPerWord"], 3))
                layer.setdefault("strokeWidth", plan["subtitleReadability"]["minStrokeWidth"])
                layer.setdefault("strokeColor", "#000000")
                layer.setdefault("lineSpacing", 8)
                if layer.get("type") in {"caption", "captions"}:
                    layer.setdefault("box", True)
                    layer.setdefault("boxColor", "#000000a8")


def _audio_intelligence_plan(music_path: Path | None) -> dict[str, Any]:
    if not music_path or not music_path.exists():
        return {"available": False, "recommendedTrackSettings": {}, "mixPipeline": []}
    try:
        report = analyze_audio_intelligence(music_path)
    except Exception as exc:
        return {"available": False, "error": str(exc), "recommendedTrackSettings": {}, "mixPipeline": []}
    return {
        "available": True,
        "mixProfile": report.get("mixProfile", {}),
        "recommendedTrackSettings": report.get("recommendedTrackSettings", {}),
        "editRecommendations": report.get("editRecommendations", []),
        "mixPipeline": [
            "sample-rate normalize 48kHz",
            "high/low cleanup for speech",
            "compressor",
            "bass emphasis on drops",
            "limiter",
            "loudness normalization",
            "fade blend",
        ],
    }


def _apply_audio_intelligence(project: dict[str, Any], plan: dict[str, Any]) -> None:
    if not plan.get("available"):
        return
    settings = plan.get("recommendedTrackSettings", {})
    for track in project.get("audio", []):
        for key, value in settings.items():
            track.setdefault(key, value)
        track.setdefault("autoBalance", True)
        track.setdefault("loudnessNormalize", True)
        track.setdefault("transitionBlend", True)


def _render_graph_plan(project: dict[str, Any]) -> dict[str, Any]:
    nodes = []
    edges = []
    for scene in project.get("timeline", []):
        scene_id = scene.get("id")
        scene_node = f"scene:{scene_id}"
        nodes.append({"id": scene_node, "type": "scene", "cacheKey": _stable_digest(scene)})
        for layer_index, layer in enumerate(scene.get("layers", [])):
            layer_node = f"{scene_node}:layer:{layer_index}:{layer.get('type')}"
            nodes.append({"id": layer_node, "type": "layer", "layerType": layer.get("type"), "cacheKey": _stable_digest(layer)})
            edges.append({"from": layer_node, "to": scene_node})
        graph = scene.get("effectGraph", {})
        effect_nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
        for effect_index, effect in enumerate(effect_nodes if isinstance(effect_nodes, list) else []):
            effect_node = f"{scene_node}:effect:{effect_index}:{effect.get('type', 'node')}"
            nodes.append({"id": effect_node, "type": "effect", "effectType": effect.get("type"), "cacheKey": _stable_digest(effect)})
            edges.append({"from": scene_node, "to": effect_node})
    return {
        "nodeCount": len(nodes),
        "edgeCount": len(edges),
        "nodes": nodes,
        "edges": edges,
        "evaluation": "scene layers -> scene composite -> post/effect graph -> transition graph -> mux",
        "intermediateCaching": "scene cache keys include render settings and asset references",
        "partialRerendering": "scene-level cache invalidation",
    }


def _gpu_vram_plan(project: dict[str, Any]) -> dict[str, Any]:
    width = int(project.get("project", {}).get("width", 1920))
    height = int(project.get("project", {}).get("height", 1080))
    layers = max(max(len(scene.get("layers", [])), 1) for scene in project.get("timeline", []) or [{}])
    frame_bytes = width * height * 4
    estimated = frame_bytes * min(layers + 2, 8)
    encoders = _available_encoders()
    return {
        "estimatedWorkingSetBytes": estimated,
        "estimatedWorkingSetMB": round(estimated / 1024 / 1024, 2),
        "recommendedPreviewScale": 0.5 if estimated > 512 * 1024 * 1024 else 1.0,
        "hardwareEncoders": encoders,
        "preferredBackend": "gpu" if encoders.get("nvidia") or encoders.get("intel") or encoders.get("amd") else "cpu",
        "fallback": "libx264 CPU render if GPU encoder fails",
        "adaptiveQuality": {"enabled": True, "previewScale": 0.5, "finalScale": 1.0},
    }


def _asset_scoring(project: dict[str, Any], root: Path) -> dict[str, Any]:
    rows = []
    seen_hashes: dict[str, str] = {}
    for key, value in project.get("assets", {}).items():
        path = Path(str(value))
        if not path.is_absolute():
            path = root / path
        report = analyze_asset(str(key), path)
        digest = _file_digest(path) if path.exists() else None
        duplicate_of = seen_hashes.get(digest) if digest else None
        if digest and not duplicate_of:
            seen_hashes[digest] = str(key)
        score = _asset_quality_score(report, duplicate_of)
        rows.append(
            {
                "key": key,
                "path": str(path),
                "type": report.get("type"),
                "score": score,
                "duplicateOf": duplicate_of,
                "highlightPotential": _highlight_potential(report),
                "issues": report.get("issues", []),
            }
        )
    return {
        "assets": sorted(rows, key=lambda item: item["score"], reverse=True),
        "bestAssets": sorted(rows, key=lambda item: item["score"], reverse=True)[:5],
        "duplicateCount": len([item for item in rows if item.get("duplicateOf")]),
    }


def _human_override_index(project: dict[str, Any]) -> dict[str, Any]:
    locked_scenes = []
    locked_transitions = []
    ai_disabled = []
    protected_regions = []
    forced_timing = []
    for scene in project.get("timeline", []):
        scene_id = str(scene.get("id"))
        metadata = scene.get("metadata", {})
        if scene.get("locked") or metadata.get("locked"):
            locked_scenes.append(scene_id)
        if scene.get("aiDisabled") or metadata.get("aiDisabled"):
            ai_disabled.append(scene_id)
        if isinstance(scene.get("transitionOut"), dict) and scene["transitionOut"].get("locked"):
            locked_transitions.append(scene_id)
        if metadata.get("protectedRegions"):
            protected_regions.append({"sceneId": scene_id, "regions": metadata["protectedRegions"]})
        if metadata.get("forcedTiming"):
            forced_timing.append({"sceneId": scene_id, "timing": metadata["forcedTiming"]})
    return {
        "lockedScenes": locked_scenes,
        "lockedTransitions": locked_transitions,
        "aiDisabledScenes": ai_disabled,
        "protectedRegions": protected_regions,
        "forcedTiming": forced_timing,
        "revertBySection": True,
        "editConfidenceScoring": True,
    }


def _deterministic_rendering(project: dict[str, Any]) -> dict[str, Any]:
    seed = _stable_digest({"assets": project.get("assets"), "timeline": project.get("timeline"), "project": project.get("project")})[:12]
    for scene_index, scene in enumerate(project.get("timeline", [])):
        scene.setdefault("metadata", {})["deterministicOrder"] = scene_index
        graph = scene.get("effectGraph", {})
        nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
        for node_index, node in enumerate(nodes if isinstance(nodes, list) else []):
            node.setdefault("id", f"{scene.get('id')}:effect:{node_index}:{node.get('type', 'node')}")
            node.setdefault("order", node_index)
    return {
        "seed": seed,
        "effectOrdering": "stable insertion order with explicit node ids",
        "transitionTiming": "frame-rounded by project FPS in renderer",
        "exportConsistency": "scene cache keys and project fingerprint are deterministic",
        "projectFingerprint": _stable_digest(project),
    }


def _asset_license_safety(project: dict[str, Any]) -> dict[str, Any]:
    licenses = project.get("metadata", {}).get("assetLicenses", {})
    warnings = []
    for key in project.get("assets", {}):
        lower = str(key).lower()
        if lower in {"music", "song", "soundtrack"} or "music" in lower:
            if key not in licenses:
                warnings.append(f"Music asset '{key}' has no usage/license metadata.")
        if "font" in lower and key not in licenses:
            warnings.append(f"Font asset '{key}' has no license metadata.")
    return {
        "safeExportMode": bool(project.get("metadata", {}).get("safeExportMode", False)),
        "assetAttribution": licenses,
        "warnings": warnings,
        "codecLicenseAwareness": {
            "h264": "widely supported; check distribution requirements for commercial packaging",
            "aac": "widely supported; check platform policy when redistributing encoders",
        },
    }


def _confidence_explainability(project: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    decisions = report.get("decisions", [])
    average = statistics.mean(float(item.get("confidence", 0.5)) for item in decisions) if decisions else 0.5
    scene_reasons = {}
    for scene in project.get("timeline", []):
        scene_id = str(scene.get("id"))
        matching = [item for item in decisions if item.get("sceneId") == scene_id]
        scene_reasons[scene_id] = {
            "confidence": round(statistics.mean(float(item.get("confidence", 0.5)) for item in matching), 3) if matching else 0.58,
            "whyThisSceneMatters": scene.get("metadata", {}).get("semantic", {}).get("reason", "Scene contributes to the showcase flow."),
            "whyThisCutHappened": scene.get("metadata", {}).get("focusReason", "Cut follows focus, pacing, or transition continuity."),
        }
    return {
        "averageConfidence": round(average, 3),
        "sceneReasons": scene_reasons,
        "safeAIBoundaries": ["locked scenes unchanged", "source media remains immutable", "manual timing preserved", "license warnings do not block local drafts"],
        "decisionCount": len(decisions),
    }


def _apply_scene_metadata(scene: dict[str, Any], key: str, value: Any) -> None:
    scene.setdefault("metadata", {})[key] = value


def _path_for_scene(path: list[dict[str, Any]], scene_start: float, scene_duration: float) -> list[dict[str, Any]]:
    if not path:
        return []
    scene_end = scene_start + scene_duration
    inside = [item for item in path if scene_start - 0.3 <= float(item.get("time", 0)) <= scene_end + 0.3]
    if not inside:
        nearest = min(path, key=lambda item: abs(float(item.get("time", 0)) - (scene_start + scene_duration * 0.5)))
        inside = [nearest]
    rows = []
    for item in inside[:4]:
        local_t = max(0.0, min(scene_duration, float(item.get("time", scene_start)) - scene_start))
        rows.append(
            {
                "time": round(local_t, 3),
                "x": item.get("x", 0.5),
                "y": item.get("y", 0.5),
                "zoom": item.get("zoom", 1.1),
                "easing": item.get("easing", "smoothstep"),
                "reason": item.get("reason"),
            }
        )
    rows.sort(key=lambda item: item["time"])
    if rows[0]["time"] > 0:
        first = dict(rows[0])
        first["time"] = 0
        rows.insert(0, first)
    if rows[-1]["time"] < scene_duration:
        last = dict(rows[-1])
        last["time"] = round(scene_duration, 3)
        rows.append(last)
    return rows


def _soften_scene_zoom(scene: dict[str, Any], report: dict[str, Any]) -> None:
    for layer in scene.get("layers", []):
        camera = layer.get("camera")
        if isinstance(camera, dict) and float(camera.get("zoom", 1) or 1) > 1.2:
            camera["zoom"] = round(1.16, 3)
            report["decisions"].append(_decision(scene.get("id"), "zoom_softening", "Reduced repeated zoom intensity to keep motion intentional.", 0.71))


def _clamp_text_layer(layer: dict[str, Any], width: int, height: int, safe_x: int, safe_y: int) -> None:
    for axis, max_value, safe in (("x", width, safe_x), ("y", height, safe_y)):
        value = layer.get(axis)
        if isinstance(value, (int, float)):
            layer[axis] = max(safe, min(int(value), max_value - safe))


def _balance_text(text: str, max_chars: int) -> str:
    if "\n" in text or len(text) <= max_chars:
        return text
    words = text.split()
    if len(words) <= 2:
        return text
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if len(candidate) > max_chars and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    if len(lines) > 2:
        half = math.ceil(len(words) / 2)
        return " ".join(words[:half]) + "\n" + " ".join(words[half:])
    return "\n".join(lines)


def _font_fallbacks() -> list[str]:
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    return [path for path in candidates if Path(path).exists()]


def _object_tracks(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tracks: list[dict[str, Any]] = []
    for event in events[:20]:
        assigned = False
        for track in tracks:
            last = track["points"][-1]
            if math.dist((float(event.get("x", 0.5)), float(event.get("y", 0.5))), (float(last.get("x", 0.5)), float(last.get("y", 0.5)))) < 0.18:
                track["points"].append({"time": event.get("time"), "x": event.get("x"), "y": event.get("y"), "score": event.get("score")})
                assigned = True
                break
        if not assigned:
            tracks.append({"id": f"track_{len(tracks)+1}", "points": [{"time": event.get("time"), "x": event.get("x"), "y": event.get("y"), "score": event.get("score")}], "label": event.get("reason", "focus region")})
    for track in tracks:
        scores = [float(item.get("score", 0.4) or 0.4) for item in track["points"]]
        track["confidence"] = round(statistics.mean(scores), 3) if scores else 0.4
    return tracks


def _semantic_kind(text: str, scene: dict[str, Any]) -> str:
    rules = [
        ("login_flow", ("login", "sign in", "authenticate", "password")),
        ("dashboard", ("dashboard", "overview", "home", "panel")),
        ("success_state", ("success", "complete", "done", "passed", "fixed")),
        ("loading_state", ("loading", "wait", "progress", "spinner")),
        ("scan", ("scan", "scanner", "analyze", "diagnostic", "troubleshoot")),
        ("analytics_view", ("analytics", "metrics", "chart", "report")),
        ("before_after", ("before", "after", "compare")),
        ("setup_flow", ("setup", "install", "configure", "settings")),
        ("feature_reveal", ("feature", "reveal", "showcase")),
    ]
    for label, terms in rules:
        if any(term in text for term in terms):
            return label
    role = str(scene.get("metadata", {}).get("role", ""))
    if role == "result_moment":
        return "result_payoff"
    if role == "interaction_highlight":
        return "important_ui_interaction"
    return "feature_reveal"


def _semantic_importance(kind: str) -> float:
    return {
        "login_flow": 0.74,
        "dashboard": 0.82,
        "success_state": 0.88,
        "scan": 0.86,
        "analytics_view": 0.78,
        "before_after": 0.84,
        "important_ui_interaction": 0.8,
        "result_payoff": 0.9,
        "feature_reveal": 0.72,
    }.get(kind, 0.58)


def _semantic_reason(kind: str) -> str:
    reasons = {
        "login_flow": "A login or authentication moment establishes the user workflow.",
        "dashboard": "Dashboard views are high-value product context and should stay readable.",
        "success_state": "Success states create the payoff and should be highlighted.",
        "loading_state": "Loading states are usually trimmed unless they clarify progress.",
        "scan": "Scan or diagnostic workflows are core feature demonstrations.",
        "analytics_view": "Analytics/report screens communicate product outcomes.",
        "before_after": "Before/after moments create a clear reveal.",
        "setup_flow": "Setup flows explain how the product becomes useful.",
        "important_ui_interaction": "The user action is visually important.",
        "result_payoff": "This scene completes the promise of the showcase.",
    }
    return reasons.get(kind, "This scene supports the product showcase.")


def _infer_demonstration(moments: list[dict[str, Any]], instructions: str, analysis: dict[str, Any]) -> str:
    states = {item["workflowState"] for item in moments}
    if "scan" in states and "success_state" in states:
        return "scan-to-result product workflow"
    if "login_flow" in states and "dashboard" in states:
        return "login-to-dashboard product walkthrough"
    if "analytics_view" in states:
        return "analytics/reporting showcase"
    if "cyber" in instructions or "security" in instructions:
        return "cybersecurity product showcase"
    if analysis.get("summary", {}).get("focusEventCount", 0):
        return "interaction-led desktop showcase"
    return "general product showcase"


def _scene_text(scene: dict[str, Any]) -> str:
    values = [str(scene.get("id", ""))]
    for layer in scene.get("layers", []):
        if layer.get("text"):
            values.append(str(layer["text"]))
        for item in layer.get("items", []) or []:
            values.append(str(item.get("text", "")))
        if layer.get("title"):
            values.append(str(layer["title"]))
        if layer.get("subtitle"):
            values.append(str(layer["subtitle"]))
    return " ".join(values)


def _direction(dx: float, dy: float) -> str:
    if abs(dx) < 0.015 and abs(dy) < 0.015:
        return "stable"
    if abs(dx) > abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


def _direction_phase(normalized: float) -> str:
    if normalized < 0.18:
        return "hook"
    if normalized < 0.42:
        return "anticipation"
    if normalized < 0.72:
        return "reveal"
    if normalized < 0.9:
        return "payoff"
    return "resolution"


def _repetition_warnings(transitions: list[str], zooms: list[float]) -> list[str]:
    warnings = []
    for left, mid, right in zip(transitions, transitions[1:], transitions[2:]):
        if left == mid == right:
            warnings.append(f"Transition '{left}' repeats three times.")
            break
    if len([value for value in zooms if value > 1.12]) > max(3, len(zooms) * 0.7):
        warnings.append("Zoom behavior is frequent; soften some scenes to avoid robotic motion.")
    return warnings


def _decision(scene_id: Any, kind: str, reason: str, confidence: float) -> dict[str, Any]:
    return {"sceneId": scene_id, "type": kind, "reason": reason, "confidence": round(confidence, 3)}


def _node_key(node: dict[str, Any]) -> str:
    return json.dumps({k: v for k, v in node.items() if k not in {"id", "order"}}, sort_keys=True)


def _stable_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _file_digest(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _asset_quality_score(report: dict[str, Any], duplicate_of: str | None) -> float:
    score = 0.55
    resolution = report.get("resolution") or {}
    if resolution.get("width", 0) >= 1280 and resolution.get("height", 0) >= 720:
        score += 0.12
    motion = float(report.get("motionIntensity") or 0)
    score += min(motion * 3.2, 0.18)
    if report.get("audioPresence"):
        score += 0.04
    if report.get("dominantColors"):
        score += 0.03
    score -= len(report.get("issues", [])) * 0.04
    if duplicate_of:
        score -= 0.18
    return round(max(0.0, min(1.0, score)), 3)


def _highlight_potential(report: dict[str, Any]) -> str:
    motion = float(report.get("motionIntensity") or 0)
    if motion > 0.08:
        return "high-energy"
    if motion > 0.02:
        return "usable"
    return "low-motion"


def _available_encoders() -> dict[str, bool]:
    binary = shutil.which("ffmpeg")
    if not binary:
        return {"nvidia": False, "amd": False, "intel": False}
    result = subprocess.run([binary, "-hide_banner", "-encoders"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    text = (result.stdout or "") + (result.stderr or "")
    return {
        "nvidia": "h264_nvenc" in text or "hevc_nvenc" in text,
        "amd": "h264_amf" in text or "hevc_amf" in text,
        "intel": "h264_qsv" in text or "hevc_qsv" in text,
    }


def _parse_resolution(text: str, fallback_w: int, fallback_h: int) -> tuple[int, int]:
    match = re.search(r"(\d{3,5})x(\d{3,5})", text)
    if match:
        return int(match.group(1)), int(match.group(2))
    return fallback_w or 0, fallback_h or 0


def _regex(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def _float_regex(text: str, pattern: str) -> float | None:
    value = _regex(text, pattern)
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def _compression_risk(text: str) -> str:
    bitrate = _float_regex(text, r"bitrate:\s*(\d+(?:\.\d+)?)\s*kb/s")
    if bitrate is None:
        return "unknown"
    if bitrate < 2500:
        return "high"
    if bitrate < 8000:
        return "medium"
    return "low"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
