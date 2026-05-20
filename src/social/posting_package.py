from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from content.thumbnails import generate_thumbnail_set
from quality.checker import run_quality_check
from utils.media import media_duration, run_ffmpeg


PLATFORM_PACKAGES: dict[str, dict[str, Any]] = {
    "youtube_shorts": {
        "label": "YouTube Shorts",
        "folder": "youtube_shorts",
        "expected": {"width": 1080, "height": 1920, "maxDuration": 60, "maxBytes": 256 * 1024 * 1024},
        "aspect": "vertical",
        "hashtags": ["#Shorts", "#Productivity", "#TechDemo"],
        "notes": "Upload as a Short. Keep the title direct and let captions carry the hook.",
    },
    "youtube_landscape": {
        "label": "YouTube Landscape",
        "folder": "youtube_landscape",
        "expected": {"width": 1920, "height": 1080, "maxDuration": 7200, "maxBytes": 128 * 1024 * 1024 * 1024},
        "aspect": "landscape",
        "hashtags": ["#YouTube", "#ProductDemo", "#CreatorTools"],
        "notes": "Use the description for chapter notes and keep the title searchable.",
    },
    "tiktok": {
        "label": "TikTok",
        "folder": "tiktok",
        "expected": {"width": 1080, "height": 1920, "maxDuration": 60, "maxBytes": 287 * 1024 * 1024},
        "aspect": "vertical",
        "hashtags": ["#TechTok", "#Automation", "#ProductDemo"],
        "notes": "Use the strongest hook as the first line of the caption.",
    },
    "instagram_reels": {
        "label": "Instagram Reels",
        "folder": "instagram_reels",
        "expected": {"width": 1080, "height": 1920, "maxDuration": 90, "maxBytes": 256 * 1024 * 1024},
        "aspect": "vertical",
        "hashtags": ["#Reels", "#CreatorTools", "#Tech"],
        "notes": "Use the thumbnail option with the clearest centered title.",
    },
    "discord": {
        "label": "Discord",
        "folder": "discord",
        "expected": {"width": 1280, "height": 720, "maxDuration": 600, "maxBytes": 25 * 1024 * 1024},
        "aspect": "landscape",
        "hashtags": [],
        "notes": "Use the compressed file-size checklist before posting to a server.",
    },
    "high_quality_archive": {
        "label": "High Quality Archive",
        "folder": "high_quality_archive",
        "expected": {"width": 3840, "height": 2160, "maxDuration": 14400, "maxBytes": 512 * 1024 * 1024 * 1024},
        "aspect": "landscape",
        "hashtags": [],
        "notes": "Keep this package as the local master archive, not the compressed social upload.",
    },
    "x_twitter": {
        "label": "X/Twitter",
        "folder": "x_twitter",
        "expected": {"width": 1920, "height": 1080, "maxDuration": 140, "maxBytes": 512 * 1024 * 1024},
        "aspect": "landscape",
        "hashtags": ["#BuildInPublic", "#AI", "#VideoEditing"],
        "notes": "Lead with the hook in the post text and keep the CTA short.",
    },
}

ALIASES = {
    "all": "all",
    "shorts": "youtube_shorts",
    "youtube": "youtube_landscape",
    "youtube_landscape": "youtube_landscape",
    "youtube_1080p": "youtube_landscape",
    "youtube_short": "youtube_shorts",
    "youtube_shorts": "youtube_shorts",
    "tiktok": "tiktok",
    "reels": "instagram_reels",
    "instagram": "instagram_reels",
    "instagram_reels": "instagram_reels",
    "discord": "discord",
    "discord_720p": "discord",
    "high_quality_archive": "high_quality_archive",
    "archive": "high_quality_archive",
    "twitter": "x_twitter",
    "x": "x_twitter",
    "x_twitter": "x_twitter",
}


