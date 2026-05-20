from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from utils.media import ffmpeg_binary, media_duration, run_ffmpeg


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".wmv", ".mpeg", ".mpg", ".m4v", ".ts", ".mts", ".m2ts"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff", ".tif", ".svg"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a"}
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS | AUDIO_EXTENSIONS

SUPPORTED_VIDEO_CODECS = {"h264", "hevc", "h265", "av1", "vp8", "vp9", "prores", "dnxhd", "mjpeg", "mpeg2video", "mpeg4", "wmv3", "theora"}
SUPPORTED_AUDIO_CODECS = {"mp3", "aac", "pcm_s16le", "pcm_s24le", "flac", "vorbis", "opus", "alac"}
SUPPORTED_IMAGE_CODECS = {"png", "mjpeg", "jpeg", "jpg", "webp", "bmp", "gif", "tiff", "tif", "svg"}
AUTO_TRANSCODE_VIDEO_EXTENSIONS = {".avi", ".flv", ".wmv", ".mpeg", ".mpg", ".ts", ".mts", ".m2ts"}

EXPORT_FORMATS: dict[str, dict[str, Any]] = {
    "mp4": {"extensions": [".mp4"], "videoCodec": "h264", "audioCodec": "aac", "supportsAudio": True},
    "mov": {"extensions": [".mov"], "videoCodec": "h264", "audioCodec": "aac", "supportsAudio": True},
    "mkv": {"extensions": [".mkv"], "videoCodec": "h264", "audioCodec": "aac", "supportsAudio": True},
    "webm": {"extensions": [".webm"], "videoCodec": "vp9", "audioCodec": "opus", "supportsAudio": True},
    "gif": {"extensions": [".gif"], "videoCodec": "gif", "audioCodec": None, "supportsAudio": False},
    "image_sequence": {"extensions": [".png", ".jpg", ".jpeg", ".webp"], "videoCodec": "image_sequence", "audioCodec": None, "supportsAudio": False},
}


def media_type_from_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    return "unknown"


def is_supported_media_path(path: Path) -> bool:
    return path.suffix.lower() in MEDIA_EXTENSIONS


def ffprobe_binary() -> str | None:
    system = shutil.which("ffprobe")
    if system:
        return system
    binary = Path(ffmpeg_binary())
    candidate = binary.with_name("ffprobe.exe" if binary.suffix.lower() == ".exe" else "ffprobe")
    if candidate.exists():
        return str(candidate)
    return None


def available_hwaccels() -> list[str]:
    result = run_ffmpeg(["-hide_banner", "-hwaccels"])
    output = (result.stdout or "") + (result.stderr or "")
    lines = [line.strip() for line in output.splitlines()]
    return [line for line in lines if line and not line.lower().startswith(("hardware", "ffmpeg"))]


