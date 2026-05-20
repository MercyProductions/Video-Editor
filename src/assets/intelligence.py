from __future__ import annotations

import json
import re
import statistics
from pathlib import Path
from typing import Any

from intelligence.clip_understanding import understand_clip
from intelligence.beat_sync import analyze_audio
from media.compat import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, MEDIA_EXTENSIONS, VIDEO_EXTENSIONS, analyze_media
from utils.media import media_duration, run_ffmpeg


def analyze_asset_library(
    project_or_folder: Path,
    *,
    project_data: dict[str, Any] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    project_or_folder = project_or_folder.resolve()
    assets = _asset_paths(project_or_folder, project_data)
    reports = [analyze_asset(key, path) for key, path in assets.items()]
    result = {
        "source": str(project_or_folder),
        "assetCount": len(reports),
        "assets": reports,
        "smartCollections": _smart_collections(reports),
        "recommendations": _library_recommendations(reports),
        "searchIndex": _search_index(reports),
        "issues": [issue for report in reports for issue in report.get("issues", [])],
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")
    return result


def analyze_asset(key: str, path: Path) -> dict[str, Any]:
    path = path.resolve()
    report: dict[str, Any] = {
        "key": key,
        "path": str(path),
        "exists": path.exists(),
        "type": _media_type(path),
        "fileSize": path.stat().st_size if path.exists() else 0,
        "duration": 0.0,
        "resolution": None,
        "fps": None,
        "audioPresence": False,
        "loudness": None,
        "motionIntensity": None,
        "dominantColors": [],
        "codec": None,
        "smartTags": [],
        "smartDetections": {},
        "smartMoments": {},
        "recommendations": [],
        "searchText": "",
        "issues": [],
    }
    if not path.exists():
        report["issues"].append({"asset": key, "severity": "error", "message": "Asset file is missing."})
        return report

    if path.suffix.lower() not in MEDIA_EXTENSIONS:
        report["issues"].append({"asset": key, "severity": "warning", "message": "Unsupported or unknown media extension."})

    media_info = analyze_media(path)
    report.update(
        {
            "duration": media_info.get("duration", report["duration"]),
            "resolution": media_info.get("resolution"),
            "fps": media_info.get("fps"),
            "aspectRatio": media_info.get("aspectRatio"),
            "bitrate": media_info.get("bitrate"),
            "audioPresence": media_info.get("audioPresence", False),
            "audioTracks": media_info.get("audioTracks", []),
            "codec": media_info.get("codec"),
            "hdr": media_info.get("hdr", False),
            "sdr": media_info.get("sdr", True),
            "orientation": media_info.get("orientation", 0),
            "vfr": media_info.get("vfr", False),
            "mediaMetadata": media_info,
        }
    )
    if report["type"] in {"video", "audio"}:
        report["duration"] = round(media_duration(path), 3)
    if report["type"] in {"video", "image"}:
        report["dominantColors"] = _dominant_colors(path)
    if report["type"] == "video":
        report["motionIntensity"] = _motion_intensity(path)
    audio_analysis = None
    if report["type"] in {"video", "audio"} and report["audioPresence"]:
        audio_analysis = _audio_analysis(path)
        report["loudness"] = _audio_loudness_from_analysis(audio_analysis)

    clip_report = None
    if report["type"] == "video":
        clip_report = _clip_understanding(path)

    transcript = _sidecar_transcript(path)
    smart = _smart_asset_metadata(report, clip_report, audio_analysis, transcript)
    report.update(smart)

    if report["type"] == "video" and report["duration"] <= 0:
        report["issues"].append({"asset": key, "severity": "warning", "message": "Video duration could not be detected."})
    if report["type"] == "video" and not report["audioPresence"]:
        report["issues"].append({"asset": key, "severity": "info", "message": "Video has no audio stream."})
    if report["type"] == "video" and (report["motionIntensity"] or 0) < 0.006:
        report["issues"].append({"asset": key, "severity": "info", "message": "Low motion intensity; may be weak as highlight footage."})
    return report


def _asset_paths(project_or_folder: Path, project_data: dict[str, Any] | None) -> dict[str, Path]:
    if project_data:
        root = project_or_folder.parent if project_or_folder.is_file() else project_or_folder
        assets = project_data.get("assets", {})
        if isinstance(assets, dict):
            return {
                str(key): (Path(str(value)) if Path(str(value)).is_absolute() else root / str(value))
                for key, value in assets.items()
            }
    if project_or_folder.is_file():
        with project_or_folder.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return _asset_paths(project_or_folder, data)
    return {
        path.stem: path
        for path in project_or_folder.rglob("*")
        if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS
    }


def _media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    return "unknown"


def _ffmpeg_info(path: Path) -> dict[str, Any]:
    result = run_ffmpeg(["-hide_banner", "-i", str(path)])
    output = (result.stderr or "") + (result.stdout or "")
    video_match = re.search(r"Video:\s*([^,\r\n]+).*?(\d{2,5})x(\d{2,5}).*?(?:(\d+(?:\.\d+)?)\s*fps)?", output)
    audio_match = re.search(r"Audio:\s*([^,\r\n]+)", output)
    info: dict[str, Any] = {
        "audioPresence": audio_match is not None,
        "codec": None,
        "resolution": None,
        "fps": None,
    }
    if video_match:
        codec, width, height, fps = video_match.groups()
        info["codec"] = codec.strip()
        info["resolution"] = {"width": int(width), "height": int(height)}
        info["fps"] = float(fps) if fps else _parse_tbr(output)
    elif audio_match:
        info["codec"] = audio_match.group(1).strip()
    return info


def _parse_tbr(output: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*tbr", output)
    return float(match.group(1)) if match else None


def _audio_analysis(path: Path) -> dict[str, Any] | None:
    try:
        return analyze_audio(path)
    except Exception:
        return None


def _audio_loudness_from_analysis(analysis: dict[str, Any] | None) -> dict[str, float] | None:
    if not analysis:
        return None
    return {
        "average": float(analysis.get("averageLoudness", 0) or 0),
        "peak": float(analysis.get("peakLoudness", 0) or 0),
    }


def _clip_understanding(path: Path) -> dict[str, Any] | None:
    try:
        return understand_clip(path)
    except Exception:
        return None


def _sidecar_transcript(path: Path) -> dict[str, Any]:
    candidates = [path.with_suffix(ext) for ext in (".srt", ".vtt", ".txt")]
    for candidate in candidates:
        if not candidate.exists():
            continue
        text = candidate.read_text(encoding="utf-8", errors="ignore")
        words = _transcript_words(text)
        return {
            "path": str(candidate),
            "wordCount": len(words),
            "words": words[:500],
            "preview": " ".join(words[:40]),
        }
    return {"path": None, "wordCount": 0, "words": [], "preview": ""}


def _transcript_words(text: str) -> list[str]:
    cleaned = re.sub(r"\d{1,2}:\d{2}:\d{2}[,.]\d{1,3}\s*-->\s*\d{1,2}:\d{2}:\d{2}[,.]\d{1,3}", " ", text)
    cleaned = re.sub(r"WEBVTT|NOTE|STYLE|\{\\.*?\}|\d+\n", " ", cleaned, flags=re.IGNORECASE)
    return [word.lower() for word in re.findall(r"[a-zA-Z0-9']{2,}", cleaned)]


def _smart_asset_metadata(
    report: dict[str, Any],
    clip_report: dict[str, Any] | None,
    audio_analysis: dict[str, Any] | None,
    transcript: dict[str, Any],
) -> dict[str, Any]:
    tags: list[str] = []
    detections: dict[str, Any] = {}
    moments: dict[str, Any] = {}

    width = int((report.get("resolution") or {}).get("width") or 0) if isinstance(report.get("resolution"), dict) else 0
    height = int((report.get("resolution") or {}).get("height") or 0) if isinstance(report.get("resolution"), dict) else 0
    aspect = (width / height) if height else 0
    if width and height:
        if aspect < 0.9:
            tags.append("vertical_format")
            detections["format"] = "vertical"
        elif aspect > 1.25:
            tags.append("horizontal_format")
            detections["format"] = "horizontal"
        else:
            tags.append("square_format")
            detections["format"] = "square"

    clip_detections = clip_report.get("detections", {}) if clip_report else {}
    clip_scores = clip_report.get("scores", {}) if clip_report else {}
    face_confidence = float(clip_scores.get("faceLikelihood", 0) or 0)
    possible_faces = bool(clip_detections.get("possibleFaces")) or face_confidence >= 0.18
    if possible_faces:
        tags.append("faces_detected")
    detections["facesDetected"] = {"detected": possible_faces, "confidence": round(face_confidence, 3), "method": "visual_heuristic"}

    action_score = float(clip_scores.get("actionIntensity", report.get("motionIntensity") or 0) or 0)
    if action_score >= 0.12 or str(clip_detections.get("actionIntensity")) == "high":
        tags.append("action_high_motion")
    elif action_score >= 0.055:
        tags.append("medium_motion")
    else:
        tags.append("low_motion")
    detections["motion"] = {
        "score": round(action_score, 3),
        "label": str(clip_detections.get("actionIntensity") or _motion_label(action_score)),
        "direction": clip_detections.get("dominantMotionDirection", "unknown"),
    }

    dark_ratio = float(clip_detections.get("darkSceneRatio", 0) or 0)
    light_ratio = float(clip_detections.get("lightSceneRatio", 0) or 0)
    if dark_ratio >= 0.4:
        tags.append("dark_scenes")
    if light_ratio >= 0.35:
        tags.append("bright_scenes")
    detections["lighting"] = {"darkRatio": round(dark_ratio, 3), "lightRatio": round(light_ratio, 3), "guess": _lighting_label(dark_ratio, light_ratio)}

    indoor_outdoor = _indoor_outdoor_guess(report.get("dominantColors", []), light_ratio, dark_ratio)
    tags.append(f"{indoor_outdoor}_guess")
    detections["environmentGuess"] = indoor_outdoor

    quiet_sections = list((audio_analysis or {}).get("quietSections", []) or [])
    loud_peaks = list((audio_analysis or {}).get("loudnessPeaks", []) or [])
    bass_drops = list((audio_analysis or {}).get("bassDrops", []) or [])
    speech_detected = bool(transcript.get("wordCount")) or _speech_likelihood(audio_analysis, report)
    if speech_detected:
        tags.append("speech_detected")
    if quiet_sections:
        tags.append("silent_moments")
    if loud_peaks:
        tags.append("loud_moments")
    detections["speechDetected"] = {
        "detected": speech_detected,
        "confidence": 0.94 if transcript.get("wordCount") else (0.52 if speech_detected else 0.18),
        "transcriptPath": transcript.get("path"),
    }
    detections["audio"] = {
        "loudPeakCount": len(loud_peaks),
        "quietSectionCount": len(quiet_sections),
        "bassDropCount": len(bass_drops),
    }
    moments["loudMoments"] = loud_peaks[:12]
    moments["silentMoments"] = quiet_sections[:12]
    moments["sceneChanges"] = list(clip_detections.get("sceneChanges", []) or [])[:12]

    name_text = f"{report.get('key', '')} {Path(str(report.get('path', ''))).name}".lower()
    gaming = bool(re.search(r"\b(game|gameplay|kill|match|clip|obs|steam|xbox|playstation)\b", name_text)) or (action_score >= 0.14 and report.get("type") == "video" and not speech_detected)
    if gaming:
        tags.append("gaming_footage")
    meme_reaction = bool(re.search(r"\b(meme|reaction|funny|lol|fail|rage)\b", name_text)) or (possible_faces and len(loud_peaks) >= 2)
    if meme_reaction:
        tags.append("meme_reaction_potential")
    detections["gamingFootage"] = gaming
    detections["memeReactionPotential"] = meme_reaction

    highlight_score = _highlight_score(action_score, loud_peaks, possible_faces, clip_detections)
    hook_score = _hook_score(highlight_score, speech_detected, possible_faces, dark_ratio, report)
    detections["scores"] = {"highlight": highlight_score, "hook": hook_score, "readability": clip_scores.get("readability", None)}
    moments["highlightCandidates"] = _highlight_candidates(clip_report, audio_analysis, highlight_score)

    unique_tags = sorted(set(tags))
    recommendations = _asset_recommendations(report, unique_tags, detections, moments)
    search_words = " ".join(str(word) for word in transcript.get("words", [])[:180])
    search_text = " ".join(
        [
            str(report.get("key", "")),
            Path(str(report.get("path", ""))).name,
            " ".join(unique_tags),
            str(detections.get("environmentGuess", "")),
            search_words,
        ]
    ).lower()
    return {
        "smartTags": unique_tags,
        "smartDetections": detections,
        "smartMoments": moments,
        "recommendations": recommendations,
        "transcript": transcript,
        "searchText": search_text,
    }


def _motion_label(value: float) -> str:
    if value >= 0.12:
        return "high"
    if value >= 0.055:
        return "medium"
    return "low"


def _lighting_label(dark_ratio: float, light_ratio: float) -> str:
    if dark_ratio >= 0.4:
        return "dark"
    if light_ratio >= 0.35:
        return "bright"
    return "balanced"


def _speech_likelihood(audio_analysis: dict[str, Any] | None, report: dict[str, Any]) -> bool:
    if not audio_analysis or not report.get("audioPresence"):
        return False
    average = float(audio_analysis.get("averageLoudness", 0) or 0)
    peak = float(audio_analysis.get("peakLoudness", 0) or 0)
    quiet_duration = sum(float(section.get("duration", 0) or 0) for section in audio_analysis.get("quietSections", []) or [])
    duration = float(report.get("duration", 0) or audio_analysis.get("duration", 0) or 0)
    audible_ratio = 1 - quiet_duration / max(duration, 0.001)
    return average >= 0.006 and peak >= 0.025 and audible_ratio >= 0.25


def _indoor_outdoor_guess(colors: Any, light_ratio: float, dark_ratio: float) -> str:
    parsed = [_hex_to_rgb(str(color)) for color in colors if isinstance(color, str)]
    green_blue = sum(1 for rgb in parsed if rgb and (rgb[1] > rgb[0] * 1.08 or rgb[2] > rgb[0] * 1.12))
    if light_ratio > 0.35 and green_blue >= 2:
        return "outdoor"
    if dark_ratio > 0.25 or parsed:
        return "indoor"
    return "unknown_environment"


def _hex_to_rgb(color: str) -> tuple[int, int, int] | None:
    match = re.match(r"#?([0-9a-fA-F]{6})$", color)
    if not match:
        return None
    value = match.group(1)
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _highlight_score(action_score: float, loud_peaks: list[Any], possible_faces: bool, clip_detections: dict[str, Any]) -> float:
    scene_changes = len(clip_detections.get("sceneChanges", []) or [])
    score = action_score * 2.4 + min(len(loud_peaks), 8) * 0.035 + min(scene_changes, 8) * 0.025 + (0.12 if possible_faces else 0)
    return round(max(0.0, min(1.0, score)), 3)


def _hook_score(highlight_score: float, speech_detected: bool, possible_faces: bool, dark_ratio: float, report: dict[str, Any]) -> float:
    duration = float(report.get("duration", 0) or 0)
    score = highlight_score + (0.16 if speech_detected else 0) + (0.1 if possible_faces else 0) - (0.12 if dark_ratio > 0.55 else 0)
    if 2.0 <= duration <= 45:
        score += 0.08
    return round(max(0.0, min(1.0, score)), 3)


def _highlight_candidates(clip_report: dict[str, Any] | None, audio_analysis: dict[str, Any] | None, highlight_score: float) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in (audio_analysis or {}).get("loudnessPeaks", []) or []:
        time = float(item.get("time", 0) or 0)
        candidates.append({"start": round(max(0, time - 1.0), 3), "end": round(time + 1.4, 3), "reason": "loud_moment", "score": float(item.get("loudness", highlight_score) or highlight_score)})
    for item in (clip_report or {}).get("detections", {}).get("sceneChanges", []) or []:
        time = float(item.get("time", 0) or 0)
        candidates.append({"start": round(max(0, time - 0.6), 3), "end": round(time + 1.2, 3), "reason": "scene_change", "score": float(item.get("strength", highlight_score) or highlight_score)})
    if not candidates and highlight_score > 0.35:
        candidates.append({"start": 0, "end": 3, "reason": "strong_clip", "score": highlight_score})
    return sorted(candidates, key=lambda item: float(item.get("score", 0)), reverse=True)[:8]


def _asset_recommendations(report: dict[str, Any], tags: list[str], detections: dict[str, Any], moments: dict[str, Any]) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    scores = detections.get("scores", {})
    hook = float(scores.get("hook", 0) or 0)
    highlight = float(scores.get("highlight", 0) or 0)
    if hook >= 0.5:
        recommendations.append({"type": "hook", "message": "This clip may work well as a hook.", "confidence": hook, "requiresApproval": True})
    if highlight >= 0.45:
        recommendations.append({"type": "highlight", "message": "This scene has high energy.", "confidence": highlight, "requiresApproval": True})
    if "silent_moments" in tags:
        count = len(moments.get("silentMoments", []) or [])
        recommendations.append({"type": "silence", "message": f"Detected {count} silent/dead section(s). Remove or speed up?", "confidence": 0.72, "requiresApproval": True})
    if "meme_reaction_potential" in tags:
        recommendations.append({"type": "viral", "message": "Potential meme/reaction moment detected.", "confidence": 0.62, "requiresApproval": True})
    if "faces_detected" in tags and detections.get("speechDetected", {}).get("detected"):
        recommendations.append({"type": "dialogue", "message": "Face and speech cues suggest this can carry dialogue or commentary.", "confidence": 0.68, "requiresApproval": True})
    if report.get("type") == "video" and "low_motion" in tags:
        recommendations.append({"type": "dead_space", "message": "Low motion detected; review before using as a highlight.", "confidence": 0.55, "requiresApproval": True})
    return recommendations


def _smart_collections(reports: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    collections: dict[str, list[dict[str, Any]]] = {
        "Highlights": [],
        "Funny moments": [],
        "Action scenes": [],
        "Dialogue scenes": [],
        "Good intro candidates": [],
        "Good hook candidates": [],
        "Silent/dead sections": [],
    }
    for report in reports:
        tags = set(report.get("smartTags", []) or [])
        detections = report.get("smartDetections", {}) or {}
        scores = detections.get("scores", {}) if isinstance(detections, dict) else {}
        moments = report.get("smartMoments", {}) or {}
        item = _collection_item(report)
        if float(scores.get("highlight", 0) or 0) >= 0.45:
            collections["Highlights"].append({**item, "reason": "high highlight score"})
        if "meme_reaction_potential" in tags:
            collections["Funny moments"].append({**item, "reason": "reaction/meme cues"})
        if "action_high_motion" in tags:
            collections["Action scenes"].append({**item, "reason": "high motion"})
        if "speech_detected" in tags:
            collections["Dialogue scenes"].append({**item, "reason": "speech or transcript detected"})
        if float(scores.get("hook", 0) or 0) >= 0.5:
            collections["Good hook candidates"].append({**item, "reason": "strong hook score"})
        if report.get("type") in {"video", "image"} and "dark_scenes" not in tags and float(scores.get("highlight", 0) or 0) < 0.75:
            collections["Good intro candidates"].append({**item, "reason": "readable visual candidate"})
        if moments.get("silentMoments") or (report.get("type") == "video" and "low_motion" in tags):
            collections["Silent/dead sections"].append({**item, "reason": "silence or low motion"})
    for key, items in collections.items():
        collections[key] = sorted(items, key=lambda value: float(value.get("score", 0)), reverse=True)[:20]
    return collections


def _collection_item(report: dict[str, Any]) -> dict[str, Any]:
    scores = (report.get("smartDetections", {}) or {}).get("scores", {}) if isinstance(report.get("smartDetections"), dict) else {}
    return {
        "key": report.get("key"),
        "path": report.get("path"),
        "type": report.get("type"),
        "score": scores.get("hook") or scores.get("highlight") or 0,
        "tags": report.get("smartTags", []),
        "moments": report.get("smartMoments", {}).get("highlightCandidates", [])[:3] if isinstance(report.get("smartMoments"), dict) else [],
    }


def _library_recommendations(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for report in reports:
        for recommendation in report.get("recommendations", []) or []:
            rows.append({"asset": report.get("key"), "path": report.get("path"), **recommendation})
    return sorted(rows, key=lambda item: float(item.get("confidence", 0)), reverse=True)[:30]


def _search_index(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for report in reports:
        detections = report.get("smartDetections", {}) or {}
        rows.append(
            {
                "key": report.get("key"),
                "path": report.get("path"),
                "type": report.get("type"),
                "tags": report.get("smartTags", []),
                "words": (report.get("transcript", {}) or {}).get("words", [])[:80] if isinstance(report.get("transcript"), dict) else [],
                "activity": (detections.get("motion", {}) or {}).get("label") if isinstance(detections, dict) else None,
                "emotion": "reaction" if "meme_reaction_potential" in (report.get("smartTags", []) or []) else "neutral",
                "searchText": report.get("searchText", ""),
            }
        )
    return rows


def _motion_intensity(path: Path) -> float:
    width = 64
    height = 36
    fps = 2
    result = run_ffmpeg(
        [
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-vf",
            f"fps={fps},scale={width}:{height},format=gray",
            "-an",
            "-f",
            "rawvideo",
            "-",
        ],
        capture_bytes=True,
    )
    if result.returncode != 0 or not result.stdout:
        return 0.0
    raw = result.stdout
    frame_size = width * height
    previous: bytes | None = None
    samples: list[float] = []
    for index in range(0, len(raw), frame_size):
        frame = raw[index : index + frame_size]
        if len(frame) != frame_size:
            continue
        if previous is not None:
            samples.append(sum(abs(a - b) for a, b in zip(frame, previous)) / (frame_size * 255))
        previous = frame
    return round(float(statistics.mean(samples)), 5) if samples else 0.0


def _dominant_colors(path: Path) -> list[str]:
    result = run_ffmpeg(
        [
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            "scale=16:16,format=rgb24",
            "-f",
            "rawvideo",
            "-",
        ],
        capture_bytes=True,
    )
    if result.returncode != 0 or not result.stdout:
        return []
    buckets: dict[tuple[int, int, int], int] = {}
    raw = result.stdout
    for index in range(0, len(raw) - 2, 3):
        rgb = tuple((raw[index + offset] // 32) * 32 for offset in range(3))
        buckets[rgb] = buckets.get(rgb, 0) + 1
    colors = sorted(buckets.items(), key=lambda item: item[1], reverse=True)[:5]
    return [f"#{r:02x}{g:02x}{b:02x}" for (r, g, b), _count in colors]