def create_posting_package(
    project_path: Path,
    video_path: Path,
    *,
    output_dir: Path,
    platforms: list[str] | None = None,
    title: str | None = None,
    accent_color: str | None = None,
    render_report_path: Path | None = None,
    render_logs_path: Path | None = None,
) -> dict[str, Any]:
    project_path = project_path.resolve()
    video_path = video_path.resolve()
    output_dir = output_dir.resolve()
    if not project_path.exists():
        raise FileNotFoundError(f"Project JSON does not exist: {project_path}")
    if not video_path.exists():
        raise FileNotFoundError(f"Rendered video does not exist: {video_path}")
    project = json.loads(project_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)

    selected_platforms = _normalize_platforms(platforms or ["all"])
    video_info = inspect_video(video_path)
    captions = collect_caption_items(project)
    package_title = title or _primary_title(project)
    accent = accent_color or _accent_color(project)
    render_report = _read_optional_json(render_report_path or video_path.parent / "render_report.json")
    quality = build_quality_checklist(project_path, video_path, video_info=video_info)

    packages = []
    first_platform_metadata: dict[str, Any] | None = None
    first_thumbnails: dict[str, Any] | None = None
    first_captions: dict[str, str] | None = None
    for platform_key in selected_platforms:
        config = PLATFORM_PACKAGES[platform_key]
        package_dir = output_dir / config["folder"]
        package_dir.mkdir(parents=True, exist_ok=True)
        metadata = generate_platform_metadata(project, platform_key, title=package_title)
        captions_written = write_caption_exports(captions, package_dir)
        thumbnails = _write_thumbnails(video_path, package_dir, title=metadata["title"], accent_color=accent, aspect=config["aspect"])
        if first_platform_metadata is None:
            first_platform_metadata = metadata
            first_thumbnails = thumbnails
            first_captions = captions_written
        video_copy = package_dir / "final_video.mp4"
        shutil.copy2(video_path, video_copy)
        _write_text_metadata(package_dir, metadata)
        checklist = platform_quality_checklist(video_info, quality, platform_key)
        _write_json(package_dir / "quality_checklist.json", checklist)
        _write_json(package_dir / "render_report.json", render_report or _fallback_render_report(video_path, video_info))
        _write_json(
            package_dir / "package_manifest.json",
            {
                "platform": platform_key,
                "label": config["label"],
                "video": str(video_copy.resolve()),
                "thumbnail": thumbnails["primary"],
                "thumbnailOptions": thumbnails["options"],
                "captions": captions_written,
                "metadata": metadata,
                "qualityChecklist": checklist,
            },
        )
        packages.append(
            {
                "platform": platform_key,
                "folder": str(package_dir.resolve()),
                "video": str(video_copy.resolve()),
                "thumbnail": thumbnails["primary"],
                "ready": checklist["ready"],
                "warningCount": len(checklist["warnings"]),
            }
        )

    root_package = _write_root_upload_package(
        output_dir,
        project_path=project_path,
        video_path=video_path,
        metadata=first_platform_metadata or generate_platform_metadata(project, selected_platforms[0], title=package_title),
        thumbnail_path=Path(str((first_thumbnails or {}).get("primary"))) if first_thumbnails else None,
        captions=first_captions,
        render_report=render_report or _fallback_render_report(video_path, video_info),
        quality=quality,
        video_info=video_info,
        platform_packages=packages,
    )
    archive = _write_local_archive(
        output_dir,
        project_path=project_path,
        video_path=video_path,
        project=project,
        render_report=render_report,
        render_logs_path=render_logs_path,
        metadata={"title": package_title, "accentColor": accent, "platforms": selected_platforms},
    )
    summary = {
        "packageVersion": 1,
        "project": str(project_path),
        "video": str(video_path),
        "outputDir": str(output_dir),
        "platforms": packages,
        "videoInfo": video_info,
        "qualityChecklist": quality,
        "rootPackage": root_package,
        "archive": archive,
    }
    _write_json(output_dir / "posting_package_summary.json", summary)
    return summary


def generate_platform_metadata(project: dict[str, Any], platform: str, *, title: str | None = None) -> dict[str, Any]:
    config = PLATFORM_PACKAGES[platform]
    product = _product_name(project)
    hook = _hook(project, product)
    features = _features(project)
    primary_title = _fit_line(title or hook or product, 78)
    benefit = features[0] if features else "a cleaner workflow"
    title_options = [
        primary_title,
        _fit_line(f"{product}: {benefit}", 78),
        _fit_line(f"Stop guessing. Let {product} show the fix.", 78),
    ]
    cta = _cta_for_platform(platform, product)
    hashtags = _dedupe(config["hashtags"] + _feature_hashtags(features) + _style_hashtags(project))
    description = _description(platform, product, hook, features, cta)
    return {
        "platform": platform,
        "platformLabel": config["label"],
        "title": title_options[0],
        "titleOptions": title_options,
        "description": description,
        "hashtags": hashtags,
        "pinnedComment": _pinned_comment(platform, product),
        "cta": cta,
        "uploadNotes": config["notes"],
    }


