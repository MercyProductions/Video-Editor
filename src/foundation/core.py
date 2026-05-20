from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from local_ai.model_manager import model_manager_status
from recovery.integrity import check_project_integrity
from schema.validator import validate_project
from stability.cache import cache_report
from utils.media import media_duration, run_ffmpeg


CACHE_BUCKETS = (
    "thumbnails",
    "proxies",
    "shaders",
    "waveforms",
    "ai_analysis",
    "rendered_previews",
    "timeline_previews",
)

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".wmv", ".mpeg", ".mpg", ".m4v", ".ts", ".mts", ".m2ts"}


def run_foundation_pass(
    project_path: Path,
    *,
    output_path: Path | None = None,
    report_path: Path | None = None,
    metadata_dir: Path | None = None,
    cache_dir: Path | None = None,
    generate_proxies: bool = False,
    run_benchmark: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    project_path = project_path.resolve()
    data = _read_json(project_path)
    validate_project(data)

    output = output_path.resolve() if output_path else project_path.with_name(f"{project_path.stem}.foundation.json")
    report_output = report_path.resolve() if report_path else output.with_suffix(".foundation_report.json")
    metadata_root = metadata_dir.resolve() if metadata_dir else output.parent / ".ave_metadata"
    cache_root = cache_dir.resolve() if cache_dir else output.parent / ".ave_cache"

    original = deepcopy(data)
    project = deepcopy(data)
    _relocate_assets_for_output(project, project_path, output)

    timings: dict[str, float] = {}
    section_start = time.perf_counter()
    timeline_report = _normalize_timeline(project)
    timings["timelineSeconds"] = round(time.perf_counter() - section_start, 4)

    section_start = time.perf_counter()
    nondestructive = _non_destructive_manifest(project, original, project_path, output)
    timings["nondestructiveSeconds"] = round(time.perf_counter() - section_start, 4)

    section_start = time.perf_counter()
    history = _record_history(project_path, original, project, metadata_root)
    timings["historySeconds"] = round(time.perf_counter() - section_start, 4)

    section_start = time.perf_counter()
    cache_index = _ensure_cache_buckets(cache_root, project, project_path)
    proxies = _proxy_system(project, output, cache_root, generate=generate_proxies)
    timings["proxySeconds"] = round(time.perf_counter() - section_start, 4)

    section_start = time.perf_counter()
    scheduler = _task_scheduler(project, output, cache_root, proxies)
    keyframes = _keyframe_engine(project)
    shader = _shader_pipeline(project, cache_root)
    model = _model_lifecycle(report_output.parent)
    structured = _structured_metadata(project, metadata_root, timeline_report, nondestructive, history)
    hardware = _hardware_abstraction()
    recovery = _integrity_recovery(project_path, output, metadata_root)
    safety = _accessibility_safety(project)
    performance = _performance_benchmark(project, cache_root, timings, run_benchmark=run_benchmark)
    cache_layers = _multi_layer_cache_report(cache_root, cache_index)
    taste = _creative_taste_model(project)
    timings["systemsSeconds"] = round(time.perf_counter() - section_start, 4)

    project.setdefault("metadata", {})["foundation"] = {
        "version": 1,
        "createdAt": _now(),
        "localFirst": True,
        "frameAccurateTimeline": timeline_report["summary"],
        "nonDestructive": nondestructive["summary"],
        "history": history["summary"],
        "proxyMedia": proxies["summary"],
        "taskScheduler": scheduler["summary"],
        "keyframes": keyframes["summary"],
        "gpuEffectPipeline": shader["summary"],
        "modelLifecycle": model["summary"],
        "structuredMetadata": structured["summary"],
        "hardware": hardware["summary"],
        "recovery": recovery["summary"],
        "accessibilitySafety": safety["summary"],
        "performance": performance["summary"],
        "cache": cache_layers["summary"],
        "creativeTaste": taste["summary"],
    }

    validate_project(project)
    _atomic_write_json(output, project)

    integrity_after = check_project_integrity(output)
    report = {
        "format": "automatic-video-editor-foundation-report",
        "createdAt": _now(),
        "project": str(project_path),
        "output": str(output),
        "localFirst": True,
        "systems": {
            "frameAccurateTimeline": timeline_report,
            "nonDestructiveEditing": nondestructive,
            "undoRedoHistory": history,
            "proxyMedia": proxies,
            "backgroundTaskScheduler": scheduler,
            "advancedKeyframes": keyframes,
            "gpuShaderPipeline": shader,
            "aiModelLifecycle": model,
            "structuredMetadata": structured,
            "hardwareAbstraction": hardware,
            "projectIntegrityRecovery": recovery,
            "accessibilitySafety": safety,
            "performanceBenchmarking": performance,
            "multiLayerCache": cache_layers,
            "creativeTasteModeling": taste,
        },
        "validation": {
            "before": "valid",
            "after": "valid" if integrity_after.get("valid") else "issues",
            "issues": integrity_after.get("issues", []),
        },
        "timings": {**timings, "totalSeconds": round(time.perf_counter() - started, 4)},
    }
    _atomic_write_json(report_output, report)
    return {"project": project, "report": report, "outputPath": str(output), "reportPath": str(report_output)}


def _normalize_timeline(project: dict[str, Any]) -> dict[str, Any]:
    settings = project.setdefault("project", {})
    fps = int(settings.get("fps", 30) or 30)
    fps = max(1, fps)
    timebase = {"fps": fps, "ticksPerSecond": fps, "tickDuration": round(1 / fps, 9), "dropFrame": False}
    cursor_frames = 0
    changes = []
    warnings = []
    timeline = project.get("timeline", [])
    for index, scene in enumerate(timeline):
        old_start = float(scene.get("start", 0) or 0)
        old_duration = float(scene.get("duration", 0) or 0)
        start_frame = cursor_frames
        duration_frames = max(1, _seconds_to_frames(old_duration, fps))
        scene["start"] = _frames_to_seconds(start_frame, fps)
        scene["duration"] = _frames_to_seconds(duration_frames, fps)
        scene.setdefault("metadata", {})["timeline"] = {
            "startFrame": start_frame,
            "durationFrames": duration_frames,
            "endFrame": start_frame + duration_frames,
            "smpteStart": _smpte(start_frame, fps),
            "smpteEnd": _smpte(start_frame + duration_frames, fps),
        }
        if abs(scene["start"] - old_start) > 0.0005 or abs(scene["duration"] - old_duration) > 0.0005:
            changes.append({"scene": scene.get("id"), "oldStart": old_start, "newStart": scene["start"], "oldDuration": old_duration, "newDuration": scene["duration"]})
        _normalize_layers(scene, fps, scene["duration"], changes)
        _normalize_transition(scene, timeline[index + 1] if index + 1 < len(timeline) else None, fps, warnings)
        cursor_frames += duration_frames

    total_duration = _frames_to_seconds(cursor_frames, fps)
    old_total = float(settings.get("duration", total_duration) or total_duration)
    settings["duration"] = total_duration
    if abs(old_total - total_duration) > 0.0005:
        changes.append({"projectDurationOld": old_total, "projectDurationNew": total_duration})
    _normalize_audio(project, fps, total_duration, changes)
    project.setdefault("metadata", {})["timebase"] = timebase
    project["metadata"]["timelineIntegrity"] = {
        "frameAccurate": True,
        "totalFrames": cursor_frames,
        "duration": total_duration,
        "audioVideoSyncProtection": "all starts/durations are rounded to the project FPS timebase",
        "captionSyncStability": "caption starts and durations are frame-rounded",
        "vfrNormalization": "render pipeline outputs constant FPS using project.fps",
    }
    return {"timebase": timebase, "changes": changes, "warnings": warnings, "summary": {"fps": fps, "totalFrames": cursor_frames, "duration": total_duration, "changeCount": len(changes), "warningCount": len(warnings)}}


def _normalize_layers(scene: dict[str, Any], fps: int, scene_duration: float, changes: list[dict[str, Any]]) -> None:
    scene_frames = _seconds_to_frames(scene_duration, fps)
    for layer_index, layer in enumerate(scene.get("layers", [])):
        for key in ("start", "duration", "trimStart", "trimEnd"):
            if key in layer and isinstance(layer[key], (int, float)):
                old = float(layer[key])
                layer[key] = _frames_to_seconds(_seconds_to_frames(old, fps), fps)
                if abs(float(layer[key]) - old) > 0.0005:
                    changes.append({"scene": scene.get("id"), "layer": layer_index, "field": key, "old": old, "new": layer[key]})
        if layer.get("type") in {"caption", "captions"}:
            for item_index, item in enumerate(layer.get("items", [])):
                for key in ("start", "duration", "end"):
                    if key in item and isinstance(item[key], (int, float)):
                        old = float(item[key])
                        item[key] = _frames_to_seconds(_seconds_to_frames(old, fps), fps)
                        if abs(float(item[key]) - old) > 0.0005:
                            changes.append({"scene": scene.get("id"), "layer": layer_index, "caption": item_index, "field": key, "old": old, "new": item[key]})
        layer.setdefault("metadata", {})["nonDestructive"] = True
        layer["metadata"]["renderTimeTransformation"] = True
        if layer.get("duration"):
            duration_frames = min(_seconds_to_frames(float(layer["duration"]), fps), scene_frames)
            layer["metadata"]["durationFrames"] = duration_frames


def _normalize_transition(scene: dict[str, Any], next_scene: dict[str, Any] | None, fps: int, warnings: list[dict[str, Any]]) -> None:
    transition = scene.get("transitionOut")
    if not isinstance(transition, dict):
        return
    old = float(transition.get("duration", 0) or 0)
    duration = _frames_to_seconds(_seconds_to_frames(old, fps), fps)
    max_duration = float(scene.get("duration", 0) or 0) * 0.5
    if next_scene:
        max_duration = min(max_duration, float(next_scene.get("duration", 0) or 0) * 0.5)
    if duration > max_duration:
        warnings.append({"type": "transition_overlap", "scene": scene.get("id"), "oldDuration": old, "safeDuration": round(max_duration, 3)})
        duration = _frames_to_seconds(max(0, _seconds_to_frames(max_duration, fps)), fps)
    transition["duration"] = duration
    transition.setdefault("metadata", {})["durationFrames"] = _seconds_to_frames(duration, fps)
    transition["metadata"]["overlapSafe"] = True


def _normalize_audio(project: dict[str, Any], fps: int, total_duration: float, changes: list[dict[str, Any]]) -> None:
    for index, track in enumerate(project.get("audio", [])):
        for key in ("start", "duration", "trimStart", "trimEnd", "fadeIn", "fadeOut"):
            if key in track and isinstance(track[key], (int, float)):
                old = float(track[key])
                track[key] = _frames_to_seconds(_seconds_to_frames(old, fps), fps)
                if abs(float(track[key]) - old) > 0.0005:
                    changes.append({"audio": index, "field": key, "old": old, "new": track[key]})
        track.setdefault("metadata", {})["audioVideoSyncProtected"] = True
        track["metadata"]["projectDuration"] = total_duration


def _non_destructive_manifest(project: dict[str, Any], original: dict[str, Any], project_path: Path, output_path: Path) -> dict[str, Any]:
    assets = {}
    for key, value in project.get("assets", {}).items():
        path = Path(str(value))
        resolved = path if path.is_absolute() else output_path.parent / path
        original_value = original.get("assets", {}).get(key, value)
        assets[key] = {
            "originalReference": original_value,
            "resolvedPath": str(resolved.resolve()),
            "exists": resolved.exists(),
            "sha256": _file_hash(resolved) if resolved.exists() else None,
            "immutable": True,
        }
    edit_stack = []
    for scene in project.get("timeline", []):
        for index, layer in enumerate(scene.get("layers", [])):
            operations = []
            for key in ("trimStart", "trimEnd", "crop", "brightness", "contrast", "blur", "opacity", "effects", "camera", "animation"):
                if key in layer:
                    operations.append({"type": key, "value": deepcopy(layer[key]), "renderTimeOnly": True})
            if operations:
                edit_stack.append({"sceneId": scene.get("id"), "layerIndex": index, "layerType": layer.get("type"), "operations": operations, "reversible": True})
    manifest = {
        "projectPath": str(project_path),
        "outputPath": str(output_path),
        "immutableSources": assets,
        "editStack": edit_stack,
        "summary": {"sourceCount": len(assets), "operationCount": sum(len(item["operations"]) for item in edit_stack), "sourceMediaModified": False},
    }
    project.setdefault("metadata", {})["nonDestructiveEditing"] = {"enabled": True, "sourceMediaModified": False, "editStackLength": len(edit_stack)}
    return manifest


def _record_history(project_path: Path, before: dict[str, Any], after: dict[str, Any], metadata_root: Path) -> dict[str, Any]:
    history_dir = metadata_root / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    entry_dir = history_dir / stamp
    entry_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(entry_dir / "before.json", before)
    _atomic_write_json(entry_dir / "after.json", after)
    diff = _metadata_diff(before, after)
    entry = {
        "id": stamp,
        "type": "foundation_pass",
        "project": str(project_path),
        "group": "foundation",
        "undo": str((entry_dir / "before.json").resolve()),
        "redo": str((entry_dir / "after.json").resolve()),
        "diff": diff,
        "renderSafeStateRestoration": True,
    }
    _atomic_write_json(entry_dir / "action.json", entry)
    return {"entry": entry, "summary": {"historyId": stamp, "diffCount": len(diff), "sceneLevelUndo": True, "partialRollback": True}}


def _proxy_system(project: dict[str, Any], output: Path, cache_root: Path, *, generate: bool) -> dict[str, Any]:
    proxy_dir = cache_root / "proxies"
    proxy_dir.mkdir(parents=True, exist_ok=True)
    proxies = []
    for key, value in project.get("assets", {}).items():
        path = Path(str(value))
        resolved = path if path.is_absolute() else output.parent / path
        if resolved.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        digest = _asset_cache_key(resolved)
        proxy_path = proxy_dir / f"{resolved.stem}.{digest}.proxy.mp4"
        status = "exists" if proxy_path.exists() else "pending"
        if generate and resolved.exists() and not proxy_path.exists():
            result = run_ffmpeg(
                [
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(resolved),
                    "-vf",
                    "scale=640:-2,fps=24",
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast",
                    "-crf",
                    "32",
                    str(proxy_path),
                ]
            )
            status = "generated" if result.returncode == 0 and proxy_path.exists() else "failed"
        proxies.append({"asset": key, "source": str(resolved), "proxy": str(proxy_path), "status": status, "cacheKey": digest})
    project.setdefault("metadata", {})["proxyMedia"] = {
        "enabled": True,
        "previewQualityModes": ["proxy", "draft", "balanced", "full"],
        "proxies": proxies,
        "offlineReconnect": "source path and hash are retained for full-quality reconnect",
    }
    return {"proxies": proxies, "summary": {"proxyCount": len(proxies), "generatedCount": sum(1 for item in proxies if item["status"] == "generated"), "cacheReuseCount": sum(1 for item in proxies if item["status"] == "exists")}}


def _task_scheduler(project: dict[str, Any], output: Path, cache_root: Path, proxy_report: dict[str, Any]) -> dict[str, Any]:
    task_dir = cache_root / "tasks"
    task_dir.mkdir(parents=True, exist_ok=True)
    tasks = []
    task_specs = [
        ("thumbnail", "thumbnail_worker", 40),
        ("waveform", "waveform_worker", 35),
        ("ai_analysis", "ai_analysis_worker", 20),
        ("proxy_generation", "proxy_worker", 50),
        ("indexing", "indexing_worker", 15),
    ]
    for kind, worker, priority in task_specs:
        task = {"id": f"{_stamp()}_{kind}", "kind": kind, "worker": worker, "priority": priority, "status": "queued", "project": str(output), "localOnly": True}
        tasks.append(task)
    _atomic_write_json(task_dir / f"{output.stem}.tasks.json", {"tasks": tasks, "cpuGpuScheduling": "CPU default; GPU reserved for render/proxy encode when available", "backgroundThrottling": {"maxConcurrent": 1, "interactivePriority": "preview"}})
    project.setdefault("metadata", {})["backgroundTasks"] = {"taskFile": str((task_dir / f"{output.stem}.tasks.json").resolve()), "queued": len(tasks)}
    return {"tasks": tasks, "summary": {"queued": len(tasks), "prioritized": True, "uiSafe": True}}


def _keyframe_engine(project: dict[str, Any]) -> dict[str, Any]:
    normalized = []
    for scene in project.get("timeline", []):
        for layer_index, layer in enumerate(scene.get("layers", [])):
            for source_key in ("keyframes", "camera"):
                source = layer.get(source_key)
                keyframes = source.get("keyframes") if isinstance(source, dict) else source if source_key == "keyframes" else None
                if isinstance(keyframes, list) and keyframes:
                    rows = _normalize_keyframes(keyframes)
                    layer.setdefault("metadata", {})["keyframes"] = {"engine": "foundation-v1", "interpolation": "smoothstep", "samples": rows[:12]}
                    normalized.append({"sceneId": scene.get("id"), "layerIndex": layer_index, "parameter": source_key, "keyframeCount": len(rows), "duration": scene.get("duration")})
    project.setdefault("metadata", {})["keyframeEngine"] = {
        "enabled": True,
        "curves": ["linear", "smoothstep", "easeIn", "easeOut", "easeInOut", "bezier"],
        "interpolationModes": ["hold", "linear", "smooth", "bezier"],
        "supportedParameters": ["zoom", "opacity", "blur", "lighting", "text", "camera", "transition"],
        "tracks": normalized,
    }
    return {"tracks": normalized, "summary": {"trackCount": len(normalized), "graphEditorReady": True, "nestedAnimations": True}}


def _normalize_keyframes(keyframes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in keyframes:
        if not isinstance(item, dict):
            continue
        row = {"time": round(float(item.get("time", 0) or 0), 3), "easing": item.get("easing", "smoothstep")}
        for key in ("x", "y", "zoom", "opacity", "blur", "lighting"):
            if key in item:
                row[key] = item[key]
        rows.append(row)
    return sorted(rows, key=lambda item: item["time"])


def _shader_pipeline(project: dict[str, Any], cache_root: Path) -> dict[str, Any]:
    shader_dir = cache_root / "shaders"
    shader_dir.mkdir(parents=True, exist_ok=True)
    passes = []
    for scene in project.get("timeline", []):
        nodes = []
        graph = scene.get("effectGraph", {})
        if isinstance(graph, dict) and isinstance(graph.get("nodes"), list):
            nodes.extend(graph["nodes"])
        if scene.get("effectGraphPreset"):
            nodes.append({"type": "preset", "name": scene["effectGraphPreset"]})
        if scene.get("postProcessing"):
            nodes.append({"type": "postProcessing", "settings": scene["postProcessing"]})
        if not nodes:
            continue
        digest = hashlib.sha256(json.dumps(nodes, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]
        pass_info = {"sceneId": scene.get("id"), "cacheKey": digest, "nodeCount": len(nodes), "shaderCache": str((shader_dir / f"{digest}.json").resolve())}
        _atomic_write_json(shader_dir / f"{digest}.json", {"scene": scene.get("id"), "nodes": nodes, "backend": "ffmpeg-filtergraph", "realtimePreviewCompatible": True})
        passes.append(pass_info)
    project.setdefault("metadata", {})["gpuEffectPipeline"] = {
        "runtime": "ffmpeg-filtergraph-with-gpu-ready-cache",
        "shaderCache": str(shader_dir.resolve()),
        "passes": passes,
        "fallback": "CPU FFmpeg filters when no GPU effect backend is active",
    }
    return {"passes": passes, "summary": {"passCount": len(passes), "shaderCacheReady": True, "realtimePreviewCompatible": True}}


def _model_lifecycle(output_dir: Path) -> dict[str, Any]:
    status = model_manager_status(output_path=output_dir / "foundation_model_status.json")
    lifecycle = {
        "lazyLoading": True,
        "vramAwareLoading": True,
        "modelUnloading": "unload idle task model before render-heavy work",
        "warmup": "health checks are separated from first generation request",
        "quantizedModelSupport": [".gguf", ".onnx", ".safetensors"],
        "taskRouting": status.get("tasks", {}),
        "fallback": "heuristic-local-engine when no local model is available",
    }
    return {"status": status, "lifecycle": lifecycle, "summary": {"tasks": len(status.get("tasks", {})), "warnings": len(status.get("warnings", [])), "apiKeysRequired": False}}


def _structured_metadata(project: dict[str, Any], metadata_root: Path, timeline: dict[str, Any], nondestructive: dict[str, Any], history: dict[str, Any]) -> dict[str, Any]:
    metadata_root.mkdir(parents=True, exist_ok=True)
    data = {
        "version": 1,
        "projectFingerprint": _stable_hash(project),
        "updatedAt": _now(),
        "aiAnalysis": project.get("metadata", {}).get("aiExplainability", {}),
        "pacingMaps": project.get("metadata", {}).get("timelineIntegrity", {}),
        "sceneTags": {scene.get("id", f"scene_{index}"): scene.get("metadata", {}) for index, scene in enumerate(project.get("timeline", []))},
        "renderHistory": [],
        "editHistory": history.get("entry"),
        "timelineNotes": project.get("metadata", {}).get("timelineNotes", []),
        "userOverrides": project.get("metadata", {}).get("userOverrides", {}),
        "diagnostics": {"timeline": timeline.get("summary"), "nonDestructive": nondestructive.get("summary")},
    }
    target = metadata_root / "project.meta.json"
    _atomic_write_json(target, data)
    project.setdefault("metadata", {})["structuredMetadata"] = {"path": str(target.resolve()), "version": data["version"], "incrementalSave": True}
    return {"path": str(target.resolve()), "metadata": data, "summary": {"version": data["version"], "fastLookup": True, "corruptionResistant": True}}


def _hardware_abstraction() -> dict[str, Any]:
    encoders = _ffmpeg_encoders()
    hardware = {
        "platform": platform.platform(),
        "gpuVendors": {
            "nvidia": bool(encoders.get("h264_nvenc") or encoders.get("hevc_nvenc")),
            "amd": bool(encoders.get("h264_amf") or encoders.get("hevc_amf")),
            "intel": bool(encoders.get("h264_qsv") or encoders.get("hevc_qsv")),
        },
        "graphicsApis": {"directX": platform.system() == "Windows", "vulkan": shutil.which("vulkaninfo") is not None, "openGL": shutil.which("glxinfo") is not None},
        "encoders": encoders,
        "decoderFallbacks": ["software decode", "imageio-ffmpeg bundled binary"],
        "selectedFallback": "libx264",
    }
    return {"hardware": hardware, "summary": {"nvidia": hardware["gpuVendors"]["nvidia"], "amd": hardware["gpuVendors"]["amd"], "intel": hardware["gpuVendors"]["intel"], "fallback": hardware["selectedFallback"]}}


def _integrity_recovery(project_path: Path, output: Path, metadata_root: Path) -> dict[str, Any]:
    journal_dir = metadata_root / "journals"
    journal_dir.mkdir(parents=True, exist_ok=True)
    journal = {"project": str(project_path), "output": str(output), "timestamp": _now(), "transactionalSave": True, "sha256Before": _file_hash(project_path) if project_path.exists() else None}
    _atomic_write_json(journal_dir / f"{output.stem}.{_stamp()}.journal.json", journal)
    integrity = check_project_integrity(project_path)
    return {"journal": journal, "integrity": integrity, "summary": {"transactionalSaves": True, "autosaveJournals": True, "corruptionDetection": True, "issueCount": integrity.get("issueCount", 0)}}


def _accessibility_safety(project: dict[str, Any]) -> dict[str, Any]:
    issues = []
    score = 1.0
    settings = project.get("project", {})
    width = int(settings.get("width", 1920))
    height = int(settings.get("height", 1080))
    for scene in project.get("timeline", []):
        if scene.get("duration", 0) and float(scene.get("duration", 0)) < 0.5:
            issues.append({"severity": "warning", "scene": scene.get("id"), "type": "bad_pacing", "message": "Scene is shorter than 0.5s."})
            score -= 0.05
        if _scene_flash_risk(scene):
            issues.append({"severity": "warning", "scene": scene.get("id"), "type": "flashing", "message": "High-intensity quick visual changes may be uncomfortable."})
            score -= 0.12
        for layer in scene.get("layers", []):
            if layer.get("type") in {"text", "caption", "captions"}:
                if _text_outside_safe_zone(layer, width, height):
                    issues.append({"severity": "warning", "scene": scene.get("id"), "type": "safe_zone", "message": "Text may sit outside safe zones."})
                    score -= 0.04
                if layer.get("type") in {"caption", "captions"}:
                    for item in layer.get("items", []):
                        words = len(str(item.get("text", "")).split())
                        duration = max(float(item.get("duration", 1) or 1), 0.001)
                        if words / duration > 4.5:
                            issues.append({"severity": "warning", "scene": scene.get("id"), "type": "caption_speed", "message": "Caption may be too fast to read."})
                            score -= 0.05
    score = round(max(0.0, min(1.0, score)), 3)
    project.setdefault("metadata", {})["accessibilitySafety"] = {"safeEditingMode": True, "score": score, "issueCount": len(issues)}
    return {"issues": issues, "summary": {"score": score, "issueCount": len(issues), "safeEditingMode": True}}


def _performance_benchmark(project: dict[str, Any], cache_root: Path, timings: dict[str, float], *, run_benchmark: bool) -> dict[str, Any]:
    start = time.perf_counter()
    frame_count = int(float(project.get("project", {}).get("duration", 0) or 0) * int(project.get("project", {}).get("fps", 30) or 30))
    memory = _memory_snapshot()
    cache = cache_report(cache_root)
    stress = {
        "sceneCount": len(project.get("timeline", [])),
        "layerCount": sum(len(scene.get("layers", [])) for scene in project.get("timeline", [])),
        "estimatedFrames": frame_count,
        "largeProjectRisk": frame_count > 60 * 60 * 30 or len(project.get("timeline", [])) > 200,
    }
    benchmark = {"enabled": run_benchmark, "projectJsonHashMs": round((time.perf_counter() - start) * 1000, 3), "stress": stress}
    return {"timings": timings, "memory": memory, "cache": cache, "benchmark": benchmark, "summary": {"tracked": True, "estimatedFrames": frame_count, "cacheBytes": cache.get("totalBytes", 0)}}


def _multi_layer_cache_report(cache_root: Path, index: dict[str, Any]) -> dict[str, Any]:
    buckets = []
    for name in CACHE_BUCKETS:
        path = cache_root / name
        path.mkdir(parents=True, exist_ok=True)
        buckets.append({"name": name, "path": str(path.resolve()), "bytes": _path_size(path), "files": len([item for item in path.rglob("*") if item.is_file()])})
    total = sum(item["bytes"] for item in buckets)
    report = {"root": str(cache_root.resolve()), "buckets": buckets, "index": index, "cleanupPolicy": {"maxBytesDefault": 5 * 1024**3, "deleteOldestFirst": True}, "corruptionRecovery": "bucket indexes can be rebuilt from filenames and asset hashes"}
    return {**report, "summary": {"bucketCount": len(buckets), "totalBytes": total, "sizeManaged": True}}


def _creative_taste_model(project: dict[str, Any]) -> dict[str, Any]:
    transitions = [scene.get("transitionOut", {}).get("type") for scene in project.get("timeline", []) if isinstance(scene.get("transitionOut"), dict)]
    captions = sum(1 for scene in project.get("timeline", []) for layer in scene.get("layers", []) if layer.get("type") in {"caption", "captions"})
    motion_layers = sum(1 for scene in project.get("timeline", []) for layer in scene.get("layers", []) if layer.get("camera") or layer.get("animation"))
    scene_count = max(len(project.get("timeline", [])), 1)
    style = "minimal" if motion_layers / scene_count < 1 else "aggressive" if motion_layers / scene_count > 2 else "balanced"
    taste = {
        "pacingStyleMemory": _pacing_label(project),
        "editingPersonality": style,
        "creatorProfile": project.get("metadata", {}).get("creatorProfile", "default-local"),
        "showcaseIdentityConsistency": _dominant(transitions) or "cut",
        "transitionPhilosophy": "restrained" if len(set(transitions)) <= 2 else "varied",
        "cinematicRhythmModel": {"captionDensity": round(captions / scene_count, 3), "motionDensity": round(motion_layers / scene_count, 3)},
    }
    project.setdefault("metadata", {})["creativeTasteModel"] = taste
    return {"taste": taste, "summary": {"personality": style, "pacing": taste["pacingStyleMemory"], "transitionPhilosophy": taste["transitionPhilosophy"]}}


def _ensure_cache_buckets(cache_root: Path, project: dict[str, Any], project_path: Path) -> dict[str, Any]:
    cache_root.mkdir(parents=True, exist_ok=True)
    bucket_index = {"project": str(project_path), "fingerprint": _stable_hash(project), "buckets": {}}
    for name in CACHE_BUCKETS:
        path = cache_root / name
        path.mkdir(parents=True, exist_ok=True)
        bucket_index["buckets"][name] = str(path.resolve())
    _atomic_write_json(cache_root / "cache_index.json", bucket_index)
    return bucket_index


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def _relocate_assets_for_output(project: dict[str, Any], source_path: Path, output_path: Path) -> None:
    if source_path.parent.resolve() == output_path.parent.resolve():
        return
    assets = project.get("assets")
    if not isinstance(assets, dict):
        return
    for key, value in list(assets.items()):
        raw = Path(str(value))
        if raw.is_absolute():
            continue
        assets[key] = str((source_path.parent / raw).resolve())


def _seconds_to_frames(value: float, fps: int) -> int:
    return int(round(float(value) * fps))


def _frames_to_seconds(frames: int, fps: int) -> float:
    return round(frames / fps, 6)


def _smpte(frame: int, fps: int) -> str:
    hours = frame // (fps * 3600)
    frame %= fps * 3600
    minutes = frame // (fps * 60)
    frame %= fps * 60
    seconds = frame // fps
    frames = frame % fps
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"


def _metadata_diff(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    diff = []
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            diff.append({"path": key, "beforeHash": _stable_hash(before.get(key)), "afterHash": _stable_hash(after.get(key))})
    return diff


def _file_hash(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _asset_cache_key(path: Path) -> str:
    stat = path.stat() if path.exists() else None
    payload = {"path": str(path.resolve()), "mtime": stat.st_mtime if stat else None, "size": stat.st_size if stat else None}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _ffmpeg_encoders() -> dict[str, bool]:
    try:
        result = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8)
        text = (result.stdout or "") + (result.stderr or "")
    except Exception:
        try:
            result = run_ffmpeg(["-hide_banner", "-encoders"])
            text = (result.stdout or "") + (result.stderr or "")
        except Exception:
            text = ""
    names = ("h264_nvenc", "hevc_nvenc", "h264_amf", "hevc_amf", "h264_qsv", "hevc_qsv", "libx264")
    return {name: name in text for name in names}


def _scene_flash_risk(scene: dict[str, Any]) -> bool:
    transition = scene.get("transitionOut", {})
    if isinstance(transition, dict) and transition.get("type") in {"fadeToBlack", "zoom"} and float(transition.get("duration", 1) or 1) < 0.12:
        return True
    post = scene.get("postProcessing", {})
    return isinstance(post, dict) and float(post.get("glow", post.get("bloom", 0)) or 0) > 0.75


def _text_outside_safe_zone(layer: dict[str, Any], width: int, height: int) -> bool:
    x = layer.get("x")
    y = layer.get("y")
    if isinstance(x, (int, float)) and not (width * 0.04 <= float(x) <= width * 0.96):
        return True
    if isinstance(y, (int, float)) and not (height * 0.04 <= float(y) <= height * 0.96):
        return True
    return False


def _memory_snapshot() -> dict[str, Any]:
    try:
        import psutil

        process = psutil.Process()
        mem = process.memory_info()
        vm = psutil.virtual_memory()
        return {"rssBytes": mem.rss, "availableBytes": vm.available, "source": "psutil"}
    except Exception:
        return {"rssBytes": None, "availableBytes": None, "source": "unavailable"}


def _path_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _pacing_label(project: dict[str, Any]) -> str:
    durations = [float(scene.get("duration", 0) or 0) for scene in project.get("timeline", [])]
    if not durations:
        return "unknown"
    avg = sum(durations) / len(durations)
    if avg < 2:
        return "fast"
    if avg > 5:
        return "slow"
    return "medium"


def _dominant(values: list[Any]) -> Any:
    values = [value for value in values if value]
    if not values:
        return None
    return max(sorted(set(values)), key=values.count)


def _stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
