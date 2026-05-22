from __future__ import annotations

from pathlib import Path

from media.compat import export_format_from_path
from parser.models import ProjectSettings
from renderer.ffmpeg import FFmpeg


def mux_export(
    ffmpeg: FFmpeg,
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    settings: ProjectSettings,
    quality: str,
) -> None:
    export_format = export_format_from_path(output_path)
    if export_format == "gif":
        _mux_gif(ffmpeg, video_path, output_path, settings)
        return
    if export_format == "image_sequence":
        _mux_image_sequence(ffmpeg, video_path, output_path)
        return
    if export_format == "webm":
        _mux_webm(ffmpeg, video_path, audio_path, output_path, quality)
        return
    _mux_container(ffmpeg, video_path, audio_path, output_path, export_format)


def _mux_gif(ffmpeg: FFmpeg, video_path: Path, output_path: Path, settings: ProjectSettings) -> None:
    fps = min(settings.fps, 15)
    width = min(settings.width, 1080)
    ffmpeg.run(
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-vf",
            f"fps={fps},scale={width}:-2:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
            "-loop",
            "0",
            str(output_path),
        ]
    )


def _mux_image_sequence(ffmpeg: FFmpeg, video_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg.run(
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-vsync",
            "0",
            str(output_path),
        ]
    )


def _mux_webm(ffmpeg: FFmpeg, video_path: Path, audio_path: Path, output_path: Path, quality: str) -> None:
    ffmpeg.run(
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libvpx-vp9",
            "-crf",
            "32" if quality == "preview" else "24",
            "-b:v",
            "0",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "libopus",
            "-b:a",
            "160k",
            "-shortest",
            str(output_path),
        ]
    )


def _mux_container(ffmpeg: FFmpeg, video_path: Path, audio_path: Path, output_path: Path, export_format: str) -> None:
    container_args: list[str] = []
    if export_format in {"mp4", "mov"}:
        container_args = ["-movflags", "+faststart"]
    ffmpeg.run(
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-colorspace",
            "bt709",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-c:a",
            "aac",
            "-shortest",
            *container_args,
            str(output_path),
        ]
    )