def build_quality_checklist(project_path: Path, video_path: Path, *, video_info: dict[str, Any] | None = None) -> dict[str, Any]:
    video_info = video_info or inspect_video(video_path)
    project_quality = run_quality_check(project_path)
    checks = {
        "videoExists": video_path.exists(),
        "playableVideo": video_info.get("duration", 0) > 0 and video_info.get("width", 0) > 0,
        "durationSeconds": video_info.get("duration", 0),
        "resolution": {"width": video_info.get("width", 0), "height": video_info.get("height", 0)},
        "fps": video_info.get("fps", 0),
        "hasAudio": video_info.get("hasAudio", False),
        "audioLoudness": video_info.get("audioLoudness", {}),
        "fileSizeBytes": video_path.stat().st_size if video_path.exists() else 0,
        "captionIssueCount": sum(1 for issue in project_quality.get("issues", []) if "caption" in str(issue.get("message", "")).lower()),
        "safeZoneIssueCount": sum(1 for issue in project_quality.get("issues", []) if "safe zone" in str(issue.get("message", "")).lower()),
        "projectQualityPassed": project_quality.get("passed", False),
        "projectIssues": project_quality.get("issues", []),
    }
    warnings = []
    if not checks["playableVideo"]:
        warnings.append("Rendered video could not be inspected as playable.")
    if not checks["hasAudio"]:
        warnings.append("Final video has no detectable audio stream.")
    max_volume = checks["audioLoudness"].get("maxVolumeDb")
    if isinstance(max_volume, (int, float)) and max_volume > -0.5:
        warnings.append("Audio peak is close to clipping.")
    if checks["captionIssueCount"]:
        warnings.append("Caption timing may be hard to read.")
    if checks["safeZoneIssueCount"]:
        warnings.append("Text may be outside safe zones.")
    return {"ready": not warnings and bool(checks["projectQualityPassed"]), "checks": checks, "warnings": warnings}


def platform_quality_checklist(video_info: dict[str, Any], base_quality: dict[str, Any], platform: str) -> dict[str, Any]:
    config = PLATFORM_PACKAGES[platform]
    expected = config["expected"]
    file_size = video_info.get("fileSizeBytes", 0)
    warnings = list(base_quality.get("warnings", []))
    width = int(video_info.get("width", 0) or 0)
    height = int(video_info.get("height", 0) or 0)
    duration = float(video_info.get("duration", 0) or 0)
    if width and height and (width != expected["width"] or height != expected["height"]):
        warnings.append(f"{config['label']} prefers {expected['width']}x{expected['height']}; packaged video is {width}x{height}.")
    if duration > expected["maxDuration"]:
        warnings.append(f"{config['label']} duration target is {expected['maxDuration']}s; video is {round(duration, 2)}s.")
    if file_size > expected["maxBytes"]:
        warnings.append(f"{config['label']} package may be too large ({file_size} bytes).")
    return {
        "platform": platform,
        "ready": not any("could not" in warning.lower() for warning in warnings),
        "warnings": warnings,
        "checks": {
            "expectedResolution": {"width": expected["width"], "height": expected["height"]},
            "actualResolution": {"width": width, "height": height},
            "durationSeconds": duration,
            "fileSizeBytes": file_size,
            "hasAudio": video_info.get("hasAudio", False),
            "captionIssueCount": base_quality.get("checks", {}).get("captionIssueCount", 0),
        },
    }


