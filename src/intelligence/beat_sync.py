from __future__ import annotations

import json
import math
import statistics
import struct
import tempfile
import wave
from pathlib import Path
from typing import Any

from utils.media import ffmpeg_binary, run_ffmpeg


def analyze_audio(audio_path: Path, *, output_path: Path | None = None) -> dict[str, Any]:
    audio_path = audio_path.resolve()
    with tempfile.TemporaryDirectory(prefix="ave_audio_") as temp_name:
        wav_path = Path(temp_name) / "analysis.wav"
        result = run_ffmpeg(
            [
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(audio_path),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-vn",
                "-c:a",
                "pcm_s16le",
                str(wav_path),
            ],
            binary=ffmpeg_binary(),
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        samples, sample_rate = _read_wav_samples(wav_path)

    frame_seconds = 0.05
    envelope = _rms_envelope(samples, sample_rate, frame_seconds)
    if not envelope:
        analysis = _empty_analysis(audio_path)
    else:
        analysis = _analysis_from_envelope(audio_path, envelope, frame_seconds)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(analysis, handle, indent=2)
            handle.write("\n")
    return analysis


def apply_beat_sync(project: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    beats = [float(beat["time"]) for beat in analysis.get("beats", [])]
    peaks = [float(peak["time"]) for peak in analysis.get("loudnessPeaks", [])]
    bass_drops = [float(drop["time"]) for drop in analysis.get("bassDrops", [])]
    all_hits = sorted(set(round(value, 3) for value in beats + peaks + bass_drops))
    timeline = project.get("timeline", [])
    if not timeline or not all_hits:
        return project

    duration = float(project.get("project", {}).get("duration", timeline[-1].get("start", 0) + timeline[-1].get("duration", 0)))
    scene_count = len(timeline)
    selected_hits = _spread_hits(all_hits, scene_count + 1, duration)
    if len(selected_hits) < scene_count + 1:
        selected_hits = [round(index * duration / scene_count, 3) for index in range(scene_count + 1)]

    for index, scene in enumerate(timeline):
        start = selected_hits[index]
        end = selected_hits[index + 1] if index + 1 < len(selected_hits) else duration
        scene["start"] = round(start, 3)
        scene["duration"] = round(max(end - start, 0.3), 3)
        if index < len(timeline) - 1:
            scene["transitionOut"] = _transition_for_hit(start, bass_drops)
        _add_hit_effects(scene, start, peaks, bass_drops)

    project.setdefault("metadata", {})["beatSync"] = {
        "bpm": analysis.get("bpm"),
        "beatCount": len(beats),
        "bassDropCount": len(bass_drops),
        "appliedHitCount": len(selected_hits),
    }
    return project


def _read_wav_samples(path: Path) -> tuple[list[int], int]:
    with wave.open(str(path), "rb") as handle:
        sample_rate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    if not frames:
        return [], sample_rate
    count = len(frames) // 2
    samples = list(struct.unpack("<" + "h" * count, frames[: count * 2]))
    return samples, sample_rate


def _rms_envelope(samples: list[int], sample_rate: int, frame_seconds: float) -> list[float]:
    frame_size = max(int(sample_rate * frame_seconds), 1)
    envelope: list[float] = []
    for start in range(0, len(samples), frame_size):
        frame = samples[start : start + frame_size]
        if not frame:
            continue
        rms = math.sqrt(sum(sample * sample for sample in frame) / len(frame)) / 32768
        envelope.append(rms)
    return envelope


def _analysis_from_envelope(audio_path: Path, envelope: list[float], frame_seconds: float) -> dict[str, Any]:
    median = statistics.median(envelope)
    mean = statistics.mean(envelope)
    stdev = statistics.pstdev(envelope) or 0.001
    duration = len(envelope) * frame_seconds

    beats = _detect_beats(envelope, frame_seconds, median, stdev)
    peaks = _detect_peaks(envelope, frame_seconds, median, stdev)
    quiet_sections = _quiet_sections(envelope, frame_seconds, median)
    bass_drops = _bass_drops(envelope, frame_seconds, median, quiet_sections)
    bpm = _estimate_bpm(beats)

    return {
        "audio": str(audio_path),
        "duration": round(duration, 3),
        "bpm": bpm,
        "tempoConfidence": _tempo_confidence(beats),
        "averageLoudness": round(mean, 5),
        "peakLoudness": round(max(envelope), 5),
        "beats": beats,
        "bassDrops": bass_drops,
        "loudnessPeaks": peaks,
        "quietSections": quiet_sections,
        "warnings": _analysis_warnings(beats, bass_drops, quiet_sections),
    }


def _detect_beats(envelope: list[float], frame_seconds: float, median: float, stdev: float) -> list[dict[str, Any]]:
    threshold = max(median * 1.25, median + stdev * 0.45, 0.015)
    beats: list[dict[str, Any]] = []
    last_time = -1.0
    for index in range(1, len(envelope) - 1):
        value = envelope[index]
        onset = value - envelope[index - 1]
        if value >= threshold and value >= envelope[index - 1] and value >= envelope[index + 1] and onset > stdev * 0.15:
            time = round(index * frame_seconds, 3)
            if time - last_time >= 0.22:
                beats.append({"time": time, "strength": round(value, 5)})
                last_time = time
    return beats


def _detect_peaks(envelope: list[float], frame_seconds: float, median: float, stdev: float) -> list[dict[str, Any]]:
    threshold = max(median + stdev, median * 1.6)
    peaks = []
    for index in range(1, len(envelope) - 1):
        value = envelope[index]
        if value >= threshold and value >= envelope[index - 1] and value >= envelope[index + 1]:
            peaks.append({"time": round(index * frame_seconds, 3), "loudness": round(value, 5)})
    peaks.sort(key=lambda item: item["loudness"], reverse=True)
    return sorted(peaks[:40], key=lambda item: item["time"])


def _quiet_sections(envelope: list[float], frame_seconds: float, median: float) -> list[dict[str, Any]]:
    threshold = max(median * 0.55, 0.004)
    sections: list[dict[str, Any]] = []
    start: int | None = None
    for index, value in enumerate(envelope):
        if value <= threshold:
            if start is None:
                start = index
        elif start is not None:
            _append_quiet(sections, start, index, frame_seconds)
            start = None
    if start is not None:
        _append_quiet(sections, start, len(envelope), frame_seconds)
    return sections


def _append_quiet(sections: list[dict[str, Any]], start: int, end: int, frame_seconds: float) -> None:
    duration = (end - start) * frame_seconds
    if duration >= 0.35:
        sections.append({"start": round(start * frame_seconds, 3), "end": round(end * frame_seconds, 3), "duration": round(duration, 3)})


def _bass_drops(
    envelope: list[float],
    frame_seconds: float,
    median: float,
    quiet_sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    drops: list[dict[str, Any]] = []
    threshold = max(median * 2.1, 0.03)
    for index in range(2, len(envelope) - 2):
        value = envelope[index]
        if value < threshold or value < envelope[index - 1] or value < envelope[index + 1]:
            continue
        time = index * frame_seconds
        has_pre_quiet = any(section["end"] <= time and time - section["end"] <= 1.2 for section in quiet_sections)
        previous = envelope[max(0, index - int(1 / frame_seconds)) : index]
        previous_avg = statistics.mean(previous) if previous else median
        if has_pre_quiet or value > previous_avg * 2.4:
            drops.append({"time": round(time, 3), "strength": round(value, 5)})
    deduped: list[dict[str, Any]] = []
    for drop in drops:
        if not deduped or drop["time"] - deduped[-1]["time"] > 1.0:
            deduped.append(drop)
    return deduped[:12]


def _estimate_bpm(beats: list[dict[str, Any]]) -> float | None:
    times = [float(beat["time"]) for beat in beats]
    intervals = [b - a for a, b in zip(times, times[1:]) if 0.24 <= b - a <= 1.5]
    if not intervals:
        return None
    median_interval = statistics.median(intervals)
    bpm = 60 / median_interval
    while bpm < 70:
        bpm *= 2
    while bpm > 190:
        bpm /= 2
    return round(bpm, 1)


def _tempo_confidence(beats: list[dict[str, Any]]) -> float:
    if len(beats) < 4:
        return 0.0
    times = [float(beat["time"]) for beat in beats]
    intervals = [b - a for a, b in zip(times, times[1:]) if 0.24 <= b - a <= 1.5]
    if len(intervals) < 3:
        return 0.25
    spread = statistics.pstdev(intervals)
    return round(max(0.0, min(1.0, 1 - spread)), 2)


def _analysis_warnings(beats: list[dict[str, Any]], bass_drops: list[dict[str, Any]], quiet_sections: list[dict[str, Any]]) -> list[str]:
    warnings = []
    if len(beats) < 4:
        warnings.append("Few clear beats detected; edit timing may rely on loudness peaks.")
    if not bass_drops:
        warnings.append("No strong bass drops detected.")
    if not quiet_sections:
        warnings.append("No quiet sections detected.")
    return warnings


def _spread_hits(hits: list[float], count: int, duration: float) -> list[float]:
    selected = [0.0]
    if count <= 2:
        return [0.0, duration]
    target_gap = duration / (count - 1)
    cursor = target_gap
    for _ in range(count - 2):
        candidates = [hit for hit in hits if selected[-1] + 0.35 < hit < duration - 0.35]
        if not candidates:
            selected.append(round(cursor, 3))
        else:
            selected.append(round(min(candidates, key=lambda hit: abs(hit - cursor)), 3))
        cursor += target_gap
    selected.append(round(duration, 3))
    return sorted(set(selected))


def _transition_for_hit(scene_start: float, bass_drops: list[float]) -> dict[str, Any]:
    if any(abs(drop - scene_start) < 0.45 for drop in bass_drops):
        return {"type": "zoom", "duration": 0.25}
    return {"type": "crossfade", "duration": 0.3}


def _add_hit_effects(scene: dict[str, Any], scene_start: float, peaks: list[float], bass_drops: list[float]) -> None:
    hit_nearby = any(abs(hit - scene_start) < 0.35 for hit in peaks + bass_drops)
    for layer in scene.get("layers", []):
        if layer.get("type") == "text" and hit_nearby:
            layer["effects"] = sorted(set(layer.get("effects", []) + ["shake"]))
            layer.setdefault("animation", {"in": "pulse", "out": "fade", "duration": 0.25})
        if layer.get("type") in {"video", "image"} and hit_nearby:
            layer.setdefault("animation", {"in": "zoomIn", "duration": 0.25})


def _empty_analysis(audio_path: Path) -> dict[str, Any]:
    return {
        "audio": str(audio_path),
        "duration": 0,
        "bpm": None,
        "tempoConfidence": 0,
        "averageLoudness": 0,
        "peakLoudness": 0,
        "beats": [],
        "bassDrops": [],
        "loudnessPeaks": [],
        "quietSections": [],
        "warnings": ["No readable audio samples found."],
    }
