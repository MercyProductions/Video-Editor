from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from intelligence.beat_sync import analyze_audio


def analyze_audio_intelligence(audio_path: Path, *, output_path: Path | None = None) -> dict[str, Any]:
    """Create practical mix/edit recommendations from local audio analysis."""
    base = analyze_audio(audio_path)
    average = float(base.get("averageLoudness", 0) or 0)
    peak = float(base.get("peakLoudness", 0) or 0)
    quiet = base.get("quietSections", [])
    beats = base.get("beats", [])
    drops = base.get("bassDrops", [])
    peaks = base.get("loudnessPeaks", [])

    recommendations: list[dict[str, Any]] = []
    if peak > 0.55:
        recommendations.append(_rec("limiter", "Enable limiter to keep music from clipping during transitions.", {"limiter": True}))
    if average < 0.035 and peak < 0.18:
        recommendations.append(_rec("gain", "Track is quiet; increase music volume or normalize it.", {"normalize": True, "volume": 0.65}))
    if len(quiet) >= 2:
        recommendations.append(_rec("ducking", "Quiet sections are present; use them for title cards or VO emphasis.", {"ducking": True}))
    if drops:
        recommendations.append(_rec("bass_hit", "Use bass drops for zoom transitions and lighting pulses.", {"bassEmphasis": 4}))
    if len(beats) >= 8:
        recommendations.append(_rec("beat_sync", "Beat grid is strong enough for cut timing.", {"beatSync": True}))

    report = {
        **base,
        "mixProfile": {
            "averageLoudness": round(average, 5),
            "peakLoudness": round(peak, 5),
            "dynamicRange": round(max(peak - average, 0), 5),
            "quietSectionCount": len(quiet),
            "beatCount": len(beats),
            "bassDropCount": len(drops),
            "loudnessPeakCount": len(peaks),
        },
        "recommendedTrackSettings": _recommended_track_settings(base),
        "editRecommendations": recommendations,
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _recommended_track_settings(analysis: dict[str, Any]) -> dict[str, Any]:
    peak = float(analysis.get("peakLoudness", 0) or 0)
    average = float(analysis.get("averageLoudness", 0) or 0)
    volume = 0.42
    if peak > 0.45:
        volume = 0.34
    elif average < 0.035:
        volume = 0.55
    return {
        "volume": round(volume, 2),
        "fadeIn": 0.2,
        "fadeOut": 1.0,
        "compressor": True,
        "limiter": peak > 0.45,
        "bassEmphasis": 3 if analysis.get("bassDrops") else 0,
        "loop": True,
    }


def _rec(kind: str, message: str, settings: dict[str, Any]) -> dict[str, Any]:
    return {"type": kind, "message": message, "settings": settings}