def inspect_video(video_path: Path) -> dict[str, Any]:
    result = run_ffmpeg(["-hide_banner", "-i", str(video_path)])
    output = (result.stderr or "") + (result.stdout or "")
    duration = media_duration(video_path)
    video_match = re.search(r"Video:\s*[^,\n]+(?:,[^,\n]+)*,\s*(\d{2,5})x(\d{2,5})[^,\n]*(?:,\s*([\d.]+)\s*fps)?", output)
    if not video_match:
        video_match = re.search(r"(\d{2,5})x(\d{2,5}).*?([\d.]+)\s*fps", output)
    width = int(video_match.group(1)) if video_match else 0
    height = int(video_match.group(2)) if video_match else 0
    fps_match = re.search(r",\s*([\d.]+)\s*fps", output)
    fps = float(fps_match.group(1)) if fps_match else 0.0
    has_audio = "Audio:" in output
    loudness = _audio_loudness(video_path) if has_audio else {}
    return {
        "path": str(video_path.resolve()),
        "duration": round(duration, 3),
        "width": width,
        "height": height,
        "fps": fps,
        "hasAudio": has_audio,
        "audioLoudness": loudness,
        "fileSizeBytes": video_path.stat().st_size if video_path.exists() else 0,
    }


def collect_caption_items(project: dict[str, Any]) -> list[dict[str, Any]]:
    captions: list[dict[str, Any]] = []
    for item in project.get("captions", []) or []:
        if isinstance(item, dict) and item.get("text"):
            captions.append(_caption_item(item, base_start=0))
    for scene in project.get("timeline", []) or []:
        scene_start = float(scene.get("start", 0) or 0)
        for layer in scene.get("layers", []) or []:
            layer_start = scene_start + float(layer.get("start", 0) or 0)
            if layer.get("type") in {"caption", "captions"}:
                for item in layer.get("items", []) or []:
                    if isinstance(item, dict) and item.get("text"):
                        captions.append(_caption_item(item, base_start=layer_start))
            elif layer.get("type") == "text" and layer.get("text"):
                captions.append(
                    {
                        "start": layer_start,
                        "end": layer_start + float(layer.get("duration", scene.get("duration", 2)) or 2),
                        "text": str(layer.get("text", "")),
                    }
                )
    deduped = []
    seen = set()
    for item in sorted(captions, key=lambda value: (value["start"], value["text"])):
        marker = (round(item["start"], 2), round(item["end"], 2), item["text"])
        if marker not in seen:
            seen.add(marker)
            deduped.append(item)
    return deduped


def write_caption_exports(captions: list[dict[str, Any]], output_dir: Path) -> dict[str, str]:
    srt = output_dir / "captions.srt"
    vtt = output_dir / "captions.vtt"
    transcript = output_dir / "transcript.txt"
    srt.write_text(_srt(captions), encoding="utf-8")
    vtt.write_text(_vtt(captions), encoding="utf-8")
    transcript.write_text("\n".join(item["text"] for item in captions) + ("\n" if captions else ""), encoding="utf-8")
    (output_dir / "burned_in_captions.txt").write_text(
        "The packaged final_video.mp4 is copied from the rendered output. If the source render used caption layers, captions are already burned in.\n",
        encoding="utf-8",
    )
    return {"srt": str(srt.resolve()), "vtt": str(vtt.resolve()), "transcript": str(transcript.resolve())}


def _write_thumbnails(source_video: Path, package_dir: Path, *, title: str, accent_color: str, aspect: str) -> dict[str, Any]:
    thumbs_dir = package_dir / "thumbnail_options"
    report = generate_thumbnail_set(source_video, title=title, output_dir=thumbs_dir, accent_color=accent_color)
    options = [item for item in report["thumbnails"] if item["aspect"] == aspect][:3]
    if len(options) < 3:
        options = report["thumbnails"][:3]
    copied = []
    for index, item in enumerate(options, start=1):
        target = thumbs_dir / f"option_{index}.png"
        if Path(item["path"]).resolve() != target.resolve():
            shutil.copy2(item["path"], target)
        copied.append({"variant": index, "path": str(target.resolve()), "timestamp": item["timestamp"], "safeZoneValid": True})
    primary = package_dir / "thumbnail.png"
    if copied:
        shutil.copy2(copied[0]["path"], primary)
    return {"primary": str(primary.resolve()), "options": copied, "reportPath": report["reportPath"]}