def analyze_media(path: Path) -> dict[str, Any]:
    path = path.resolve()
    suffix = path.suffix.lower()
    base: dict[str, Any] = {
        "path": str(path),
        "fileName": path.name,
        "extension": suffix,
        "type": media_type_from_path(path),
        "exists": path.exists(),
        "fileSize": path.stat().st_size if path.exists() else 0,
        "supportedExtension": suffix in MEDIA_EXTENSIONS,
        "broken": False,
        "decodeSupported": False,
        "duration": 0.0,
        "bitrate": None,
        "codec": None,
        "codecLongName": None,
        "resolution": None,
        "fps": None,
        "aspectRatio": None,
        "audioTracks": [],
        "audioPresence": False,
        "sampleRate": None,
        "channels": None,
        "hdr": False,
        "sdr": True,
        "colorSpace": None,
        "colorTransfer": None,
        "colorPrimaries": None,
        "orientation": 0,
        "vfr": False,
        "pixelFormat": None,
        "container": None,
        "hardwareDecodeAvailable": bool(available_hwaccels()),
        "issues": [],
    }
    if not path.exists():
        base["broken"] = True
        base["issues"].append({"severity": "error", "message": "File does not exist."})
        return base
    if suffix not in MEDIA_EXTENSIONS:
        base["issues"].append({"severity": "warning", "message": "Extension is not in the supported import list."})

    probe = _ffprobe_json(path)
    if probe:
        _apply_probe_json(base, probe)
    else:
        _apply_ffmpeg_fallback(base, path)

    base["duration"] = round(float(base.get("duration") or media_duration(path) or 0), 3)
    base["audioPresence"] = bool(base["audioTracks"])
    if base["audioTracks"]:
        first_audio = base["audioTracks"][0]
        base["sampleRate"] = first_audio.get("sampleRate")
        base["channels"] = first_audio.get("channels")

    codec = str(base.get("codec") or "").lower()
    if base["type"] == "video":
        base["decodeSupported"] = codec in SUPPORTED_VIDEO_CODECS or bool(codec)
    elif base["type"] == "audio":
        audio_codec = str((base["audioTracks"][0] or {}).get("codec") if base["audioTracks"] else base.get("codec") or "").lower()
        base["decodeSupported"] = audio_codec in SUPPORTED_AUDIO_CODECS or bool(audio_codec)
    elif base["type"] == "image":
        base["decodeSupported"] = codec in SUPPORTED_IMAGE_CODECS or suffix in IMAGE_EXTENSIONS
    else:
        base["decodeSupported"] = False

    if not base["decodeSupported"]:
        base["issues"].append({"severity": "warning", "message": "Codec support could not be confirmed; normalization is recommended."})
    if base["type"] == "video" and base["vfr"]:
        base["issues"].append({"severity": "info", "message": "Variable frame rate detected; import normalization will convert to constant FPS."})
    if base["type"] in {"video", "audio"} and base["audioPresence"] and base["sampleRate"] not in {None, 48000}:
        base["issues"].append({"severity": "info", "message": "Audio sample rate will be normalized to 48 kHz for editing."})
    if base["hdr"]:
        base["issues"].append({"severity": "info", "message": "HDR source detected; current renderer exports Rec.709 SDR unless color pipeline is applied."})
    if base["duration"] <= 0 and base["type"] in {"video", "audio"}:
        base["broken"] = True
        base["issues"].append({"severity": "error", "message": "Duration could not be detected."})
    return base


