from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from utils.media import media_duration, run_ffmpeg


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".wmv", ".mpeg", ".mpg", ".m4v", ".ts", ".mts", ".m2ts"}


def understand_folder(folder: Path, *, output_path: Path | None = None) -> dict[str, Any]:
    clips = [understand_clip(path) for path in sorted(folder.rglob("*")) if path.suffix.lower() in VIDEO_EXTENSIONS and path.is_file()]
    clips.sort(key=lambda item: item["scores"]["highlightPotential"], reverse=True)
    report = {
        "folder": str(folder.resolve()),
        "clipCount": len(clips),
        "clips": clips,
        "topHighlights": clips[:10],
    }
    _write_optional(report, output_path)
    return report


def understand_clip(path: Path, *, output_path: Path | None = None) -> dict[str, Any]:
    path = path.resolve()
    frames = _sample_frames(path)
    duration = media_duration(path)
    metadata = _ffmpeg_metadata(path)
    if len(frames) < 2:
        report = {
            "path": str(path),
            "duration": duration,
            "metadata": metadata,
            "scores": {"highlightPotential": 0, "actionIntensity": 0, "readability": 0},
            "detections": {},
            "warnings": ["Not enough readable frames for visual understanding."],
        }
        _write_optional(report, output_path)
        return report

    brightness = [_average_brightness(frame) for frame in frames]
    diffs = [_frame_difference(a, b) for a, b in zip(frames, frames[1:])]
    centers = [_brightness_center(frame) for frame in frames]
    directions = [_direction(a, b) for a, b in zip(centers, centers[1:])]
    edge_scores = [_edge_density(frame) for frame in frames]
    skin_scores = [_skin_tone_ratio(frame) for frame in frames]

    scene_changes = _scene_change_times(diffs, duration)
    dark_ratio = sum(1 for value in brightness if value < 0.22) / len(brightness)
    light_ratio = sum(1 for value in brightness if value > 0.72) / len(brightness)
    action_intensity = sum(diffs) / len(diffs)
    max_motion = max(diffs)
    text_heavy_ratio = sum(1 for value in edge_scores if value > 0.18) / len(edge_scores)
    face_likelihood = max(skin_scores)
    highlight = min(1.0, action_intensity * 2.6 + max_motion * 1.4 + min(len(scene_changes), 6) * 0.035)
    readability = max(0.0, min(1.0, 1 - dark_ratio * 0.45 - text_heavy_ratio * 0.15))

    report = {
        "path": str(path),
        "duration": round(duration, 3),
        "metadata": metadata,
        "scores": {
            "highlightPotential": round(highlight, 3),
            "actionIntensity": round(action_intensity, 3),
            "maxMotion": round(max_motion, 3),
            "readability": round(readability, 3),
            "faceLikelihood": round(face_likelihood, 3),
        },
        "detections": {
            "sceneChanges": scene_changes,
            "darkSceneRatio": round(dark_ratio, 3),
            "lightSceneRatio": round(light_ratio, 3),
            "textHeavyRatio": round(text_heavy_ratio, 3),
            "dominantMotionDirection": _dominant_direction(directions),
            "possibleFaces": face_likelihood > 0.18,
            "actionIntensity": _energy_label(action_intensity),
        },
        "suggestedUse": _suggested_use(action_intensity, text_heavy_ratio, face_likelihood),
        "warnings": _warnings(metadata, dark_ratio, text_heavy_ratio, duration),
    }
    _write_optional(report, output_path)
    return report