def _write_text_metadata(package_dir: Path, metadata: dict[str, Any]) -> None:
    (package_dir / "title.txt").write_text(metadata["title"] + "\n", encoding="utf-8")
    (package_dir / "title_ideas.txt").write_text("\n".join(metadata["titleOptions"]) + "\n", encoding="utf-8")
    (package_dir / "description.txt").write_text(metadata["description"] + "\n", encoding="utf-8")
    (package_dir / "hashtags.txt").write_text(" ".join(metadata["hashtags"]) + "\n", encoding="utf-8")
    (package_dir / "pinned_comment.txt").write_text(metadata["pinnedComment"] + "\n", encoding="utf-8")
    (package_dir / "cta.txt").write_text(metadata["cta"] + "\n", encoding="utf-8")
    (package_dir / "upload_notes.txt").write_text(metadata["uploadNotes"] + "\n", encoding="utf-8")
    _write_json(package_dir / "metadata.json", metadata)


def _write_root_upload_package(
    output_dir: Path,
    *,
    project_path: Path,
    video_path: Path,
    metadata: dict[str, Any],
    thumbnail_path: Path | None,
    captions: dict[str, str] | None,
    render_report: dict[str, Any],
    quality: dict[str, Any],
    video_info: dict[str, Any],
    platform_packages: list[dict[str, Any]],
) -> dict[str, Any]:
    final_video = output_dir / "final_video.mp4"
    if video_path.resolve() != final_video.resolve():
        shutil.copy2(video_path, final_video)

    thumbnail = output_dir / "thumbnail.png"
    if thumbnail_path and thumbnail_path.exists():
        shutil.copy2(thumbnail_path, thumbnail)
    elif not thumbnail.exists():
        generated = _write_thumbnails(video_path, output_dir, title=metadata["title"], accent_color="#ef4444", aspect="vertical")
        thumbnail = Path(generated["primary"])

    caption_paths = _copy_or_create_caption_exports(captions, output_dir)
    _write_text_metadata(output_dir, metadata)
    shutil.copy2(project_path, output_dir / "project_backup.json")
    project = json.loads(project_path.read_text(encoding="utf-8"))
    _write_json(output_dir / "assets_used.json", {"assets": project.get("assets", {})})
    _write_json(output_dir / "render_report.json", render_report)
    _write_json(output_dir / "quality_checklist.json", quality)
    _write_json(output_dir / "version_history.json", _version_history(project))
    validation = _validate_export_package(output_dir, video_info=video_info, quality=quality)
    _write_json(output_dir / "export_validation.json", validation)
    manifest = {
        "folder": str(output_dir.resolve()),
        "video": str(final_video.resolve()),
        "thumbnail": str(thumbnail.resolve()),
        "captions": caption_paths,
        "metadata": metadata,
        "platformPackages": platform_packages,
        "validation": validation,
    }
    _write_json(output_dir / "package_manifest.json", manifest)
    return manifest


def _copy_or_create_caption_exports(captions: dict[str, str] | None, output_dir: Path) -> dict[str, str]:
    targets = {
        "srt": output_dir / "captions.srt",
        "vtt": output_dir / "captions.vtt",
        "transcript": output_dir / "transcript.txt",
    }
    for key, target in targets.items():
        source = Path(captions[key]) if captions and captions.get(key) else None
        if source and source.exists() and source.resolve() != target.resolve():
            shutil.copy2(source, target)
        elif not target.exists():
            if key == "vtt":
                target.write_text("WEBVTT\n\n", encoding="utf-8")
            else:
                target.write_text("", encoding="utf-8")
    return {key: str(path.resolve()) for key, path in targets.items()}