def import_media_files(
    files: list[Path],
    *,
    project_dir: Path,
    normalize: str = "auto",
    generate_proxy: bool = True,
    generate_thumbnail: bool = True,
    generate_waveform: bool = True,
    target_fps: int = 30,
    sample_rate: int = 48000,
    output_path: Path | None = None,
) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    assets_dir = project_dir / "assets"
    media_dir = project_dir / ".ave_media"
    assets_dir.mkdir(parents=True, exist_ok=True)
    media_dir.mkdir(parents=True, exist_ok=True)
    imported: list[dict[str, Any]] = []
    warnings: list[str] = []
    for source in files:
        row = _import_one(
            source.resolve(),
            project_dir=project_dir,
            assets_dir=assets_dir,
            media_dir=media_dir,
            normalize=normalize,
            generate_proxy=generate_proxy,
            generate_thumbnail=generate_thumbnail,
            generate_waveform=generate_waveform,
            target_fps=target_fps,
            sample_rate=sample_rate,
        )
        imported.append(row)
        warnings.extend(row.get("warnings", []))
    report = {
        "format": "automatic-video-editor-media-import-report",
        "projectDir": str(project_dir),
        "normalize": normalize,
        "targetFps": target_fps,
        "sampleRate": sample_rate,
        "hardwareAcceleration": available_hwaccels(),
        "imported": imported,
        "warnings": warnings,
    }
    report_path = output_path or (media_dir / "media_import_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["reportPath"] = str(report_path.resolve())
    return report


def export_format_from_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if "%" in path.name and suffix in EXPORT_FORMATS["image_sequence"]["extensions"]:
        return "image_sequence"
    for key, config in EXPORT_FORMATS.items():
        if suffix in config["extensions"]:
            return key
    return "mp4"


def should_normalize(metadata: dict[str, Any], normalize: str) -> bool:
    mode = normalize.strip().lower()
    if mode in {"never", "false", "no", "off"}:
        return False
    if mode in {"always", "true", "yes", "on"}:
        return True
    suffix = str(metadata.get("extension") or "").lower()
    media_type = str(metadata.get("type") or "")
    if metadata.get("broken"):
        return False
    if not metadata.get("decodeSupported"):
        return True
    if media_type == "video":
        return bool(metadata.get("vfr")) or suffix in AUTO_TRANSCODE_VIDEO_EXTENSIONS
    if media_type == "audio":
        return metadata.get("sampleRate") not in {None, 48000}
    if media_type == "image":
        return suffix in {".svg", ".tiff", ".tif", ".bmp"}
    return False


def _import_one(
    source: Path,
    *,
    project_dir: Path,
    assets_dir: Path,
    media_dir: Path,
    normalize: str,
    generate_proxy: bool,
    generate_thumbnail: bool,
    generate_waveform: bool,
    target_fps: int,
    sample_rate: int,
) -> dict[str, Any]:
    warnings: list[str] = []
    original_target = _unique_path(assets_dir / source.name)
    if not source.exists():
        metadata = analyze_media(source)
        return {
            "source": str(source),
            "assetKey": _safe_asset_key(source.stem),
            "projectPath": None,
            "type": metadata["type"],
            "metadata": metadata,
            "warnings": ["Source file does not exist."],
            "error": "missing",
        }
    if source.resolve() != original_target.resolve():
        shutil.copy2(source, original_target)

    metadata = analyze_media(original_target)
    media_type = _project_media_type(metadata)
    active_path = original_target
    normalized_path: Path | None = None
    normalized = False
    if should_normalize(metadata, normalize):
        try:
            normalized_path = _normalize_media(original_target, metadata, media_dir / "normalized", target_fps=target_fps, sample_rate=sample_rate)
            active_path = normalized_path
            metadata = analyze_media(active_path)
            media_type = _project_media_type(metadata)
            normalized = True
        except Exception as exc:
            warnings.append(f"Normalization failed for {source.name}: {exc}")

    thumbnail_path: Path | None = None
    waveform_path: Path | None = None
    proxy_path: Path | None = None
    if generate_thumbnail and media_type in {"video", "image"}:
        try:
            thumbnail_path = _thumbnail(active_path, media_dir / "thumbnails")
        except Exception as exc:
            warnings.append(f"Thumbnail generation failed for {source.name}: {exc}")
    if generate_waveform and (media_type == "audio" or metadata.get("audioPresence")):
        try:
            waveform_path = _waveform(active_path, media_dir / "waveforms")
        except Exception as exc:
            warnings.append(f"Waveform generation failed for {source.name}: {exc}")
    if generate_proxy and media_type == "video":
        try:
            proxy_path = _proxy_video(active_path, media_dir / "proxies", target_fps=min(target_fps, 30))
        except Exception as exc:
            warnings.append(f"Proxy generation failed for {source.name}: {exc}")

    return {
        "source": str(source),
        "assetKey": _safe_asset_key(active_path.stem),
        "originalPath": str(original_target.resolve()),
        "normalized": normalized,
        "normalizedPath": str(normalized_path.resolve()) if normalized_path else None,
        "activePath": str(active_path.resolve()),
        "projectPath": _relative(project_dir, active_path),
        "type": media_type,
        "metadata": metadata,
        "thumbnailPath": str(thumbnail_path.resolve()) if thumbnail_path else None,
        "waveformPath": str(waveform_path.resolve()) if waveform_path else None,
        "proxyPath": str(proxy_path.resolve()) if proxy_path else None,
        "hash": _hash_file(active_path),
        "warnings": [*warnings, *[str(issue.get("message")) for issue in metadata.get("issues", []) if issue.get("severity") == "warning"]],
    }


def _project_media_type(metadata: dict[str, Any]) -> str:
    suffix = str(metadata.get("extension") or "").lower()
    if suffix == ".gif" and float(metadata.get("duration") or 0) > 0.2:
        return "video"
    return str(metadata.get("type") or "unknown")


def _ffprobe_json(path: Path) -> dict[str, Any] | None:
    binary = ffprobe_binary()
    if not binary:
        return None
    result = subprocess.run(
        [
            binary,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-print_format",
            "json",
            str(path),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _apply_probe_json(target: dict[str, Any], probe: dict[str, Any]) -> None:
    fmt = probe.get("format") or {}
    streams = probe.get("streams") or []
    target["container"] = fmt.get("format_name")
    target["duration"] = _float_or_none(fmt.get("duration")) or target["duration"]
    target["bitrate"] = _int_or_none(fmt.get("bit_rate"))
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if video_stream:
        width = _int_or_none(video_stream.get("width"))
        height = _int_or_none(video_stream.get("height"))
        target["codec"] = _codec_name(video_stream)
        target["codecLongName"] = video_stream.get("codec_long_name")
        if width and height:
            target["resolution"] = {"width": width, "height": height}
            target["aspectRatio"] = _aspect_ratio(width, height)
        target["fps"] = _rate(video_stream.get("avg_frame_rate")) or _rate(video_stream.get("r_frame_rate"))
        target["vfr"] = _is_vfr(video_stream)
        target["pixelFormat"] = video_stream.get("pix_fmt")
        target["colorSpace"] = video_stream.get("color_space")
        target["colorTransfer"] = video_stream.get("color_transfer")
        target["colorPrimaries"] = video_stream.get("color_primaries")
        target["orientation"] = _rotation(video_stream)
        target["hdr"] = _is_hdr(video_stream)
        target["sdr"] = not target["hdr"]
    elif target["type"] == "image":
        image_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
        if image_stream:
            width = _int_or_none(image_stream.get("width"))
            height = _int_or_none(image_stream.get("height"))
            target["codec"] = _codec_name(image_stream)
            if width and height:
                target["resolution"] = {"width": width, "height": height}
                target["aspectRatio"] = _aspect_ratio(width, height)
    target["audioTracks"] = [
        {
            "index": stream.get("index"),
            "codec": _codec_name(stream),
            "sampleRate": _int_or_none(stream.get("sample_rate")),
            "channels": _int_or_none(stream.get("channels")),
            "language": (stream.get("tags") or {}).get("language"),
        }
        for stream in audio_streams
    ]
    if not target.get("codec") and audio_streams:
        target["codec"] = _codec_name(audio_streams[0])


def _apply_ffmpeg_fallback(target: dict[str, Any], path: Path) -> None:
    result = run_ffmpeg(["-hide_banner", "-i", str(path)])
    output = (result.stderr or "") + (result.stdout or "")
    target["duration"] = media_duration(path)
    video_match = re.search(r"Video:\s*([^,\r\n]+).*?(\d{2,5})x(\d{2,5}).*?(?:(\d+(?:\.\d+)?)\s*fps)?", output)
    audio_match = re.search(r"Audio:\s*([^,\r\n]+).*?(\d{4,6})\s*Hz.*?(stereo|mono|(\d+)\s*channels)?", output)
    bitrate_match = re.search(r"bitrate:\s*(\d+)\s*kb/s", output)
    if bitrate_match:
        target["bitrate"] = int(bitrate_match.group(1)) * 1000
    if video_match:
        codec, width, height, fps = video_match.groups()
        target["codec"] = codec.strip().split()[0].lower()
        target["resolution"] = {"width": int(width), "height": int(height)}
        target["aspectRatio"] = _aspect_ratio(int(width), int(height))
        target["fps"] = float(fps) if fps else _parse_tbr(output)
    if audio_match:
        codec, sample_rate, layout, channels = audio_match.groups()
        target["audioTracks"] = [
            {
                "index": 0,
                "codec": codec.strip().split()[0].lower(),
                "sampleRate": int(sample_rate),
                "channels": int(channels or (2 if layout == "stereo" else 1 if layout == "mono" else 0)) or None,
                "language": None,
            }
        ]
        if not target.get("codec"):
            target["codec"] = codec.strip().split()[0].lower()
    if result.returncode != 0 and not video_match and not audio_match:
        target["broken"] = True
        target["issues"].append({"severity": "error", "message": "FFmpeg could not read this file."})


def _normalize_media(source: Path, metadata: dict[str, Any], output_dir: Path, *, target_fps: int, sample_rate: int) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    media_type = _project_media_type(metadata)
    if media_type == "video":
        output = _unique_path(output_dir / f"{source.stem}.normalized.mp4")
        _checked_ffmpeg(
            [
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(source),
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-vf",
                f"fps={target_fps},format=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-ar",
                str(sample_rate),
                "-ac",
                "2",
                "-movflags",
                "+faststart",
                str(output),
            ]
        )
        return output
    if media_type == "audio":
        output = _unique_path(output_dir / f"{source.stem}.normalized.m4a")
        _checked_ffmpeg(
            [
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(source),
                "-vn",
                "-c:a",
                "aac",
                "-ar",
                str(sample_rate),
                "-ac",
                "2",
                "-b:a",
                "192k",
                str(output),
            ]
        )
        return output
    if media_type == "image":
        output = _unique_path(output_dir / f"{source.stem}.normalized.png")
        _checked_ffmpeg(
            [
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(source),
                "-frames:v",
                "1",
                "-f",
                "image2",
                str(output),
            ]
        )
        return output
    return source


def _thumbnail(source: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output = _unique_path(output_dir / f"{source.stem}.thumb.jpg")
    _checked_ffmpeg(
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-vf",
            "scale=320:-2:force_original_aspect_ratio=decrease",
            "-q:v",
            "3",
            str(output),
        ]
    )
    return output


def _waveform(source: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output = _unique_path(output_dir / f"{source.stem}.waveform.png")
    _checked_ffmpeg(
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-filter_complex",
            "aformat=channel_layouts=mono,showwavespic=s=900x160:colors=0x6db5a5",
            "-frames:v",
            "1",
            str(output),
        ]
    )
    return output


def _proxy_video(source: Path, output_dir: Path, *, target_fps: int) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output = _unique_path(output_dir / f"{source.stem}.proxy.mp4")
    _checked_ffmpeg(
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-vf",
            f"scale=960:-2:force_original_aspect_ratio=decrease,fps={target_fps},format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "30",
            "-an",
            str(output),
        ]
    )
    return output


def _checked_ffmpeg(args: list[str]) -> None:
    result = run_ffmpeg(args)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "FFmpeg failed").strip())


