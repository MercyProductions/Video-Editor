from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from assets.intelligence import analyze_asset_library
from history.version_history import record_ai_edit
from intelligence.beat_sync import analyze_audio, apply_beat_sync
from styles.presets import apply_style


@dataclass(slots=True)
class DirectorResult:
    project: dict[str, Any]
    report: dict[str, Any]
    history: dict[str, Any] | None


def run_ai_director(
    project_path: Path,
    goal: str,
    *,
    output_path: Path | None = None,
    preserve_scene_ids: list[str] | None = None,
    save_history: bool = True,
) -> DirectorResult:
    project_path = project_path.resolve()
    original = _read_json(project_path)
    project = copy.deepcopy(original)
    preserve = set(preserve_scene_ids or []) | _approved_scene_ids(project)
    asset_report = analyze_asset_library(project_path, project_data=project)
    suggestions = _suggestions(goal, project, asset_report)

    if "gaming" in goal.lower() or "fast" in goal.lower() or "montage" in goal.lower():
        _apply_fast_montage(project, preserve)
        project = apply_style(project, "gaming_montage")
    elif "product" in goal.lower() or "promo" in goal.lower():
        _apply_product_promo(project, preserve)
        project = apply_style(project, "luxury_promo")
    else:
        _apply_general_director_pass(project, preserve)

    _add_caption_hits(project, goal, preserve)
    _add_broll_requests(project, asset_report, preserve)
    _improve_music_timing(project_path, project, preserve, suggestions)
    _refresh_project_duration(project)

    report = {
        "goal": goal,
        "preservedScenes": sorted(preserve),
        "suggestions": suggestions,
        "changedScenes": _changed_scene_ids(original, project),
        "assetIssues": asset_report.get("issues", []),
        "summary": _change_summary(original, project, goal),
    }
    history = None
    if save_history:
        history = record_ai_edit(project_path, original, project, report)
    if output_path:
        _relocate_assets_for_output(project, project_path, output_path)
        _write_json(output_path, project)
        report_path = output_path.with_suffix(".director_report.json")
        _write_json(report_path, report)
    return DirectorResult(project=project, report=report, history=history)


def _apply_fast_montage(project: dict[str, Any], preserve: set[str]) -> None:
    timeline = project.get("timeline", [])
    cursor = 0.0
    for index, scene in enumerate(timeline):
        scene_id = str(scene.get("id", f"scene_{index + 1}"))
        if scene_id not in preserve:
            scene["duration"] = min(max(float(scene.get("duration", 1.6)), 0.9), 2.1)
            scene["transitionOut"] = {"type": "zoom" if index % 3 == 0 else "cut", "duration": 0.2 if index % 3 == 0 else 0}
            for layer in scene.get("layers", []):
                if layer.get("type") in {"video", "image"}:
                    layer.setdefault("animation", {"in": "zoomIn", "duration": 0.25})
                    layer.setdefault("contrast", 1.15)
                if layer.get("type") == "text":
                    layer.setdefault("effects", ["shake"])
                    layer.setdefault("animation", {"in": "slideUp", "out": "fade", "duration": 0.25})
        scene["start"] = round(cursor, 3)
        cursor += float(scene.get("duration", 0))
    project["stylePreset"] = "gaming_montage"


def _apply_product_promo(project: dict[str, Any], preserve: set[str]) -> None:
    cursor = 0.0
    for index, scene in enumerate(project.get("timeline", [])):
        if str(scene.get("id")) not in preserve:
            scene["duration"] = max(float(scene.get("duration", 3)), 3.0)
            scene["transitionOut"] = {"type": "crossfade", "duration": 0.55}
            for layer in scene.get("layers", []):
                if layer.get("type") == "text":
                    layer.setdefault("animation", {"in": "fade", "out": "fade", "duration": 0.45})
        scene["start"] = round(cursor, 3)
        cursor += float(scene.get("duration", 0))
    project["stylePreset"] = "luxury_promo"


def _apply_general_director_pass(project: dict[str, Any], preserve: set[str]) -> None:
    cursor = 0.0
    for index, scene in enumerate(project.get("timeline", [])):
        if str(scene.get("id")) not in preserve and index < len(project.get("timeline", [])) - 1:
            scene.setdefault("transitionOut", {"type": "crossfade", "duration": 0.35})
        scene["start"] = round(cursor, 3)
        cursor += float(scene.get("duration", 0))


def _add_caption_hits(project: dict[str, Any], goal: str, preserve: set[str]) -> None:
    wants_captions = "caption" in goal.lower() or "tiktok" in goal.lower() or "gaming" in goal.lower()
    if not wants_captions:
        return
    for scene in project.get("timeline", []):
        if str(scene.get("id")) in preserve:
            continue
        layers = scene.setdefault("layers", [])
        has_caption = any(layer.get("type") in {"caption", "captions"} for layer in layers)
        if has_caption:
            continue
        label = _scene_caption(scene)
        layers.append(
            {
                "type": "caption",
                "layout": "lower_third",
                "fontSize": 50,
                "color": "#ffffff",
                "strokeColor": "#000000",
                "strokeWidth": 4,
                "box": True,
                "boxColor": "#00000099",
                "items": [{"text": label, "start": 0.15, "duration": min(1.2, float(scene.get("duration", 1)))}],
            }
        )


