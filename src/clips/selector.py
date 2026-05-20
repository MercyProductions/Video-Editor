from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from intelligence.beat_sync import analyze_audio
from utils.media import media_duration, run_ffmpeg


VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
    ".flv",
    ".wmv",
    ".mpeg",
    ".mpg",
    ".m4v",
    ".ts",
    ".mts",
    ".m2ts",
}


@dataclass(slots=True)
class ClipAnalysis:
    path: str
    duration: float
    motionScore: float
    loudnessScore: float
    highlightScore: float
    highlightStart: float
    highlightDuration: float
    highlightReason: str
    tags: list[str]
    motionSpikes: list[dict[str, float]]
    silenceSections: list[dict[str, float]]
    killMomentScore: float
    explosionScore: float
    loudReactionScore: float
    facecamReactionScore: float
    deadFootage: bool
    warnings: list[str]


def select_highlights(
    folder: Path,
    *,
    scene_duration: float = 3,
    max_clips: int = 8,
    output_path: Path | None = None,
) -> dict[str, Any]:
    folder = folder.resolve()
    clips = [path for path in folder.rglob("*") if path.suffix.lower() in VIDEO_EXTENSIONS]
    analyses = [_analyze_clip(path, scene_duration) for path in clips]
    usable = [clip for clip in analyses if not clip.deadFootage]
    usable.sort(key=lambda clip: clip.highlightScore, reverse=True)
    selected = usable[:max_clips]

    result = {
        "folder": str(folder),
        "sceneDuration": scene_duration,
        "scannedClipCount": len(clips),
        "selectedClipCount": len(selected),
        "clips": [asdict(clip) for clip in analyses],
        "selected": [asdict(clip) for clip in selected],
        "warnings": _selection_warnings(clips, analyses, selected),
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2)
            handle.write("\n")
    return result


def _analyze_clip(path: Path, scene_duration: float) -> ClipAnalysis:
    duration = media_duration(path)
    warnings: list[str] = []
    motion_samples = _motion_samples(path)
    if not motion_samples:
        warnings.append("Could not sample video frames for motion.")
    motion_score = round(max((sample["score"] for sample in motion_samples), default=0), 5)
    motion_time = max(motion_samples, key=lambda sample: sample["score"])["time"] if motion_samples else 0

    loudness_score = 0.0
    loud_time = 0.0
    audio_analysis: dict[str, Any] = {}
    try:
        audio_analysis = analyze_audio(path)
        peaks = audio_analysis.get("loudnessPeaks", [])
        if peaks:
            strongest = max(peaks, key=lambda item: item["loudness"])
            loudness_score = float(strongest["loudness"])
            loud_time = float(strongest["time"])
    except Exception:
        warnings.append("No readable audio loudness data.")

    target_time = loud_time if loudness_score > motion_score else motion_time
    highlight_duration = min(scene_duration, duration if duration > 0 else scene_duration)
    highlight_start = max(0.0, min(target_time - highlight_duration / 2, max(duration - highlight_duration, 0)))
    motion_spikes = _top_motion_spikes(motion_samples)
    silence_sections = [
        {"start": float(item["start"]), "end": float(item["end"]), "duration": float(item["duration"])}
        for item in audio_analysis.get("quietSections", [])
    ][:12]
    scores = _semantic_scores(motion_score, loudness_score, motion_spikes, silence_sections)
    tags = _tags_for_clip(scores, motion_score, loudness_score, silence_sections)
    highlight_reason = _highlight_reason(tags, loudness_score, motion_score)
    highlight_score = round(motion_score * 0.58 + loudness_score * 0.42 + scores["killMomentScore"] * 0.2, 5)
    dead = duration <= 0 or (motion_score < 0.008 and loudness_score < 0.012)
    if dead:
        warnings.append("Likely dead footage: low motion and low audio intensity.")
    if "possible_kill_or_payoff" in tags:
        warnings.append("Detected a likely action/payoff moment using motion and loudness heuristics.")

    return ClipAnalysis(
        path=str(path.resolve()),
        duration=round(duration, 3),
        motionScore=motion_score,
        loudnessScore=round(loudness_score, 5),
        highlightScore=highlight_score,
        highlightStart=round(highlight_start, 3),
        highlightDuration=round(highlight_duration, 3),
        highlightReason=highlight_reason,
        tags=tags,
        motionSpikes=motion_spikes,
        silenceSections=silence_sections,
        killMomentScore=scores["killMomentScore"],
        explosionScore=scores["explosionScore"],
        loudReactionScore=scores["loudReactionScore"],
        facecamReactionScore=scores["facecamReactionScore"],
        deadFootage=dead,
        warnings=warnings,
    )


