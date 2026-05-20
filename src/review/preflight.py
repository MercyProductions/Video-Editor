from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from assets.intelligence import analyze_asset_library
from media.compat import EXPORT_FORMATS, analyze_media
from quality.checker import run_quality_check
from utils.media import run_ffmpeg


SAFE_ACTIONS = {
    "adjust_caption_timing",
    "move_text_safe_zone",
    "lower_effect_intensity",
    "normalize_audio",
    "replace_transition",
}


def run_final_preflight(
    project_path: Path,
    *,
    preview_video: Path | None = None,
    output_path: Path | None = None,
    export_format: str = "mp4",
) -> dict[str, Any]:
    project_path = project_path.resolve()
    data = json.loads(project_path.read_text(encoding="utf-8"))
    issues: list[dict[str, Any]] = []
    accepted = set(_accepted_issue_ids(data))
    settings = data.get("project", {})
    width = int(settings.get("width", 1920) or 1920)
    height = int(settings.get("height", 1080) or 1080)
    fps = int(settings.get("fps", 30) or 30)
    duration = _timeline_duration(data)
    asset_report = analyze_asset_library(project_path, project_data=data)
    quality_report = run_quality_check(project_path)

    _check_assets(data, asset_report, issues)
    _check_review_state(data, issues)
    _check_audio(data, asset_report, issues, duration)
    _check_text_and_captions(data, issues, width, height)
    _check_motion_safety(data, issues)
    _check_export_preset(data, issues, export_format)
    _check_quality_report(quality_report, issues)
    if preview_video and preview_video.exists():
        _check_preview_video(preview_video.resolve(), issues)

    for issue in issues:
        issue["id"] = _issue_id(issue)
        issue["accepted"] = issue["id"] in accepted
        issue["blocking"] = issue["severity"] == "error" and not issue["accepted"]

    scores = _scores(data, issues)
    blocking = [issue for issue in issues if issue["blocking"]]
    warnings_remaining = [issue for issue in issues if issue["severity"] in {"error", "warning"} and not issue["accepted"]]
    report = {
        "project": str(project_path),
        "previewVideo": str(preview_video.resolve()) if preview_video else None,
        "ready": not blocking,
        "warningsRemaining": len(warnings_remaining),
        "blockingCount": len(blocking),
        "issueCount": len(issues),
        "issues": issues,
        "autoFixSuggestions": [_suggestion(issue) for issue in issues if not issue.get("accepted")],
        "scores": scores,
        "exportReadinessScore": _readiness_score(scores, issues),
        "summary": _export_summary(data, export_format, width, height, fps, duration, len(warnings_remaining)),
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def repair_final_preflight(
    project_path: Path,
    *,
    output_path: Path,
    issue_id: str | None = None,
    mode: str = "all",
    preview_video: Path | None = None,
    export_format: str = "mp4",
) -> dict[str, Any]:
    project_path = project_path.resolve()
    data = json.loads(project_path.read_text(encoding="utf-8"))
    report = run_final_preflight(project_path, preview_video=preview_video, export_format=export_format)
    issues = report.get("issues", [])
    applied: list[dict[str, Any]] = []

    if mode in {"ignore", "accept"}:
        if not issue_id:
            raise ValueError("Ignoring a preflight issue requires --issue-id.")
        _accept_issue(data, issue_id)
        applied.append({"issueId": issue_id, "action": "accepted"})
    else:
        targets = issues if mode == "all" else [issue for issue in issues if issue.get("id") == issue_id]
        if mode == "selected" and not targets:
            raise KeyError(f"Preflight issue not found: {issue_id}")
        for issue in targets:
            action = (issue.get("autoFix") or {}).get("type")
            if action not in SAFE_ACTIONS or issue.get("accepted"):
                continue
            if _apply_fix(data, issue):
                applied.append({"issueId": issue.get("id"), "action": action})

    data.setdefault("metadata", {}).setdefault("finalPreflight", {})
    data["metadata"]["finalPreflight"]["lastRepair"] = {
        "mode": mode,
        "issueId": issue_id,
        "applied": applied,
    }
    if output_path.resolve().parent != project_path.parent:
        _absolutize_assets(data, project_path.parent)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    followup = run_final_preflight(output_path, preview_video=preview_video, export_format=export_format)
    return {
        "output": str(output_path.resolve()),
        "applied": applied,
        "reportBefore": report,
        "reportAfter": followup,
        "project": data,
    }


def _check_assets(data: dict[str, Any], asset_report: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    assets = data.get("assets", {}) if isinstance(data.get("assets"), dict) else {}
    referenced = _referenced_assets(data)
    reports = {asset.get("key"): asset for asset in asset_report.get("assets", [])}
    for key, kind in referenced.items():
        if key not in assets:
            issues.append(_issue("missing_assets", "error", f"Referenced {kind} asset is not defined: {key}", asset=key, auto_fix=None))
            continue
        report = reports.get(key)
        if not report or not report.get("exists"):
            issues.append(_issue("missing_assets", "error", f"Missing asset: {key}", asset=key, auto_fix=None, suggestion="Relink missing asset."))
            continue
        media = report.get("mediaMetadata") or {}
        if media.get("broken"):
            issues.append(_issue("broken_clips", "error", f"Broken media file: {key}", asset=key, auto_fix=None, suggestion="Replace or normalize the broken clip."))
        for media_issue in media.get("issues", []) + report.get("issues", []):
            message = str(media_issue.get("message", "Asset issue."))
            severity = "error" if str(media_issue.get("severity")) == "error" else "warning"
            if "Variable frame rate" in message:
                issues.append(_issue("audio_video_sync", "warning", f"{key}: VFR can cause sync drift; normalize before final export.", asset=key, auto_fix=None, suggestion="Normalize media on import."))
            elif "sample rate" in message:
                issues.append(_issue("audio_video_sync", "warning", f"{key}: audio sample rate should be normalized to 48 kHz.", asset=key, auto_fix={"type": "normalize_audio", "label": "Normalize audio settings"}))
            elif severity == "error":
                issues.append(_issue("broken_clips", "error", f"{key}: {message}", asset=key, auto_fix=None))


def _check_review_state(data: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    review = data.get("metadata", {}).get("previewReview", {})
    review_gate_active = bool(review.get("enforceExportGate")) if isinstance(review, dict) else False
    markers = review.get("markers", []) if isinstance(review, dict) else []
    for marker in markers:
        if marker.get("resolved") or marker.get("type") == "keep":
            continue
        issues.append(
            _issue(
                "unresolved_review_markers",
                "error",
                f"Unresolved preview marker: {str(marker.get('type', 'marker')).replace('_', ' ')}",
                scene=marker.get("sceneId"),
                time=marker.get("time"),
                auto_fix=None,
                suggestion="Review the marker, repair the scene, or lock it as accepted.",
            )
        )
    scenes = data.get("timeline", [])
    explicit_scene_review = any(isinstance(scene, dict) and "reviewStatus" in scene for scene in scenes)
    if not review_gate_active and not explicit_scene_review:
        return
    for scene in data.get("timeline", []):
        if scene.get("excludeFromFinal"):
            continue
        status = scene.get("reviewStatus")
        if status not in {"approved", "locked"}:
            severity = "error" if review_gate_active else "warning"
            issues.append(
                _issue(
                    "unapproved_scenes",
                    severity,
                    f"Scene has not been explicitly approved: {scene.get('id')}",
                    scene=scene.get("id"),
                    auto_fix=None,
                    suggestion="Approve or lock the scene if you are using the review workflow.",
                )
            )


def _check_audio(data: dict[str, Any], asset_report: dict[str, Any], issues: list[dict[str, Any]], duration: float) -> None:
    audio = data.get("audio", []) or []
    assets = {asset.get("key"): asset for asset in asset_report.get("assets", [])}
    if not audio:
        issues.append(_issue("dead_silence", "warning", "No project audio track is configured.", auto_fix=None, suggestion="Add music/SFX or accept intentional silence."))
        return
    covered_until = 0.0
    for track in audio:
        start = float(track.get("start", 0) or 0)
        volume = float(track.get("volume", 1) or 1)
        asset = assets.get(track.get("asset"), {})
        asset_duration = float(asset.get("duration", 0) or 0)
        track_duration = float(track.get("duration", 0) or 0) or asset_duration
        covered_until = max(covered_until, start + track_duration)
        if start > duration + 0.05:
            issues.append(_issue("audio_desync", "error", "Audio starts after the timeline ends.", asset=track.get("asset"), auto_fix={"type": "normalize_audio", "label": "Move audio back into timeline"}))
        if volume <= 0.01:
            issues.append(_issue("dead_silence", "warning", "Audio volume is effectively muted.", asset=track.get("asset"), auto_fix={"type": "normalize_audio", "label": "Restore audible volume"}))
    if covered_until + 0.75 < duration:
        issues.append(_issue("dead_silence", "warning", "Audio ends before the video finishes.", auto_fix={"type": "normalize_audio", "label": "Extend/loop audio timing"}))


def _check_text_and_captions(data: dict[str, Any], issues: list[dict[str, Any]], width: int, height: int) -> None:
    background = str(data.get("project", {}).get("background", "#000000"))
    for scene in data.get("timeline", []):
        scene_duration = float(scene.get("duration", 0) or 0)
        for layer in scene.get("layers", []):
            if layer.get("type") in {"text", "lower_third"}:
                _check_text_position(layer, scene, issues, width, height)
                color = str(layer.get("color", "#ffffff"))
                if _contrast_ratio(color, background) < 3.0:
                    issues.append(_issue("unreadable_contrast", "warning", "Text contrast may be unreadable.", scene=scene.get("id"), auto_fix={"type": "lower_effect_intensity", "label": "Improve text contrast"}))
            if layer.get("type") in {"caption", "captions"}:
                _check_text_position(layer, scene, issues, width, height)
                for item in layer.get("items", []):
                    start = float(item.get("start", 0) or 0)
                    duration = float(item.get("duration", max(float(item.get("end", 0) or 0) - start, 0.01)) or 0.01)
                    words = len(str(item.get("text", "")).split())
                    if words and words / max(duration, 0.01) > 4.25:
                        issues.append(_issue("caption_timing", "warning", "Caption is too fast to read.", scene=scene.get("id"), time=start, auto_fix={"type": "adjust_caption_timing", "label": "Slow caption timing"}))
                    if start + duration > scene_duration + 0.08:
                        issues.append(_issue("caption_timing", "warning", "Caption extends beyond its scene.", scene=scene.get("id"), time=start, auto_fix={"type": "adjust_caption_timing", "label": "Clamp caption to scene"}))


def _check_text_position(layer: dict[str, Any], scene: dict[str, Any], issues: list[dict[str, Any]], width: int, height: int) -> None:
    x = layer.get("x")
    y = layer.get("y")
    outside = False
    if isinstance(x, (int, float)) and not (width * 0.05 <= float(x) <= width * 0.95):
        outside = True
    if isinstance(y, (int, float)) and not (height * 0.05 <= float(y) <= height * 0.95):
        outside = True
    if outside:
        issues.append(_issue("safe_zones", "warning", "Text is outside the safe zone.", scene=scene.get("id"), auto_fix={"type": "move_text_safe_zone", "label": "Move text into safe zone"}))


def _check_motion_safety(data: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    short_scenes = [scene for scene in data.get("timeline", []) if float(scene.get("duration", 0) or 0) < 0.55]
    if len(short_scenes) >= 3:
        issues.append(_issue("excessive_flashing", "warning", "Several very short scenes may create excessive flashing.", auto_fix={"type": "replace_transition", "label": "Soften rapid cuts"}))
    for scene in data.get("timeline", []):
        if _scene_has_aggressive_effect(scene):
            issues.append(_issue("excessive_flashing", "warning", "Aggressive shake/pulse effects may be uncomfortable.", scene=scene.get("id"), auto_fix={"type": "lower_effect_intensity", "label": "Lower effect intensity"}))


def _check_export_preset(data: dict[str, Any], issues: list[dict[str, Any]], export_format: str) -> None:
    settings = data.get("project", {})
    width = int(settings.get("width", 0) or 0)
    height = int(settings.get("height", 0) or 0)
    preset = str(data.get("exportPreset") or settings.get("exportPreset") or "custom")
    if preset in {"tiktok_reels", "shorts", "instagram_reels"} and width > height:
        issues.append(_issue("export_preset_mismatch", "error", f"{preset} expects vertical video but project is landscape.", auto_fix=None, suggestion="Use a vertical export preset or reformat first."))
    if preset == "youtube_1080p" and height > width:
        issues.append(_issue("export_preset_mismatch", "warning", "YouTube landscape preset is being used on vertical video.", auto_fix=None, suggestion="Switch to Shorts/TikTok/Reels preset."))
    if export_format not in EXPORT_FORMATS:
        issues.append(_issue("export_preset_mismatch", "error", f"Unsupported export format: {export_format}", auto_fix=None))


def _check_quality_report(quality_report: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    for item in quality_report.get("issues", []):
        message = str(item.get("message", "Quality warning."))
        category = "technical_quality"
        if "contrast" in message.lower():
            category = "unreadable_contrast"
        if "safe zone" in message.lower():
            category = "safe_zones"
        issues.append(
            _issue(
                category,
                "error" if item.get("severity") == "error" else "warning",
                message,
                scene=item.get("scene"),
                asset=item.get("asset"),
                auto_fix=_quality_auto_fix(message),
            )
        )


def _check_preview_video(preview_video: Path, issues: list[dict[str, Any]]) -> None:
    media = analyze_media(preview_video)
    if media.get("broken"):
        issues.append(_issue("broken_clips", "error", "Preview video cannot be decoded.", auto_fix=None))
        return
    result = run_ffmpeg(["-hide_banner", "-nostats", "-i", str(preview_video), "-vf", "blackdetect=d=0.35:pix_th=0.1,freezedetect=n=-60dB:d=0.8", "-an", "-f", "null", "-"])
    output = (result.stderr or "") + (result.stdout or "")
    if "black_start" in output:
        issues.append(_issue("black_frames", "warning", "Black frames detected in the approved preview.", auto_fix={"type": "replace_transition", "label": "Replace transition or trim black frames"}))
    if "freeze_start" in output:
        issues.append(_issue("frozen_frames", "warning", "Frozen frames detected in the approved preview.", auto_fix={"type": "replace_transition", "label": "Replace transition or regenerate scene"}))


def _apply_fix(data: dict[str, Any], issue: dict[str, Any]) -> bool:
    action = (issue.get("autoFix") or {}).get("type")
    if action == "adjust_caption_timing":
        return _fix_caption_timing(data, issue.get("scene"))
    if action == "move_text_safe_zone":
        return _fix_safe_zone(data, issue.get("scene"))
    if action == "lower_effect_intensity":
        return _fix_effect_intensity(data, issue.get("scene"))
    if action == "normalize_audio":
        return _fix_audio(data)
    if action == "replace_transition":
        return _fix_transition(data, issue.get("scene"))
    return False


def _fix_caption_timing(data: dict[str, Any], scene_id: str | None) -> bool:
    changed = False
    for scene in _target_scenes(data, scene_id):
        scene_duration = float(scene.get("duration", 0) or 0)
        for layer in scene.get("layers", []):
            if layer.get("type") not in {"caption", "captions"}:
                continue
            for item in layer.get("items", []):
                words = len(str(item.get("text", "")).split())
                start = float(item.get("start", 0) or 0)
                target = max(float(item.get("duration", 0) or 0), words / 3.2 if words else 0.8)
                item["duration"] = round(max(0.4, min(target, max(scene_duration - start, 0.4))), 3)
                changed = True
    return changed


def _fix_safe_zone(data: dict[str, Any], scene_id: str | None) -> bool:
    settings = data.get("project", {})
    width = float(settings.get("width", 1920) or 1920)
    height = float(settings.get("height", 1080) or 1080)
    changed = False
    for scene in _target_scenes(data, scene_id):
        for layer in scene.get("layers", []):
            if layer.get("type") not in {"text", "caption", "captions", "lower_third"}:
                continue
            if isinstance(layer.get("x"), (int, float)):
                layer["x"] = round(min(max(float(layer["x"]), width * 0.08), width * 0.92), 3)
                changed = True
            if isinstance(layer.get("y"), (int, float)):
                layer["y"] = round(min(max(float(layer["y"]), height * 0.08), height * 0.92), 3)
                changed = True
    return changed


def _fix_effect_intensity(data: dict[str, Any], scene_id: str | None) -> bool:
    changed = False
    for scene in _target_scenes(data, scene_id):
        post = scene.get("postProcessing")
        if isinstance(post, dict):
            for key in ("glow", "bloom", "vignette"):
                if isinstance(post.get(key), (int, float)):
                    post[key] = round(min(float(post[key]), 0.28), 3)
                    changed = True
        for layer in scene.get("layers", []):
            effects = layer.get("effects")
            if isinstance(effects, list) and any(str(item).lower() in {"shake", "pulse"} for item in effects):
                layer["effects"] = [item for item in effects if str(item).lower() not in {"shake", "pulse"}]
                changed = True
            if isinstance(layer.get("animation"), dict) and layer["animation"].get("in") in {"shake", "pulse"}:
                layer["animation"]["in"] = "fade"
                changed = True
    return changed


def _fix_audio(data: dict[str, Any]) -> bool:
    changed = False
    for track in data.get("audio", []) or []:
        if float(track.get("volume", 1) or 1) <= 0.01:
            track["volume"] = 0.8
            changed = True
        track["start"] = max(float(track.get("start", 0) or 0), 0)
        track.setdefault("fadeIn", 0.25)
        track.setdefault("fadeOut", 0.75)
        changed = True
    return changed


def _fix_transition(data: dict[str, Any], scene_id: str | None) -> bool:
    changed = False
    scenes = data.get("timeline", [])
    for scene in _target_scenes(data, scene_id):
        if scene is scenes[-1]:
            continue
        scene["transitionOut"] = {"type": "crossfade", "duration": 0.25}
        changed = True
    return changed


def _target_scenes(data: dict[str, Any], scene_id: str | None) -> list[dict[str, Any]]:
    scenes = data.get("timeline", [])
    if not scene_id:
        return scenes
    return [scene for scene in scenes if scene.get("id") == scene_id]


def _accepted_issue_ids(data: dict[str, Any]) -> list[str]:
    final = data.get("metadata", {}).get("finalPreflight", {})
    accepted = final.get("acceptedIssues", []) if isinstance(final, dict) else []
    return [str(item) for item in accepted]


def _accept_issue(data: dict[str, Any], issue_id: str) -> None:
    metadata = data.setdefault("metadata", {})
    final = metadata.setdefault("finalPreflight", {})
    accepted = list(final.get("acceptedIssues", []))
    if issue_id not in accepted:
        accepted.append(issue_id)
    final["acceptedIssues"] = accepted


def _referenced_assets(data: dict[str, Any]) -> dict[str, str]:
    refs: dict[str, str] = {}
    for scene in data.get("timeline", []):
        for layer in scene.get("layers", []):
            if layer.get("asset"):
                refs[str(layer["asset"])] = str(layer.get("type", "media"))
    for track in data.get("audio", []) or []:
        if track.get("asset"):
            refs[str(track["asset"])] = "audio"
    return refs


def _absolutize_assets(data: dict[str, Any], root: Path) -> None:
    assets = data.get("assets")
    if not isinstance(assets, dict):
        return
    for key, value in list(assets.items()):
        path = Path(str(value))
        assets[key] = str(path if path.is_absolute() else (root / path).resolve())


def _timeline_duration(data: dict[str, Any]) -> float:
    return round(max([float(data.get("project", {}).get("duration", 0) or 0)] + [float(scene.get("start", 0) or 0) + float(scene.get("duration", 0) or 0) for scene in data.get("timeline", [])]), 3)


def _scene_has_aggressive_effect(scene: dict[str, Any]) -> bool:
    text = json.dumps(scene).lower()
    return "shake" in text or "pulse" in text or "flash" in text


def _quality_auto_fix(message: str) -> dict[str, str] | None:
    lower = message.lower()
    if "caption" in lower:
        return {"type": "adjust_caption_timing", "label": "Adjust caption timing"}
    if "safe zone" in lower or "position" in lower:
        return {"type": "move_text_safe_zone", "label": "Move text into safe zone"}
    if "audio" in lower:
        return {"type": "normalize_audio", "label": "Normalize audio"}
    if "contrast" in lower:
        return {"type": "lower_effect_intensity", "label": "Improve contrast"}
    return None


def _issue(
    category: str,
    severity: str,
    message: str,
    *,
    scene: Any = None,
    asset: Any = None,
    time: Any = None,
    auto_fix: dict[str, str] | None = None,
    suggestion: str | None = None,
) -> dict[str, Any]:
    return {
        "category": category,
        "severity": severity,
        "message": message,
        "scene": scene,
        "asset": asset,
        "time": time,
        "autoFix": auto_fix,
        "suggestion": suggestion or _default_suggestion(category),
        "safeAutoFix": bool(auto_fix and auto_fix.get("type") in SAFE_ACTIONS),
    }


def _issue_id(issue: dict[str, Any]) -> str:
    payload = "|".join(str(issue.get(key, "")) for key in ["category", "severity", "message", "scene", "asset", "time"])
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


def _default_suggestion(category: str) -> str:
    return {
        "missing_assets": "Relink missing asset.",
        "broken_clips": "Replace or normalize broken media.",
        "unresolved_review_markers": "Fix, ignore, or accept the preview marker.",
        "unapproved_scenes": "Approve or lock the scene before final export.",
        "audio_desync": "Normalize audio timing.",
        "caption_timing": "Adjust caption timing.",
        "safe_zones": "Move text into safe zone.",
        "unreadable_contrast": "Improve text contrast or lower effects.",
        "excessive_flashing": "Lower effect intensity.",
        "dead_silence": "Add or normalize audio.",
        "black_frames": "Trim section or replace transition.",
        "frozen_frames": "Regenerate scene or replace transition.",
        "export_preset_mismatch": "Switch preset or reformat.",
    }.get(category, "Review before final export.")


def _suggestion(issue: dict[str, Any]) -> dict[str, Any]:
    return {
        "issueId": issue.get("id"),
        "category": issue.get("category"),
        "message": issue.get("message"),
        "suggestion": issue.get("suggestion"),
        "safeAutoFix": issue.get("safeAutoFix"),
        "autoFix": issue.get("autoFix"),
    }


def _scores(data: dict[str, Any], issues: list[dict[str, Any]]) -> dict[str, int]:
    def score(categories: set[str], base: int = 100) -> int:
        value = base
        for issue in issues:
            if issue.get("accepted") or issue.get("category") not in categories:
                continue
            value -= 18 if issue.get("severity") == "error" else 8
        return max(0, min(100, value))

    scene_count = max(len(data.get("timeline", [])), 1)
    very_short = len([scene for scene in data.get("timeline", []) if float(scene.get("duration", 0) or 0) < 0.75])
    pacing = max(0, 100 - very_short * 7 - len([issue for issue in issues if issue.get("category") in {"unresolved_review_markers", "unapproved_scenes"} and not issue.get("accepted")]) * 8)
    return {
        "pacing": min(100, pacing + min(scene_count * 2, 8)),
        "readability": score({"caption_timing", "safe_zones", "unreadable_contrast"}),
        "audio": score({"audio_desync", "dead_silence"}),
        "brandConsistency": score({"export_preset_mismatch", "unreadable_contrast"}, base=92),
        "technicalReadiness": score({"missing_assets", "broken_clips", "black_frames", "frozen_frames", "technical_quality", "export_preset_mismatch"}),
    }


def _readiness_score(scores: dict[str, int], issues: list[dict[str, Any]]) -> int:
    average = sum(scores.values()) / max(len(scores), 1)
    blocking = len([issue for issue in issues if issue.get("blocking")])
    warnings = len([issue for issue in issues if issue.get("severity") == "warning" and not issue.get("accepted")])
    return max(0, min(100, round(average - blocking * 14 - warnings * 2)))


def _export_summary(data: dict[str, Any], export_format: str, width: int, height: int, fps: int, duration: float, warnings_remaining: int) -> dict[str, Any]:
    preset = str(data.get("exportPreset") or data.get("project", {}).get("exportPreset") or "custom")
    captions_included = bool(data.get("captions")) or any(layer.get("type") in {"caption", "captions"} for scene in data.get("timeline", []) for layer in scene.get("layers", []))
    thumbnail = data.get("metadata", {}).get("thumbnail") or data.get("thumbnail")
    export = EXPORT_FORMATS.get(export_format, EXPORT_FORMATS["mp4"])
    bitrate = _suggested_bitrate(width, height, fps)
    return {
        "platform": preset,
        "resolution": {"width": width, "height": height},
        "duration": duration,
        "fps": fps,
        "codec": export.get("videoCodec", "h264"),
        "audioCodec": export.get("audioCodec"),
        "bitrate": bitrate,
        "captionsIncluded": captions_included,
        "thumbnailIncluded": bool(thumbnail),
        "warningsRemaining": warnings_remaining,
    }


def _suggested_bitrate(width: int, height: int, fps: int) -> str:
    pixels = width * height
    if pixels >= 3840 * 2160:
        return "45-68 Mbps"
    if pixels >= 1920 * 1080:
        return "12-20 Mbps" if fps <= 30 else "20-35 Mbps"
    if pixels >= 1280 * 720:
        return "5-10 Mbps"
    return "2-5 Mbps"


def _contrast_ratio(foreground: str, background: str) -> float:
    fg = _luminance(_hex_to_rgb(foreground))
    bg = _luminance(_hex_to_rgb(background))
    lighter = max(fg, bg)
    darker = min(fg, bg)
    return (lighter + 0.05) / (darker + 0.05)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    match = re.search(r"#?([0-9a-fA-F]{6})", value)
    clean = match.group(1) if match else "ffffff"
    return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))


def _luminance(rgb: tuple[int, int, int]) -> float:
    values = []
    for channel in rgb:
        normalized = channel / 255
        values.append(normalized / 12.92 if normalized <= 0.03928 else ((normalized + 0.055) / 1.055) ** 2.4)
    return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]
