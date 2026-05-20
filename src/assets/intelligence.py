from __future__ import annotations

import json
import re
import statistics
from pathlib import Path
from typing import Any

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
    if report["type"] in {"video", "audio"} and report["audioPresence"]:
        report["loudness"] = _audio_loudness(path)

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


def _audio_loudness(path: Path) -> dict[str, float] | None:
    try:
        analysis = analyze_audio(path)
    except Exception:
        return None
    return {
        "average": float(analysis.get("averageLoudness", 0) or 0),
        "peak": float(analysis.get("peakLoudness", 0) or 0),
    }


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