def _codec_name(stream: dict[str, Any]) -> str | None:
    codec = stream.get("codec_name")
    if not codec:
        return None
    codec = str(codec).lower()
    if codec == "hevc":
        return "hevc"
    return codec


def _rate(value: Any) -> float | None:
    if not value or value == "0/0":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if "/" in str(value):
        left, right = str(value).split("/", 1)
        denominator = float(right)
        return float(left) / denominator if denominator else None
    return _float_or_none(value)


def _is_vfr(stream: dict[str, Any]) -> bool:
    avg = _rate(stream.get("avg_frame_rate"))
    real = _rate(stream.get("r_frame_rate"))
    if not avg or not real:
        return False
    return abs(avg - real) > 0.01


def _is_hdr(stream: dict[str, Any]) -> bool:
    transfer = str(stream.get("color_transfer") or "").lower()
    primaries = str(stream.get("color_primaries") or "").lower()
    pix_fmt = str(stream.get("pix_fmt") or "").lower()
    return transfer in {"smpte2084", "arib-std-b67"} or "bt2020" in primaries or "p010" in pix_fmt or "10le" in pix_fmt


def _rotation(stream: dict[str, Any]) -> int:
    tags = stream.get("tags") or {}
    rotate = _int_or_none(tags.get("rotate"))
    if rotate is not None:
        return rotate
    for item in stream.get("side_data_list") or []:
        if "rotation" in item:
            return int(float(item["rotation"]))
    return 0


def _aspect_ratio(width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        return "unknown"
    divisor = math.gcd(width, height)
    return f"{width // divisor}:{height // divisor}"


def _int_or_none(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_tbr(output: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*tbr", output)
    return float(match.group(1)) if match else None


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 10000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not create unique path for {path}")


def _safe_asset_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "asset"


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
