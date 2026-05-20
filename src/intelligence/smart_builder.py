from __future__ import annotations

from pathlib import Path
from typing import Any

from clips.selector import select_highlights
from intelligence.beat_sync import analyze_audio, apply_beat_sync
from styles.presets import apply_style


def build_smart_project(
    clips_folder: Path,
    music_path: Path,
    *,
    duration: float = 20,
    scene_duration: float = 2.5,
    style: str = "gaming_montage",
    preset: str = "youtube_1080p",
) -> dict[str, Any]:
    clip_selection = select_highlights(clips_folder, scene_duration=scene_duration, max_clips=max(1, int(duration / scene_duration) + 2))
    selected = clip_selection["selected"] or clip_selection["clips"]
    if not selected:
        selected = []

    assets: dict[str, str] = {"music": str(music_path.resolve())}
    timeline: list[dict[str, Any]] = []
    cursor = 0.0
    max_scenes = max(1, int(duration / scene_duration))
    for index, clip in enumerate(selected[:max_scenes]):
        asset_key = f"clip_{index + 1}"
        assets[asset_key] = clip["path"]
        length = min(scene_duration, max(duration - cursor, 0.3))
        timeline.append(
            {
                "id": f"highlight_{index + 1}",
                "start": round(cursor, 3),
                "duration": round(length, 3),
                "layers": [
                    {
                        "type": "video",
                        "asset": asset_key,
                        "x": 0,
                        "y": 0,
                        "width": 1920,
                        "height": 1080,
                        "trimStart": clip["highlightStart"],
                        "trimEnd": round(clip["highlightStart"] + length, 3),
                        "contrast": 1.12,
                    },
                    {
                        "type": "text",
                        "text": f"HIGHLIGHT {index + 1}",
                        "layout": "upper_left",
                        "fontSize": 52,
                        "color": "#ffffff",
                        "strokeColor": "#000000",
                        "strokeWidth": 3,
                    },
                ],
                "transitionOut": {"type": "crossfade", "duration": 0.3},
            }
        )
        cursor += length
        if cursor >= duration:
            break

    if timeline:
        timeline[-1].pop("transitionOut", None)
    else:
        timeline.append(
            {
                "id": "empty",
                "start": 0,
                "duration": duration,
                "layers": [{"type": "text", "text": "No usable clips found", "x": "center", "y": "center"}],
            }
        )

    project = {
        "metadata": {
            "smartBuild": {
                "clipsFolder": str(clips_folder.resolve()),
                "music": str(music_path.resolve()),
                "clipSelection": clip_selection,
            }
        },
        "exportPreset": preset,
        "project": {"width": 1920, "height": 1080, "fps": 60, "duration": duration, "background": "#05070d"},
        "assets": assets,
        "timeline": timeline,
        "audio": [{"asset": "music", "start": 0, "volume": 0.42, "fadeIn": 0.2, "fadeOut": 1}],
    }
    try:
        analysis = analyze_audio(music_path)
        project["metadata"]["smartBuild"]["beatAnalysis"] = analysis
        project = apply_beat_sync(project, analysis)
    except Exception as exc:
        project["metadata"]["smartBuild"].setdefault("warnings", []).append(f"Beat sync skipped: {exc}")
    return apply_style(project, style)