def _validate_export_package(output_dir: Path, *, video_info: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    required = {
        "finalVideo": output_dir / "final_video.mp4",
        "thumbnail": output_dir / "thumbnail.png",
        "captionsSrt": output_dir / "captions.srt",
        "captionsVtt": output_dir / "captions.vtt",
        "transcript": output_dir / "transcript.txt",
        "title": output_dir / "title.txt",
        "description": output_dir / "description.txt",
        "hashtags": output_dir / "hashtags.txt",
        "renderReport": output_dir / "render_report.json",
        "projectBackup": output_dir / "project_backup.json",
    }
    missing = [name for name, path in required.items() if not path.exists()]
    final_video = required["finalVideo"]
    checks = {
        "fileExists": final_video.exists(),
        "playableVideo": video_info.get("duration", 0) > 0 and video_info.get("width", 0) > 0,
        "correctDuration": video_info.get("duration", 0) > 0,
        "correctResolution": video_info.get("width", 0) > 0 and video_info.get("height", 0) > 0,
        "correctAudio": bool(video_info.get("hasAudio", False)),
        "captionsExported": required["captionsSrt"].exists() and required["captionsVtt"].exists(),
        "fileSizeAcceptable": final_video.exists() and final_video.stat().st_size < 512 * 1024 * 1024 * 1024,
        "requiredFilesPresent": not missing,
        "missingFiles": missing,
        "qualityReady": bool(quality.get("ready", False)),
    }
    warnings = list(quality.get("warnings", []))
    if missing:
        warnings.append(f"Upload package is missing required files: {', '.join(missing)}.")
    if not checks["correctAudio"]:
        warnings.append("Final video has no detectable audio stream.")
    if not checks["playableVideo"]:
        warnings.append("Final video could not be inspected as playable.")
    ready = checks["fileExists"] and checks["playableVideo"] and checks["requiredFilesPresent"] and checks["fileSizeAcceptable"]
    return {"ready": ready, "checks": checks, "warnings": _dedupe(warnings)}


def _write_local_archive(
    output_dir: Path,
    *,
    project_path: Path,
    video_path: Path,
    project: dict[str, Any],
    render_report: dict[str, Any] | None,
    render_logs_path: Path | None,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    archive_dir = output_dir / "local_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(project_path, archive_dir / "project_backup.json")
    shutil.copy2(video_path, archive_dir / "final_video.mp4")
    _write_json(archive_dir / "assets_used.json", {"assets": project.get("assets", {})})
    _write_json(archive_dir / "metadata.json", metadata)
    _write_json(archive_dir / "render_report.json", render_report or _fallback_render_report(video_path, inspect_video(video_path)))
    _write_json(archive_dir / "version_history.json", _version_history(project))
    if render_logs_path and render_logs_path.exists():
        shutil.copy2(render_logs_path, archive_dir / "render_logs.txt")
    else:
        (archive_dir / "render_logs.txt").write_text("No render log file was provided for this posting package.\n", encoding="utf-8")
    return {"folder": str(archive_dir.resolve())}


def _version_history(project: dict[str, Any]) -> dict[str, Any]:
    metadata = project.get("metadata", {}) if isinstance(project.get("metadata"), dict) else {}
    history = metadata.get("versionHistory") or project.get("versionHistory") or metadata.get("history") or []
    if not isinstance(history, list):
        history = [history]
    return {"versions": history}


def _caption_item(item: dict[str, Any], *, base_start: float) -> dict[str, Any]:
    start = base_start + float(item.get("start", 0) or 0)
    if item.get("end") is not None:
        end = base_start + float(item.get("end", start) or start)
    else:
        end = start + float(item.get("duration", 1.5) or 1.5)
    return {"start": round(start, 3), "end": round(max(end, start + 0.2), 3), "text": str(item.get("text", "")).strip()}


def _srt(captions: list[dict[str, Any]]) -> str:
    lines = []
    for index, item in enumerate(captions, start=1):
        lines.extend([str(index), f"{_stamp(item['start'], comma=True)} --> {_stamp(item['end'], comma=True)}", item["text"], ""])
    return "\n".join(lines)


def _vtt(captions: list[dict[str, Any]]) -> str:
    lines = ["WEBVTT", ""]
    for item in captions:
        lines.extend([f"{_stamp(item['start'])} --> {_stamp(item['end'])}", item["text"], ""])
    return "\n".join(lines)


def _stamp(seconds: float, *, comma: bool = False) -> str:
    milliseconds = int(round((seconds - int(seconds)) * 1000))
    total = int(seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    sep = "," if comma else "."
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{milliseconds:03d}"


def _audio_loudness(video_path: Path) -> dict[str, Any]:
    result = run_ffmpeg(["-hide_banner", "-i", str(video_path), "-af", "volumedetect", "-f", "null", "-"])
    output = (result.stderr or "") + (result.stdout or "")
    mean = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", output)
    max_volume = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", output)
    return {
        "meanVolumeDb": float(mean.group(1)) if mean else None,
        "maxVolumeDb": float(max_volume.group(1)) if max_volume else None,
    }


def _normalize_platforms(platforms: list[str]) -> list[str]:
    result = []
    for platform in platforms:
        key = ALIASES.get(platform.strip().lower().replace("-", "_").replace("/", "_"), platform)
        if key == "all":
            return list(PLATFORM_PACKAGES)
        if key not in PLATFORM_PACKAGES:
            raise ValueError(f"Unknown platform '{platform}'. Valid platforms: {', '.join(PLATFORM_PACKAGES)}")
        if key not in result:
            result.append(key)
    return result or list(PLATFORM_PACKAGES)


def _primary_title(project: dict[str, Any]) -> str:
    product = _product_name(project)
    hook = _hook(project, product)
    return _fit_line(hook or product, 78)


def _product_name(project: dict[str, Any]) -> str:
    content = project.get("metadata", {}).get("contentGenerator", {})
    brief = content.get("contentBrief", {}) if isinstance(content, dict) else {}
    return str(brief.get("productName") or project.get("metadata", {}).get("productName") or "Auto Video")


def _hook(project: dict[str, Any], product: str) -> str:
    content = project.get("metadata", {}).get("contentGenerator", {})
    script = content.get("script", {}) if isinstance(content, dict) else {}
    lines = script.get("lines", []) if isinstance(script, dict) else []
    if lines:
        return str(lines[0])
    for scene in project.get("timeline", []) or []:
        for layer in scene.get("layers", []) or []:
            if layer.get("type") in {"text", "caption"} and layer.get("text"):
                return str(layer["text"])
    return f"{product} in motion."


def _features(project: dict[str, Any]) -> list[str]:
    content = project.get("metadata", {}).get("contentGenerator", {})
    brief = content.get("contentBrief", {}) if isinstance(content, dict) else {}
    features = brief.get("bulletPoints", []) if isinstance(brief, dict) else []
    if features:
        return [str(item) for item in features[:5]]
    titles = []
    for scene in project.get("timeline", []) or []:
        for layer in scene.get("layers", []) or []:
            if layer.get("type") == "text" and layer.get("text"):
                titles.append(str(layer["text"]))
    return titles[:5]


def _accent_color(project: dict[str, Any]) -> str:
    style = project.get("metadata", {}).get("contentGenerator", {}).get("contentBrief", {}).get("theme", {})
    return str(style.get("accent") or "#ef4444")


def _description(platform: str, product: str, hook: str, features: list[str], cta: str) -> str:
    details = "\n".join(f"- {feature}" for feature in features[:4])
    return f"{hook}\n\n{product} highlights:\n{details}\n\n{cta}".strip()


def _cta_for_platform(platform: str, product: str) -> str:
    if platform == "discord":
        return f"Try {product} and share your result."
    if platform == "x_twitter":
        return f"Follow for more {product} build updates."
    return f"Save this and try {product}."


def _pinned_comment(platform: str, product: str) -> str:
    if platform == "youtube_shorts":
        return f"Want a deeper walkthrough of {product}? Comment what you want to see next."
    if platform == "tiktok":
        return f"Should I make a full demo of {product}?"
    return f"What should {product} show next?"


def _feature_hashtags(features: list[str]) -> list[str]:
    tags = []
    for feature in features[:3]:
        words = re.findall(r"[A-Za-z0-9]+", feature.title())
        if words:
            tags.append("#" + "".join(words[:3])[:24])
    return tags


def _style_hashtags(project: dict[str, Any]) -> list[str]:
    style = str(project.get("stylePreset") or project.get("metadata", {}).get("stylePreset") or "")
    if "red" in style or "cyber" in style:
        return ["#Cybersecurity", "#Windows"]
    if "gaming" in style:
        return ["#Gaming", "#Montage"]
    return ["#ContentCreation"]


def _dedupe(items: list[str]) -> list[str]:
    output = []
    for item in items:
        if item and item not in output:
            output.append(item)
    return output[:14]


def _fit_line(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _fallback_render_report(video_path: Path, video_info: dict[str, Any]) -> dict[str, Any]:
    return {
        "output": str(video_path.resolve()),
        "outputFileSize": video_path.stat().st_size if video_path.exists() else 0,
        "totalDuration": video_info.get("duration", 0),
        "resolution": {"width": video_info.get("width", 0), "height": video_info.get("height", 0), "fps": video_info.get("fps", 0)},
        "warnings": ["No renderer-generated render_report.json was found; this fallback was created during posting package export."],
    }


def _read_optional_json(path: Path | None) -> dict[str, Any] | None:
    if not path or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