def _add_broll_requests(project: dict[str, Any], asset_report: dict[str, Any], preserve: set[str]) -> None:
    available = [asset for asset in asset_report.get("assets", []) if asset.get("type") in {"video", "image"} and asset.get("exists")]
    if len(available) < 2:
        return
    for scene in project.get("timeline", []):
        if str(scene.get("id")) in preserve:
            continue
        layers = scene.setdefault("layers", [])
        if not any(layer.get("type") in {"video", "image", "broll"} for layer in layers):
            layers.insert(0, {"type": "broll", "query": str(scene.get("id", "scene")), "layout": "center"})


def _improve_music_timing(project_path: Path, project: dict[str, Any], preserve: set[str], suggestions: list[str]) -> None:
    if preserve:
        suggestions.append("Skipped full beat retiming because preserved scenes were requested.")
        return
    audio_tracks = project.get("audio") or []
    assets = project.get("assets", {})
    if not audio_tracks or not isinstance(assets, dict):
        suggestions.append("No music track available for beat timing.")
        return
    asset_key = str(audio_tracks[0].get("asset", ""))
    raw = assets.get(asset_key)
    if not raw:
        suggestions.append("Music track references an undefined asset.")
        return
    audio_path = Path(str(raw))
    if not audio_path.is_absolute():
        audio_path = project_path.parent / audio_path
    try:
        analysis = analyze_audio(audio_path)
        apply_beat_sync(project, analysis)
        suggestions.append(f"Applied beat timing from {asset_key}; BPM={analysis.get('bpm')}.")
    except Exception as exc:
        suggestions.append(f"Could not analyze music timing: {exc}")


def _suggestions(goal: str, project: dict[str, Any], asset_report: dict[str, Any]) -> list[str]:
    suggestions = [f"Director goal: {goal}"]
    timeline = project.get("timeline", [])
    if len(timeline) < 3:
        suggestions.append("Add more short scenes for stronger pacing.")
    missing = [asset for asset in asset_report.get("assets", []) if not asset.get("exists")]
    if missing:
        suggestions.append(f"Resolve {len(missing)} missing assets before final render.")
    quiet_assets = [asset for asset in asset_report.get("assets", []) if (asset.get("motionIntensity") or 1) < 0.006 and asset.get("type") == "video"]
    if quiet_assets:
        suggestions.append("Some clips have low motion; use them as background or B-roll.")
    return suggestions


def _scene_caption(scene: dict[str, Any]) -> str:
    for layer in scene.get("layers", []):
        if layer.get("type") == "text" and layer.get("text"):
            return str(layer["text"])
    return str(scene.get("id", "Scene")).replace("_", " ").title()


def _approved_scene_ids(project: dict[str, Any]) -> set[str]:
    metadata = project.get("metadata", {})
    explicit = set(metadata.get("preservedScenes", []) if isinstance(metadata, dict) else [])
    for scene in project.get("timeline", []):
        if scene.get("approved") or scene.get("locked") or scene.get("lock"):
            explicit.add(str(scene.get("id")))
    return explicit


def _changed_scene_ids(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    old_by_id = {str(scene.get("id")): scene for scene in old.get("timeline", [])}
    changed = []
    for scene in new.get("timeline", []):
        scene_id = str(scene.get("id"))
        if old_by_id.get(scene_id) != scene:
            changed.append(scene_id)
    return changed


def _change_summary(old: dict[str, Any], new: dict[str, Any], goal: str) -> str:
    return (
        f"Applied AI Director goal '{goal}'. "
        f"Scenes changed: {len(_changed_scene_ids(old, new))}. "
        f"Duration: {old.get('project', {}).get('duration')} -> {new.get('project', {}).get('duration')}."
    )


def _refresh_project_duration(project: dict[str, Any]) -> None:
    duration = max((float(scene.get("start", 0)) + float(scene.get("duration", 0)) for scene in project.get("timeline", [])), default=0)
    project.setdefault("project", {})["duration"] = round(duration, 3)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def _relocate_assets_for_output(data: dict[str, Any], source_project_path: Path, output_path: Path) -> None:
    if source_project_path.parent.resolve() == output_path.parent.resolve():
        return
    assets = data.get("assets", {})
    if not isinstance(assets, dict):
        return
    for key, value in list(assets.items()):
        raw = Path(str(value))
        if not raw.is_absolute():
            assets[key] = str((source_project_path.parent / raw).resolve())