def _sample_frames(path: Path, *, width: int = 64, height: int = 36, fps: int = 2, max_frames: int = 80) -> list[bytes]:
    result = run_ffmpeg(
        [
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-vf",
            f"fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-frames:v",
            str(max_frames),
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        capture_bytes=True,
    )
    if result.returncode != 0 or not result.stdout:
        return []
    frame_size = width * height * 3
    raw = result.stdout if isinstance(result.stdout, bytes) else bytes(result.stdout)
    return [raw[index : index + frame_size] for index in range(0, len(raw) - frame_size + 1, frame_size)]


def _ffmpeg_metadata(path: Path) -> dict[str, Any]:
    result = run_ffmpeg(["-hide_banner", "-i", str(path)])
    text = (result.stderr or "") + (result.stdout or "")
    codec = None
    resolution = None
    fps = None
    codec_match = re.search(r"Video:\s*([^,\s]+)", text)
    if codec_match:
        codec = codec_match.group(1)
    resolution_match = re.search(r"(\d{3,5})x(\d{3,5})", text)
    if resolution_match:
        resolution = {"width": int(resolution_match.group(1)), "height": int(resolution_match.group(2))}
    fps_match = re.search(r"(\d+(?:\.\d+)?)\s*fps", text)
    if fps_match:
        fps = float(fps_match.group(1))
    return {
        "codec": codec,
        "resolution": resolution,
        "fps": fps,
        "hasAudio": "Audio:" in text,
    }


def _average_brightness(frame: bytes) -> float:
    if not frame:
        return 0.0
    total = 0.0
    for index in range(0, len(frame), 3):
        total += (0.2126 * frame[index] + 0.7152 * frame[index + 1] + 0.0722 * frame[index + 2]) / 255
    return total / (len(frame) / 3)


def _frame_difference(a: bytes, b: bytes) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    return sum(abs(a[index] - b[index]) for index in range(length)) / (length * 255)


def _brightness_center(frame: bytes, width: int = 64, height: int = 36) -> tuple[float, float]:
    total = 0.0
    cx = 0.0
    cy = 0.0
    for y in range(height):
        for x in range(width):
            offset = (y * width + x) * 3
            value = (frame[offset] + frame[offset + 1] + frame[offset + 2]) / 765
            total += value
            cx += x * value
            cy += y * value
    if total <= 0:
        return 0.5, 0.5
    return cx / total / width, cy / total / height


def _direction(a: tuple[float, float], b: tuple[float, float]) -> str:
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    if abs(dx) < 0.01 and abs(dy) < 0.01:
        return "stable"
    if abs(dx) > abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


def _edge_density(frame: bytes, width: int = 64, height: int = 36) -> float:
    hits = 0
    total = 0
    for y in range(height - 1):
        for x in range(width - 1):
            offset = (y * width + x) * 3
            right = offset + 3
            below = offset + width * 3
            value = sum(frame[offset : offset + 3]) / 3
            diff = max(abs(value - sum(frame[right : right + 3]) / 3), abs(value - sum(frame[below : below + 3]) / 3))
            hits += 1 if diff > 42 else 0
            total += 1
    return hits / max(total, 1)


def _skin_tone_ratio(frame: bytes) -> float:
    hits = 0
    pixels = len(frame) // 3
    for index in range(0, len(frame), 3):
        r, g, b = frame[index], frame[index + 1], frame[index + 2]
        if r > 95 and g > 40 and b > 20 and r > g and r > b and abs(r - g) > 15:
            hits += 1
    return hits / max(pixels, 1)


def _scene_change_times(diffs: list[float], duration: float) -> list[dict[str, Any]]:
    if not diffs:
        return []
    mean = sum(diffs) / len(diffs)
    variance = sum((value - mean) ** 2 for value in diffs) / len(diffs)
    threshold = max(mean + math.sqrt(variance) * 1.5, 0.16)
    frame_gap = duration / max(len(diffs), 1)
    changes = []
    for index, diff in enumerate(diffs, start=1):
        if diff >= threshold:
            changes.append({"time": round(index * frame_gap, 3), "strength": round(diff, 3)})
    return changes[:30]


def _dominant_direction(directions: list[str]) -> str:
    if not directions:
        return "stable"
    return max(sorted(set(directions)), key=directions.count)


def _energy_label(value: float) -> str:
    if value >= 0.18:
        return "high"
    if value >= 0.08:
        return "medium"
    return "low"


def _suggested_use(action: float, text_heavy: float, face: float) -> str:
    if face > 0.18:
        return "reaction_or_facecam"
    if text_heavy > 0.35:
        return "tutorial_or_ui_detail"
    if action > 0.16:
        return "highlight_cut"
    return "supporting_broll"


def _warnings(metadata: dict[str, Any], dark_ratio: float, text_heavy: float, duration: float) -> list[str]:
    warnings: list[str] = []
    resolution = metadata.get("resolution") or {}
    if resolution and (resolution.get("width", 0) < 720 or resolution.get("height", 0) < 720):
        warnings.append("Low resolution source may need careful scaling.")
    if dark_ratio > 0.6:
        warnings.append("Clip is mostly dark; captions and overlays need extra contrast.")
    if text_heavy > 0.55:
        warnings.append("Clip appears text-heavy; avoid aggressive zooms that hurt readability.")
    if duration and duration < 1:
        warnings.append("Very short clip; use as a beat hit, not a full scene.")
    return warnings


def _write_optional(report: dict[str, Any], output_path: Path | None) -> None:
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