def _motion_samples(path: Path) -> list[dict[str, float]]:
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
        return []
    raw = result.stdout
    frame_size = width * height
    previous: bytes | None = None
    samples: list[dict[str, float]] = []
    for index in range(0, len(raw), frame_size):
        frame = raw[index : index + frame_size]
        if len(frame) != frame_size:
            continue
        if previous is not None:
            diff = sum(abs(a - b) for a, b in zip(frame, previous)) / (frame_size * 255)
            samples.append({"time": round((index // frame_size) / fps, 3), "score": round(diff, 5)})
        previous = frame
    return samples


def _selection_warnings(clips: list[Path], analyses: list[ClipAnalysis], selected: list[ClipAnalysis]) -> list[str]:
    warnings: list[str] = []
    if not clips:
        warnings.append("No video clips found in folder.")
    if analyses and not selected:
        warnings.append("All scanned clips looked like dead footage.")
    return warnings


def _top_motion_spikes(samples: list[dict[str, float]]) -> list[dict[str, float]]:
    if not samples:
        return []
    sorted_samples = sorted(samples, key=lambda item: item["score"], reverse=True)
    spikes: list[dict[str, float]] = []
    for sample in sorted_samples:
        if sample["score"] < 0.012:
            continue
        if any(abs(sample["time"] - existing["time"]) < 0.75 for existing in spikes):
            continue
        spikes.append({"time": float(sample["time"]), "score": float(sample["score"])})
        if len(spikes) >= 10:
            break
    return sorted(spikes, key=lambda item: item["time"])


def _semantic_scores(
    motion_score: float,
    loudness_score: float,
    motion_spikes: list[dict[str, float]],
    silence_sections: list[dict[str, float]],
) -> dict[str, float]:
    spike_score = max((item["score"] for item in motion_spikes), default=0.0)
    quiet_bonus = 0.15 if silence_sections else 0.0
    explosion = min(1.0, loudness_score * 8 + spike_score * 6)
    kill = min(1.0, loudness_score * 5 + motion_score * 12 + quiet_bonus)
    loud_reaction = min(1.0, loudness_score * 9)
    facecam = min(1.0, loudness_score * 7 + max(0.0, 0.04 - motion_score) * 6)
    return {
        "killMomentScore": round(kill, 3),
        "explosionScore": round(explosion, 3),
        "loudReactionScore": round(loud_reaction, 3),
        "facecamReactionScore": round(facecam, 3),
    }


def _tags_for_clip(
    scores: dict[str, float],
    motion_score: float,
    loudness_score: float,
    silence_sections: list[dict[str, float]],
) -> list[str]:
    tags: list[str] = []
    if scores["killMomentScore"] >= 0.45:
        tags.append("possible_kill_or_payoff")
    if scores["explosionScore"] >= 0.55:
        tags.append("explosion_or_impact")
    if scores["loudReactionScore"] >= 0.4:
        tags.append("loud_reaction")
    if scores["facecamReactionScore"] >= 0.35:
        tags.append("possible_facecam_reaction")
    if motion_score >= 0.025:
        tags.append("motion_spike")
    if silence_sections:
        tags.append("has_silence_or_dead_moments")
    if motion_score < 0.008 and loudness_score < 0.012:
        tags.append("dead_footage")
    return tags or ["steady_context"]


def _highlight_reason(tags: list[str], loudness_score: float, motion_score: float) -> str:
    if "possible_kill_or_payoff" in tags:
        return "motion and audio spike candidate"
    if "explosion_or_impact" in tags:
        return "impact/loudness spike candidate"
    if "loud_reaction" in tags:
        return "loud reaction candidate"
    if motion_score >= loudness_score:
        return "highest motion window"
    return "highest loudness window"
