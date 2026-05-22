from __future__ import annotations

from pathlib import Path
from typing import Any

from assets.resolver import AssetResolver
from parser.models import ProjectConfig
from renderer.ffmpeg import FFmpeg
from renderer.filters import fmt


def render_audio_mix(ffmpeg: FFmpeg, project: ProjectConfig, assets: AssetResolver, temp_dir: Path) -> Path:
    output = temp_dir / "audio.m4a"
    duration = project.settings.duration
    if not project.audio:
        _render_silent_audio(ffmpeg, output, duration)
        return output

    args = ["-y", "-hide_banner", "-loglevel", "error"]
    for track in project.audio:
        raw = track.raw
        if raw.get("loop"):
            args.extend(["-stream_loop", "-1"])
        args.extend(["-i", str(assets.resolve(track.asset, "audio"))])

    filter_graph = _audio_filter_graph(project.audio, duration)
    args.extend(
        [
            "-filter_complex",
            filter_graph,
            "-map",
            "[aout]",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output),
        ]
    )
    ffmpeg.run(args)
    return output


def _render_silent_audio(ffmpeg: FFmpeg, output: Path, duration: float) -> None:
    ffmpeg.run(
        [
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t",
            fmt(duration),
            "-c:a",
            "aac",
            str(output),
        ]
    )


def _audio_filter_graph(tracks: list[Any], duration: float) -> str:
    filters: list[str] = []
    labels: list[str] = []
    for index, track in enumerate(tracks):
        label = f"[a{index}]"
        filters.append(",".join(_track_filter_parts(track.raw, index, duration)) + label)
        labels.append(label)

    filters.append(
        "".join(labels)
        + f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0,"
        + f"atrim=duration={fmt(duration)},aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[aout]"
    )
    return ";".join(filters)


def _track_filter_parts(raw: dict[str, Any], index: int, total_duration: float) -> list[str]:
    start = float(raw.get("start", 0) or 0)
    trim_start = float(raw.get("trimStart", 0) or 0)
    trim_end = raw.get("trimEnd")
    track_duration = _track_duration(raw, start, trim_start, trim_end, total_duration)

    parts = [f"[{index}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"]
    if trim_start or trim_end is not None:
        trim = f"atrim=start={fmt(trim_start)}"
        if trim_end is not None:
            trim += f":end={fmt(float(trim_end))}"
        parts.append(trim)
    parts.extend(
        [
            f"apad=whole_dur={fmt(track_duration)}",
            f"atrim=duration={fmt(track_duration)}",
            "asetpts=PTS-STARTPTS",
            f"volume={fmt(float(raw.get('volume', 1) or 1))}",
        ]
    )
    parts.extend(_audio_effect_parts(raw))
    parts.extend(_audio_fade_parts(raw, track_duration))
    if start > 0:
        delay_ms = int(start * 1000)
        parts.append(f"adelay={delay_ms}|{delay_ms}")
    return parts


def _track_duration(raw: dict[str, Any], start: float, trim_start: float, trim_end: Any, total_duration: float) -> float:
    requested_duration = raw.get("duration")
    if requested_duration is not None:
        return float(requested_duration)
    if trim_end is not None:
        return max(float(trim_end) - trim_start, 0)
    return max(total_duration - start, 0)


def _audio_effect_parts(raw: dict[str, Any]) -> list[str]:
    parts: list[str] = []
    if raw.get("voiceIsolation"):
        parts.extend(["highpass=f=90", "lowpass=f=9000"])
    if raw.get("noiseReduction"):
        parts.append("afftdn")
    bass_emphasis = raw.get("bassEmphasis")
    if bass_emphasis:
        gain = 5 if bass_emphasis is True else float(bass_emphasis)
        parts.append(f"bass=g={fmt(gain)}")
    if raw.get("ducking"):
        parts.append("acompressor=threshold=-22dB:ratio=2.5:attack=15:release=280")
    if raw.get("compressor") or raw.get("autoBalance"):
        parts.append("acompressor=threshold=-18dB:ratio=3:attack=20:release=250")
    if raw.get("limiter") or raw.get("normalize"):
        parts.append("alimiter=limit=0.95")
    if raw.get("loudnessNormalize"):
        parts.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    return parts


def _audio_fade_parts(raw: dict[str, Any], track_duration: float) -> list[str]:
    parts: list[str] = []
    fade_in = float(raw.get("fadeIn", 0) or 0)
    fade_out = float(raw.get("fadeOut", 0) or 0)
    if fade_in > 0:
        parts.append(f"afade=t=in:st=0:d={fmt(fade_in)}")
    if fade_out > 0 and track_duration > fade_out:
        parts.append(f"afade=t=out:st={fmt(track_duration - fade_out)}:d={fmt(fade_out)}")
    return parts
