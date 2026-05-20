from __future__ import annotations

import copy
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

from metrics.store import record_metric
from presets.export_presets import apply_export_preset, get_export_preset
from quality.checker import run_quality_check
from social.posting_package import collect_caption_items, inspect_video
from utils.media import run_ffmpeg


SUCCESS_TAGS = {
    "good_pacing",
    "good_style",
    "reuse_this",
    "too_much_motion",
    "captions_too_fast",
}


def review_export(
    project_path: Path,
    video_path: Path,
    *,
    package_dir: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    project_path = project_path.resolve()
    video_path = video_path.resolve()
    project = _read_json(project_path)
    video_info = inspect_video(video_path) if video_path.exists() else {"path": str(video_path), "duration": 0, "width": 0, "height": 0, "hasAudio": False, "fileSizeBytes": 0}
    package = _package_paths(package_dir)
    captions = collect_caption_items(project)
    issues = _detect_post_export_issues(project_path, project, video_path, video_info, package, captions)
    review = {
        "postExportReviewVersion": 1,
        "localOnly": True,
        "createdAt": _now(),
        "project": str(project_path),
        "video": str(video_path),
        "packageDir": str(package_dir.resolve()) if package_dir else None,
        "playbackReview": {
            "videoPath": str(video_path),
            "exists": video_path.exists(),
            "playable": video_info.get("duration", 0) > 0 and video_info.get("width", 0) > 0,
            "duration": video_info.get("duration", 0),
            "resolution": {"width": video_info.get("width", 0), "height": video_info.get("height", 0)},
            "hasAudio": bool(video_info.get("hasAudio", False)),
            "audioVideoSyncRisk": _sync_risk(project, video_info),
            "captions": package.get("captions") or _caption_summary(captions),
            "thumbnail": package.get("thumbnail"),
            "exportFolder": str((package_dir or video_path.parent).resolve()),
        },
        "issues": issues,
        "issueCount": len(issues),
        "quickReExportOptions": _quick_reexport_options(project),
        "reuseOptions": _reuse_options(project),
        "readyForReuse": not any(issue["severity"] == "error" for issue in issues),
    }
    if output_path:
        _write_json(output_path, review)
    record_metric("post_export_review", {"issues": len(issues), "video": str(video_path)})
    return review


def create_quick_reexport_project(
    project_path: Path,
    *,
    output_dir: Path,
    preset: str | None = None,
    format_name: str | None = None,
    mode: str = "custom",
    captions: str = "keep",
    thumbnail: str | None = None,
) -> dict[str, Any]:
    project_path = project_path.resolve()
    source = _read_json(project_path)
    project = copy.deepcopy(source)
    selected_preset = _quick_preset(mode, preset, project)
    preset_data = get_export_preset(selected_preset)
    if preset_data:
        project["project"] = apply_export_preset(project.get("project", {}), selected_preset)
        project["exportPreset"] = preset_data.key
    project.setdefault("metadata", {})["postExportReexport"] = {
        "createdAt": _now(),
        "sourceProject": str(project_path),
        "mode": mode,
        "preset": selected_preset,
        "format": format_name or (preset_data.container if preset_data else "mp4"),
        "captions": captions,
        "thumbnail": thumbnail,
    }
    if captions == "off":
        _remove_caption_layers(project)
    elif captions == "on":
        project.setdefault("metadata", {})["captionsIncluded"] = True
    if thumbnail:
        project.setdefault("metadata", {})["thumbnailOverride"] = thumbnail
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{project_path.stem}.{_slug(mode)}.{_slug(selected_preset or 'custom')}.json"
    _relocate_assets_for_output(project, project_path, output)
    _write_json(output, project)
    report = {
        "reexportVersion": 1,
        "source": str(project_path),
        "outputProject": str(output.resolve()),
        "mode": mode,
        "preset": selected_preset,
        "format": format_name or (preset_data.container if preset_data else "mp4"),
        "captions": captions,
        "thumbnail": thumbnail,
        "renderCommand": f"python render.py render \"{output.resolve()}\" --preset {selected_preset or 'youtube_1080p'} --format {format_name or 'mp4'} --quality final",
    }
    _write_json(output_dir / "quick_reexport_summary.json", report)
    record_metric("post_export_reexport", {"mode": mode, "preset": selected_preset})
    return report


def save_reusable_template(
    project_path: Path,
    *,
    output_path: Path,
    name: str,
    video_path: Path | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    project_path = project_path.resolve()
    project = _read_json(project_path)
    metadata = project.get("metadata", {}) if isinstance(project.get("metadata"), dict) else {}
    brand_kit = metadata.get("brandKit", {}) if isinstance(metadata.get("brandKit"), dict) else {}
    template = {
        "templateVersion": 1,
        "localOnly": True,
        "name": name,
        "createdAt": _now(),
        "sourceProject": str(project_path),
        "sourceVideo": str(video_path.resolve()) if video_path else None,
        "note": note,
        "style": {
            "stylePreset": project.get("stylePreset") or metadata.get("stylePreset"),
            "colorProfile": metadata.get("colorProfile") or brand_kit.get("colors"),
            "lightingProfile": metadata.get("lighting") or metadata.get("showcaseStyle"),
        },
        "pacing": _pacing_profile(project),
        "captionFormat": _caption_profile(project),
        "exportSettings": {
            "preset": project.get("exportPreset") or project.get("project", {}).get("exportPreset"),
            "width": project.get("project", {}).get("width"),
            "height": project.get("project", {}).get("height"),
            "fps": project.get("project", {}).get("fps"),
            "crf": project.get("project", {}).get("crf"),
        },
        "intro": _scene_summary((project.get("timeline") or [None])[0]),
        "outro": _scene_summary((project.get("timeline") or [None])[-1]),
        "transitionProfile": dict(Counter(_transition_type(scene) for scene in project.get("timeline", []) if _transition_type(scene))),
    }
    _write_json(output_path, template)
    record_metric("post_export_template_saved", {"name": name})
    return {**template, "path": str(output_path.resolve())}


def create_post_export_variants(
    project_path: Path,
    *,
    output_dir: Path,
    variants: list[str] | None = None,
    hook: str | None = None,
    cta: str | None = None,
) -> dict[str, Any]:
    project_path = project_path.resolve()
    source = _read_json(project_path)
    requested = variants or ["shorter", "longer", "hook", "cta", "thumbnail", "caption_style"]
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for variant in requested:
        project = copy.deepcopy(source)
        key = _slug(variant)
        if key == "shorter":
            _fit_duration(project, max(4.0, _project_duration(project) * 0.75))
        elif key == "longer":
            _extend_duration(project, _project_duration(project) * 1.2)
        elif key == "hook":
            _replace_first_text(project, hook or _alternate_hook(project))
        elif key == "cta":
            _replace_last_text(project, cta or _alternate_cta(project))
        elif key == "thumbnail":
            project.setdefault("metadata", {})["thumbnailVariant"] = "alternate_high_contrast"
        elif key == "caption_style":
            _apply_caption_style_variant(project)
        project.setdefault("metadata", {})["postExportVariant"] = {"type": key, "sourceProject": str(project_path), "createdAt": _now()}
        output = output_dir / key / "project.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        _relocate_assets_for_output(project, project_path, output)
        _write_json(output, project)
        outputs.append({"variant": key, "path": str(output.resolve()), "duration": round(_project_duration(project), 3)})
    summary = {"variantVersion": 1, "source": str(project_path), "outputDir": str(output_dir.resolve()), "outputs": outputs}
    _write_json(output_dir / "post_export_variants.json", summary)
    record_metric("post_export_variants", {"count": len(outputs)})
    return summary


def record_success_note(
    project_path: Path,
    *,
    video_path: Path | None = None,
    profile: str = "Default Creator",
    tags: list[str] | None = None,
    note: str | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    clean_tags = [_slug(tag) for tag in tags or [] if tag]
    clean_tags = [tag for tag in clean_tags if tag in SUCCESS_TAGS or tag]
    entry = {
        "noteVersion": 1,
        "localOnly": True,
        "createdAt": _now(),
        "profile": profile,
        "project": str(project_path.resolve()),
        "video": str(video_path.resolve()) if video_path else None,
        "tags": clean_tags,
        "note": note,
    }
    path = output_path or Path(__file__).resolve().parents[2] / "feedback" / "post_export_notes" / _slug(profile) / f"{project_path.stem}_{int(time.time() * 1000)}.json"
    _write_json(path, entry)
    record_metric("post_export_success_note", {"profile": profile, "tags": clean_tags})
    return {**entry, "path": str(path.resolve())}


def _detect_post_export_issues(
    project_path: Path,
    project: dict[str, Any],
    video_path: Path,
    video_info: dict[str, Any],
    package: dict[str, Any],
    captions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not video_path.exists():
        issues.append(_issue("missing_output", "error", "Final exported video is missing.", "Re-run final export."))
        return issues
    decode_errors = _decode_errors(video_path)
    if decode_errors:
        issues.append(_issue("corrupted_output", "error", "FFmpeg reported decode errors in the exported video.", "Retry export with render reliability enabled."))
    if not video_info.get("duration") or not video_info.get("width"):
        issues.append(_issue("not_playable", "error", "Exported video could not be inspected as playable.", "Retry export or choose a safer MP4 preset."))
    expected = _expected_preset(project)
    if expected and (int(video_info.get("width", 0) or 0), int(video_info.get("height", 0) or 0)) != (expected.width, expected.height):
        issues.append(_issue("wrong_resolution", "warning", f"Export is {video_info.get('width')}x{video_info.get('height')} but {expected.key} expects {expected.width}x{expected.height}.", "Quick re-export with the matching platform preset."))
    expected_duration = _project_duration(project)
    actual_duration = float(video_info.get("duration", 0) or 0)
    if expected_duration and actual_duration and abs(expected_duration - actual_duration) > max(1.0, expected_duration * 0.08):
        issues.append(_issue("wrong_duration", "warning", f"Export duration is {round(actual_duration, 2)}s but project timeline is {round(expected_duration, 2)}s.", "Review timeline trims and retry final export."))
    if not video_info.get("hasAudio"):
        issues.append(_issue("missing_audio", "warning", "Exported video has no detectable audio stream.", "Re-export with audio enabled or add music/SFX before delivery."))
    caption_report = _caption_summary(captions)
    if caption_report["count"] and caption_report["maxWordsPerSecond"] > 4.2:
        issues.append(_issue("bad_captions", "warning", "Some captions may be too fast to read.", "Create a caption-style variant or regenerate caption timing."))
    if project_has_captions(project) and not package.get("captions", {}).get("srt"):
        issues.append(_issue("missing_caption_exports", "warning", "Project has captions but the package does not include SRT/VTT files.", "Recreate the upload package."))
    size = int(video_info.get("fileSizeBytes", 0) or 0)
    if size > 512 * 1024 * 1024:
        issues.append(_issue("file_too_large", "warning", f"Export file is large ({size} bytes).", "Quick re-export with low-size preview or Discord compressed preset."))
    if _compression_artifact_risk(video_info):
        issues.append(_issue("compression_artifacts", "info", "Bitrate looks low for the resolution and duration.", "Create a higher-quality re-export and compare playback."))
    if package.get("thumbnail") and not Path(package["thumbnail"]).exists():
        issues.append(_issue("missing_thumbnail", "warning", "Package thumbnail is missing.", "Regenerate the posting package or thumbnail variant."))
    quality = run_quality_check(project_path)
    for item in quality.get("issues", [])[:4]:
        if "caption" in str(item.get("message", "")).lower() or "safe zone" in str(item.get("message", "")).lower():
            issues.append(_issue("project_quality", "info", str(item.get("message", "Project quality warning.")), "Open the project quality checker before re-export."))
    return _dedupe_issues(issues)


def _issue(issue_id: str, severity: str, message: str, suggestion: str) -> dict[str, Any]:
    return {"id": issue_id, "severity": severity, "message": message, "suggestion": suggestion}


def _package_paths(package_dir: Path | None) -> dict[str, Any]:
    if not package_dir:
        return {}
    root = package_dir.resolve()
    captions = {
        "srt": str((root / "captions.srt").resolve()) if (root / "captions.srt").exists() else None,
        "vtt": str((root / "captions.vtt").resolve()) if (root / "captions.vtt").exists() else None,
        "transcript": str((root / "transcript.txt").resolve()) if (root / "transcript.txt").exists() else None,
    }
    return {
        "folder": str(root),
        "thumbnail": str((root / "thumbnail.png").resolve()) if (root / "thumbnail.png").exists() else None,
        "captions": captions,
        "manifest": str((root / "package_manifest.json").resolve()) if (root / "package_manifest.json").exists() else None,
    }


def _caption_summary(captions: list[dict[str, Any]]) -> dict[str, Any]:
    max_wps = 0.0
    for item in captions:
        words = len(str(item.get("text", "")).split())
        duration = max(0.1, float(item.get("end", 0) or 0) - float(item.get("start", 0) or 0))
        max_wps = max(max_wps, words / duration)
    return {"count": len(captions), "maxWordsPerSecond": round(max_wps, 2)}


def _sync_risk(project: dict[str, Any], video_info: dict[str, Any]) -> str:
    expected = _project_duration(project)
    actual = float(video_info.get("duration", 0) or 0)
    if not expected or not actual:
        return "unknown"
    delta = abs(expected - actual)
    return "high" if delta > max(2.0, expected * 0.12) else "medium" if delta > max(0.8, expected * 0.06) else "low"


def _decode_errors(video_path: Path) -> str:
    result = run_ffmpeg(["-v", "error", "-i", str(video_path), "-f", "null", "-"])
    output = ((result.stderr or "") + (result.stdout or "")).strip()
    return output[:1000]


def _compression_artifact_risk(video_info: dict[str, Any]) -> bool:
    duration = float(video_info.get("duration", 0) or 0)
    width = int(video_info.get("width", 0) or 0)
    height = int(video_info.get("height", 0) or 0)
    size = int(video_info.get("fileSizeBytes", 0) or 0)
    if duration <= 0 or width <= 0 or height <= 0 or size <= 0:
        return False
    bits_per_pixel_second = (size * 8) / max(1, width * height * duration)
    return bits_per_pixel_second < 0.045


def _quick_reexport_options(project: dict[str, Any]) -> list[dict[str, str]]:
    current = project.get("exportPreset") or project.get("project", {}).get("exportPreset") or "youtube_1080p"
    return [
        {"label": "Lower file size", "mode": "lower_size", "preset": "low_size_preview", "captions": "keep"},
        {"label": "Higher quality", "mode": "higher_quality", "preset": "high_quality_archive", "captions": "keep"},
        {"label": "Different platform", "mode": "platform", "preset": "shorts", "captions": "keep"},
        {"label": "Captions off", "mode": "captions_off", "preset": str(current), "captions": "off"},
    ]


def _reuse_options(project: dict[str, Any]) -> dict[str, Any]:
    return {
        "canSaveTemplate": bool(project.get("timeline")),
        "variantTypes": ["shorter", "longer", "hook", "cta", "thumbnail", "caption_style"],
        "successTags": sorted(SUCCESS_TAGS),
    }


def _quick_preset(mode: str, preset: str | None, project: dict[str, Any]) -> str | None:
    if preset:
        return preset
    if mode == "lower_size":
        return "low_size_preview"
    if mode == "higher_quality":
        return "high_quality_archive"
    return str(project.get("exportPreset") or project.get("project", {}).get("exportPreset") or "youtube_1080p")


def _expected_preset(project: dict[str, Any]):
    key = project.get("exportPreset") or project.get("project", {}).get("exportPreset")
    try:
        return get_export_preset(str(key)) if key else None
    except ValueError:
        return None


def _project_duration(project: dict[str, Any]) -> float:
    duration = project.get("project", {}).get("duration")
    if duration:
        return float(duration)
    end = 0.0
    for scene in project.get("timeline", []) or []:
        end = max(end, float(scene.get("start", 0) or 0) + float(scene.get("duration", 0) or 0))
    return round(end, 3)


def project_has_captions(project: dict[str, Any]) -> bool:
    if project.get("captions"):
        return True
    for scene in project.get("timeline", []) or []:
        for layer in scene.get("layers", []) or []:
            if layer.get("type") in {"caption", "captions"}:
                return True
    return False


def _remove_caption_layers(project: dict[str, Any]) -> None:
    project.pop("captions", None)
    for scene in project.get("timeline", []) or []:
        scene["layers"] = [layer for layer in scene.get("layers", []) if layer.get("type") not in {"caption", "captions"}]


def _fit_duration(project: dict[str, Any], target: float) -> None:
    current = 0.0
    next_timeline = []
    for scene in project.get("timeline", []) or []:
        duration = float(scene.get("duration", 0) or 0)
        if current >= target:
            break
        copied = copy.deepcopy(scene)
        copied["start"] = round(current, 3)
        copied["duration"] = round(min(duration, max(0.5, target - current)), 3)
        next_timeline.append(copied)
        current += float(copied["duration"])
    project["timeline"] = next_timeline
    project.setdefault("project", {})["duration"] = round(current, 3)


def _extend_duration(project: dict[str, Any], target: float) -> None:
    timeline = project.get("timeline", []) or []
    if not timeline:
        return
    current = _project_duration(project)
    extra = max(0.0, target - current)
    timeline[-1]["duration"] = round(float(timeline[-1].get("duration", 0) or 0) + extra, 3)
    _retime_scenes(project)


def _retime_scenes(project: dict[str, Any]) -> None:
    start = 0.0
    for scene in project.get("timeline", []) or []:
        scene["start"] = round(start, 3)
        start += float(scene.get("duration", 0) or 0)
    project.setdefault("project", {})["duration"] = round(start, 3)


def _replace_first_text(project: dict[str, Any], text: str) -> None:
    for scene in project.get("timeline", []) or []:
        for layer in scene.get("layers", []) or []:
            if layer.get("type") == "text" and layer.get("text"):
                layer["text"] = text
                return


def _replace_last_text(project: dict[str, Any], text: str) -> None:
    for scene in reversed(project.get("timeline", []) or []):
        for layer in reversed(scene.get("layers", []) or []):
            if layer.get("type") == "text" and layer.get("text"):
                layer["text"] = text
                return


def _alternate_hook(project: dict[str, Any]) -> str:
    product = _product_name(project)
    return f"Stop missing what {product} can fix."


def _alternate_cta(project: dict[str, Any]) -> str:
    product = _product_name(project)
    return f"Try {product} and save the cleanest setup."


def _apply_caption_style_variant(project: dict[str, Any]) -> None:
    for scene in project.get("timeline", []) or []:
        for layer in scene.get("layers", []) or []:
            if layer.get("type") in {"text", "caption", "captions"}:
                layer["fontSize"] = min(76, max(44, int(float(layer.get("fontSize", 56) or 56))))
                layer["color"] = "#ffffff"
                layer["strokeColor"] = "#000000"
                layer["strokeWidth"] = max(3, int(float(layer.get("strokeWidth", 2) or 2)))
                layer["background"] = {"color": "#000000", "opacity": 0.42, "padding": 18}


def _pacing_profile(project: dict[str, Any]) -> dict[str, Any]:
    durations = [float(scene.get("duration", 0) or 0) for scene in project.get("timeline", []) or []]
    return {
        "sceneCount": len(durations),
        "averageSceneDuration": round(sum(durations) / max(len(durations), 1), 3),
        "shortestScene": round(min(durations), 3) if durations else 0,
        "longestScene": round(max(durations), 3) if durations else 0,
    }


def _caption_profile(project: dict[str, Any]) -> dict[str, Any]:
    layers = []
    for scene in project.get("timeline", []) or []:
        for layer in scene.get("layers", []) or []:
            if layer.get("type") in {"text", "caption", "captions"}:
                layers.append(layer)
    if not layers:
        return {"enabled": False}
    sample = layers[0]
    return {
        "enabled": True,
        "fontSize": sample.get("fontSize"),
        "fontFamily": sample.get("fontFamily"),
        "color": sample.get("color"),
        "strokeColor": sample.get("strokeColor"),
        "background": sample.get("background"),
    }


def _scene_summary(scene: Any) -> dict[str, Any] | None:
    if not isinstance(scene, dict):
        return None
    return {
        "id": scene.get("id"),
        "duration": scene.get("duration"),
        "layerTypes": [layer.get("type") for layer in scene.get("layers", [])],
        "transitionOut": scene.get("transitionOut"),
    }


def _transition_type(scene: dict[str, Any]) -> str | None:
    transition = scene.get("transitionOut") or {}
    return str(transition.get("type")) if transition.get("type") else None


def _product_name(project: dict[str, Any]) -> str:
    metadata = project.get("metadata", {})
    content = metadata.get("contentGenerator", {}) if isinstance(metadata, dict) else {}
    brief = content.get("contentBrief", {}) if isinstance(content, dict) else {}
    return str(brief.get("productName") or metadata.get("productName") or metadata.get("title") or "this product")


def _relocate_assets_for_output(data: dict[str, Any], source_project_path: Path, output_path: Path) -> None:
    if source_project_path.parent.resolve() == output_path.parent.resolve():
        return
    for key, value in list((data.get("assets", {}) or {}).items()):
        raw = Path(str(value))
        if not raw.is_absolute():
            data["assets"][key] = str((source_project_path.parent / raw).resolve())


def _dedupe_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    output = []
    for issue in issues:
        key = (issue["id"], issue["message"])
        if key not in seen:
            seen.add(key)
            output.append(issue)
    return output


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_") or "item"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
