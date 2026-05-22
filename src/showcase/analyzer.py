from __future__ import annotations

import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

from assets.intelligence import analyze_asset
from showcase.ocr import analyze_screen_text
from utils.media import media_duration, run_ffmpeg


def analyze_desktop_recording(
    recording_path: Path,
    *,
    output_path: Path | None = None,
    max_samples: int = 900,
    analysis_width: int = 160,
) -> dict[str, Any]:
    recording_path = recording_path.resolve()
    if not recording_path.exists():
        raise FileNotFoundError(f"Desktop recording does not exist: {recording_path}")

    started = time.perf_counter()
    asset_report = analyze_asset("recording", recording_path)
    duration = float(asset_report.get("duration") or media_duration(recording_path) or 0)
    resolution = asset_report.get("resolution") or {"width": 1920, "height": 1080}
    source_width = int(resolution.get("width") or 1920)
    source_height = int(resolution.get("height") or 1080)
    sample_fps = _sample_fps(duration, max_samples)
    frames = _sample_frames(recording_path, sample_fps=sample_fps, width=analysis_width, source_width=source_width, source_height=source_height)

    frame_count = len(frames)
    if frame_count < 2:
        report = _fallback_report(recording_path, asset_report, duration, source_width, source_height, started)
        _write_report(report, output_path)
        return report

    motion_samples: list[dict[str, Any]] = []
    text_samples: list[dict[str, Any]] = []
    previous = frames[0]
    for index, frame in enumerate(frames[1:], start=1):
        time_s = round(index / sample_fps, 3)
        motion = _motion_between(previous, frame)
        text_density = _text_density(frame)
        motion_samples.append({"time": time_s, **motion})
        text_samples.append({"time": time_s, "density": round(text_density, 5)})
        previous = frame

    intensities = [float(item["intensity"]) for item in motion_samples]
    text_values = [float(item["density"]) for item in text_samples]
    median_motion = statistics.median(intensities) if intensities else 0
    stdev_motion = statistics.pstdev(intensities) if len(intensities) > 1 else 0
    median_text = statistics.median(text_values) if text_values else 0
    stdev_text = statistics.pstdev(text_values) if len(text_values) > 1 else 0

    idle_sections = _sections_by_threshold(
        motion_samples,
        threshold=max(0.004, median_motion * 0.45),
        sample_fps=sample_fps,
        mode="below",
        min_duration=1.2,
    )
    fast_motion = _sections_by_threshold(
        motion_samples,
        threshold=max(0.035, median_motion + stdev_motion * 1.25),
        sample_fps=sample_fps,
        mode="above",
        min_duration=0.35,
    )
    scene_changes = _scene_changes(motion_samples, max(0.08, median_motion + stdev_motion * 2.4))
    text_heavy = _text_heavy_sections(text_samples, max(0.12, median_text + stdev_text * 0.8), sample_fps)
    clicks = _click_candidates(motion_samples, median_motion, stdev_motion)
    focus_events = _focus_events(motion_samples, text_samples, clicks, scene_changes, source_width, source_height)
    cursor_intent = _cursor_intent(motion_samples, clicks, idle_sections, sample_fps)
    ocr_report = analyze_screen_text(
        recording_path,
        sample_times=_ocr_sample_times(duration, focus_events, scene_changes, text_heavy),
        source_width=source_width,
        source_height=source_height,
    )
    ui_importance = _ui_importance(focus_events, clicks, scene_changes, text_heavy, cursor_intent, source_width, source_height, ocr_report=ocr_report)
    mistake_removal = _mistake_removal(idle_sections, clicks, scene_changes, fast_motion, duration)

    report = _build_analysis_report(
        recording_path,
        asset_report=asset_report,
        duration=duration,
        source_width=source_width,
        source_height=source_height,
        sample_fps=sample_fps,
        frame_count=frame_count,
        analysis_width=frames[0]["width"],
        analysis_height=frames[0]["height"],
        median_motion=median_motion,
        intensities=intensities,
        motion_samples=motion_samples,
        idle_sections=idle_sections,
        fast_motion=fast_motion,
        scene_changes=scene_changes,
        text_heavy=text_heavy,
        clicks=clicks,
        focus_events=focus_events,
        cursor_intent=cursor_intent,
        ui_importance=ui_importance,
        ocr_report=ocr_report,
        mistake_removal=mistake_removal,
        started=started,
    )
    _write_report(report, output_path)
    return report


def _build_analysis_report(
    recording_path: Path,
    *,
    asset_report: dict[str, Any],
    duration: float,
    source_width: int,
    source_height: int,
    sample_fps: float,
    frame_count: int,
    analysis_width: int,
    analysis_height: int,
    median_motion: float,
    intensities: list[float],
    motion_samples: list[dict[str, Any]],
    idle_sections: list[dict[str, Any]],
    fast_motion: list[dict[str, Any]],
    scene_changes: list[dict[str, Any]],
    text_heavy: list[dict[str, Any]],
    clicks: list[dict[str, Any]],
    focus_events: list[dict[str, Any]],
    cursor_intent: dict[str, Any],
    ui_importance: dict[str, Any],
    ocr_report: dict[str, Any],
    mistake_removal: dict[str, Any],
    started: float,
) -> dict[str, Any]:
    return {
        "format": "automatic-video-editor-desktop-showcase-analysis",
        "createdAt": _now(),
        "recording": str(recording_path),
        "duration": round(duration, 3),
        "source": {
            "width": source_width,
            "height": source_height,
            "fps": asset_report.get("fps"),
            "codec": asset_report.get("codec"),
            "audioPresence": bool(asset_report.get("audioPresence")),
            "motionIntensity": asset_report.get("motionIntensity"),
            "dominantColors": asset_report.get("dominantColors", []),
            "issues": asset_report.get("issues", []),
        },
        "sampling": {"fps": round(sample_fps, 3), "frameCount": frame_count, "analysisWidth": analysis_width, "analysisHeight": analysis_height},
        "summary": {
            "medianMotion": round(median_motion, 5),
            "peakMotion": round(max(intensities), 5) if intensities else 0,
            "idleSeconds": round(sum(float(item["duration"]) for item in idle_sections), 3),
            "sceneChangeCount": len(scene_changes),
            "clickCandidateCount": len(clicks),
            "textHeavyCount": len(text_heavy),
            "focusEventCount": len(focus_events),
        },
        "mouseMovement": _movement_summary(motion_samples),
        "clickTiming": clicks,
        "uiInteractions": _ui_interactions(clicks, scene_changes, fast_motion),
        "windowChanges": scene_changes,
        "sceneChanges": scene_changes,
        "idleMoments": idle_sections,
        "fastMotion": fast_motion,
        "importantUiFocusAreas": focus_events[:24],
        "activeUiRegions": _active_regions(focus_events),
        "uiImportanceDetection": ui_importance,
        "ocrDrivenUiDetection": ocr_report,
        "cursorIntent": cursor_intent,
        "textHeavyMoments": text_heavy,
        "deadTimeRemoval": {
            "recommendedCuts": _recommended_dead_cuts(idle_sections, duration),
            "strategy": "trim long idle sections, speed up medium pauses, preserve sections around clicks and scene changes",
        },
        "mistakeRemoval": mistake_removal,
        "analysisTimeSeconds": round(time.perf_counter() - started, 3),
    }


def _sample_fps(duration: float, max_samples: int) -> float:
    if duration <= 0:
        return 4.0
    return max(1.0, min(6.0, max_samples / max(duration, 1)))


def _sample_frames(path: Path, *, sample_fps: float, width: int, source_width: int, source_height: int) -> list[dict[str, Any]]:
    aspect = source_height / max(source_width, 1)
    height = max(24, int(round(width * aspect)))
    result = run_ffmpeg(
        [
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-vf",
            f"fps={sample_fps:.4f},scale={width}:{height},format=gray",
            "-an",
            "-f",
            "rawvideo",
            "-",
        ],
        capture_bytes=True,
    )
    if result.returncode != 0 or not result.stdout:
        return []
    frame_size = width * height
    frames = []
    raw = result.stdout
    for offset in range(0, len(raw), frame_size):
        frame = raw[offset : offset + frame_size]
        if len(frame) == frame_size:
            frames.append({"width": width, "height": height, "pixels": frame})
    return frames


def _motion_between(previous: dict[str, Any], frame: dict[str, Any]) -> dict[str, Any]:
    pixels_a = previous["pixels"]
    pixels_b = frame["pixels"]
    width = int(frame["width"])
    height = int(frame["height"])
    total = 0
    weighted_x = 0.0
    weighted_y = 0.0
    active = 0
    threshold = 18
    for index, (a, b) in enumerate(zip(pixels_a, pixels_b)):
        diff = abs(a - b)
        total += diff
        if diff >= threshold:
            x = index % width
            y = index // width
            weighted_x += x * diff
            weighted_y += y * diff
            active += diff
    intensity = total / (len(pixels_b) * 255)
    if active > 0:
        cx = weighted_x / active / max(width - 1, 1)
        cy = weighted_y / active / max(height - 1, 1)
        spread = min(1.0, math.sqrt(active / (len(pixels_b) * 255)))
    else:
        cx = 0.5
        cy = 0.5
        spread = 0.0
    return {
        "intensity": round(float(intensity), 5),
        "focusX": round(float(cx), 4),
        "focusY": round(float(cy), 4),
        "spread": round(float(spread), 5),
    }


def _text_density(frame: dict[str, Any]) -> float:
    pixels = frame["pixels"]
    width = int(frame["width"])
    height = int(frame["height"])
    if width < 2 or height < 2:
        return 0.0
    edges = 0
    checks = 0
    for y in range(1, height - 1, 2):
        row = y * width
        prev_row = (y - 1) * width
        for x in range(1, width - 1, 2):
            value = pixels[row + x]
            if abs(value - pixels[row + x - 1]) > 34 or abs(value - pixels[prev_row + x]) > 34:
                edges += 1
            checks += 1
    return edges / max(checks, 1)


def _sections_by_threshold(
    samples: list[dict[str, Any]],
    *,
    threshold: float,
    sample_fps: float,
    mode: str,
    min_duration: float,
) -> list[dict[str, Any]]:
    sections = []
    start: float | None = None
    last = 0.0
    for item in samples:
        value = float(item["intensity"])
        keep = value <= threshold if mode == "below" else value >= threshold
        time_s = float(item["time"])
        if keep and start is None:
            start = max(0.0, time_s - 1 / sample_fps)
        if not keep and start is not None:
            _append_section(sections, start, last, min_duration)
            start = None
        last = time_s
    if start is not None:
        _append_section(sections, start, last, min_duration)
    return sections


def _append_section(sections: list[dict[str, Any]], start: float, end: float, min_duration: float) -> None:
    duration = max(end - start, 0)
    if duration >= min_duration:
        sections.append({"start": round(start, 3), "end": round(end, 3), "duration": round(duration, 3)})


def _scene_changes(samples: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    rows = []
    last = -10.0
    for item in samples:
        time_s = float(item["time"])
        intensity = float(item["intensity"])
        if intensity >= threshold and time_s - last >= 0.8:
            rows.append({"time": round(time_s, 3), "confidence": round(min(1.0, intensity / max(threshold, 0.001)), 2)})
            last = time_s
    return rows


def _text_heavy_sections(samples: list[dict[str, Any]], threshold: float, sample_fps: float) -> list[dict[str, Any]]:
    sections = []
    start: float | None = None
    last = 0.0
    for item in samples:
        time_s = float(item["time"])
        if float(item["density"]) >= threshold:
            if start is None:
                start = max(0.0, time_s - 1 / sample_fps)
        elif start is not None:
            _append_section(sections, start, last, 0.6)
            start = None
        last = time_s
    if start is not None:
        _append_section(sections, start, last, 0.6)
    return sections


def _click_candidates(samples: list[dict[str, Any]], median: float, stdev: float) -> list[dict[str, Any]]:
    threshold = max(0.025, median + stdev * 1.8)
    rows = []
    last = -1.0
    for item in samples:
        time_s = float(item["time"])
        if float(item["intensity"]) >= threshold and float(item["spread"]) <= 0.42 and time_s - last >= 0.45:
            rows.append(
                {
                    "time": round(time_s, 3),
                    "confidence": round(min(1.0, float(item["intensity"]) / max(threshold, 0.001)), 2),
                    "x": item["focusX"],
                    "y": item["focusY"],
                    "reason": "localized motion spike",
                }
            )
            last = time_s
    return rows[:80]


def _focus_events(
    motion_samples: list[dict[str, Any]],
    text_samples: list[dict[str, Any]],
    clicks: list[dict[str, Any]],
    scene_changes: list[dict[str, Any]],
    source_width: int,
    source_height: int,
) -> list[dict[str, Any]]:
    text_by_time = {round(float(item["time"]), 3): float(item["density"]) for item in text_samples}
    click_times = [float(item["time"]) for item in clicks]
    scene_times = [float(item["time"]) for item in scene_changes]
    scored = []
    for item in motion_samples:
        time_s = float(item["time"])
        near_click = min((abs(time_s - click) for click in click_times), default=10)
        near_scene = min((abs(time_s - change) for change in scene_times), default=10)
        text_density = text_by_time.get(round(time_s, 3), 0.0)
        score = float(item["intensity"]) * 1.9 + text_density * 0.55
        if near_click <= 0.35:
            score += 0.4
        if near_scene <= 0.5:
            score += 0.22
        if score <= 0:
            continue
        scored.append((score, item, text_density, near_click <= 0.35, near_scene <= 0.5))
    scored.sort(key=lambda row: row[0], reverse=True)
    selected = []
    used_times: list[float] = []
    for score, item, text_density, is_click, is_scene in scored:
        time_s = float(item["time"])
        if any(abs(time_s - used) < 1.0 for used in used_times):
            continue
        x = float(item["focusX"])
        y = float(item["focusY"])
        selected.append(
            {
                "time": round(time_s, 3),
                "score": round(min(score, 1.0), 3),
                "x": round(x, 4),
                "y": round(y, 4),
                "sourceRect": _source_rect(x, y, source_width, source_height),
                "reason": _focus_reason(is_click, is_scene, text_density),
            }
        )
        used_times.append(time_s)
        if len(selected) >= 36:
            break
    return sorted(selected, key=lambda item: item["time"])


def _source_rect(x: float, y: float, width: int, height: int) -> dict[str, int]:
    rect_w = int(width * 0.46)
    rect_h = int(height * 0.46)
    left = int(x * width - rect_w / 2)
    top = int(y * height - rect_h / 2)
    left = max(0, min(left, max(width - rect_w, 0)))
    top = max(0, min(top, max(height - rect_h, 0)))
    return {"x": left, "y": top, "width": rect_w, "height": rect_h}


def _focus_reason(is_click: bool, is_scene: bool, text_density: float) -> str:
    if is_click:
        return "cursor emphasis / likely click"
    if is_scene:
        return "window or scene change"
    if text_density > 0.16:
        return "text-heavy UI area"
    return "motion focus"


def _ocr_sample_times(
    duration: float,
    focus_events: list[dict[str, Any]],
    scene_changes: list[dict[str, Any]],
    text_heavy: list[dict[str, Any]],
) -> list[float]:
    times: list[float] = []
    times.extend(float(item.get("time", 0)) for item in focus_events[:8])
    times.extend(float(item.get("time", 0)) for item in scene_changes[:5])
    times.extend((float(item["start"]) + float(item["end"])) / 2 for item in text_heavy[:5])
    if duration > 0:
        times.extend([min(duration * 0.25, duration - 0.1), min(duration * 0.5, duration - 0.1), min(duration * 0.75, duration - 0.1)])
    return [round(max(0.0, item), 3) for item in times]


def _active_regions(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not events:
        return []
    buckets: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for event in events:
        key = (int(float(event["x"]) * 3), int(float(event["y"]) * 3))
        buckets.setdefault(key, []).append(event)
    regions = []
    for (_gx, _gy), items in buckets.items():
        regions.append(
            {
                "count": len(items),
                "averageX": round(statistics.mean(float(item["x"]) for item in items), 4),
                "averageY": round(statistics.mean(float(item["y"]) for item in items), 4),
                "timeRange": [items[0]["time"], items[-1]["time"]],
            }
        )
    return sorted(regions, key=lambda item: item["count"], reverse=True)[:9]


def _ui_interactions(clicks: list[dict[str, Any]], scene_changes: list[dict[str, Any]], fast_motion: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for click in clicks[:30]:
        rows.append({"type": "click_or_control", "time": click["time"], "confidence": click["confidence"]})
    for change in scene_changes[:20]:
        rows.append({"type": "window_or_scene_change", "time": change["time"], "confidence": change["confidence"]})
    for section in fast_motion[:20]:
        rows.append({"type": "fast_interaction_sequence", **section})
    return sorted(rows, key=lambda item: float(item.get("time", item.get("start", 0))))


def _cursor_intent(samples: list[dict[str, Any]], clicks: list[dict[str, Any]], idle_sections: list[dict[str, Any]], sample_fps: float) -> dict[str, Any]:
    if not samples:
        return {"slowHover": [], "repeatedMovement": [], "actionPoints": [], "dragSequences": [], "idleCursor": []}
    intensities = [float(item["intensity"]) for item in samples]
    median = statistics.median(intensities)
    slow_hover = _stable_focus_sections(samples, max_motion=max(0.003, median * 0.75), sample_fps=sample_fps)
    repeated = _repeated_movement_sections(samples, sample_fps)
    drag = _drag_sequences(samples, threshold=max(0.018, median * 1.2), sample_fps=sample_fps)
    return {
        "slowHover": slow_hover,
        "repeatedMovement": repeated,
        "actionPoints": [{"time": item["time"], "x": item.get("x", 0.5), "y": item.get("y", 0.5), "confidence": item.get("confidence", 0.5)} for item in clicks],
        "dragSequences": drag,
        "idleCursor": [{"start": item["start"], "end": item["end"], "duration": item["duration"], "intent": "dead section candidate"} for item in idle_sections],
        "interpretation": "slow hover suggests importance; repeated movement suggests searching; click spikes are action points; long idle is dead time.",
    }


def _stable_focus_sections(samples: list[dict[str, Any]], *, max_motion: float, sample_fps: float) -> list[dict[str, Any]]:
    sections = []
    start: float | None = None
    points: list[dict[str, Any]] = []
    for item in samples:
        if float(item["intensity"]) <= max_motion:
            if start is None:
                start = max(0.0, float(item["time"]) - 1 / sample_fps)
            points.append(item)
        elif start is not None:
            _append_stable_section(sections, start, float(points[-1]["time"]), points)
            start = None
            points = []
    if start is not None and points:
        _append_stable_section(sections, start, float(points[-1]["time"]), points)
    return sections[:20]


def _append_stable_section(sections: list[dict[str, Any]], start: float, end: float, points: list[dict[str, Any]]) -> None:
    if end - start < 0.8:
        return
    sections.append(
        {
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(end - start, 3),
            "x": round(statistics.mean(float(item["focusX"]) for item in points), 4),
            "y": round(statistics.mean(float(item["focusY"]) for item in points), 4),
            "intent": "important hover",
        }
    )


def _repeated_movement_sections(samples: list[dict[str, Any]], sample_fps: float) -> list[dict[str, Any]]:
    rows = []
    window = max(4, int(sample_fps * 1.2))
    for index in range(0, max(len(samples) - window, 0), max(1, window // 2)):
        group = samples[index : index + window]
        if len(group) < 3:
            continue
        path = _path_distance(group)
        displacement = math.dist((float(group[0]["focusX"]), float(group[0]["focusY"])), (float(group[-1]["focusX"]), float(group[-1]["focusY"])))
        if path > 0.45 and displacement < path * 0.42:
            rows.append({"start": group[0]["time"], "end": group[-1]["time"], "duration": round(float(group[-1]["time"]) - float(group[0]["time"]), 3), "intent": "user searching"})
    return _dedupe_sections(rows)


def _drag_sequences(samples: list[dict[str, Any]], *, threshold: float, sample_fps: float) -> list[dict[str, Any]]:
    rows = []
    start: dict[str, Any] | None = None
    points: list[dict[str, Any]] = []
    for item in samples:
        if float(item["intensity"]) >= threshold and float(item["spread"]) <= 0.55:
            if start is None:
                start = item
            points.append(item)
        elif start is not None:
            _append_drag(rows, start, points)
            start = None
            points = []
    if start is not None:
        _append_drag(rows, start, points)
    return rows[:20]


def _append_drag(rows: list[dict[str, Any]], start: dict[str, Any], points: list[dict[str, Any]]) -> None:
    if not points:
        return
    duration = float(points[-1]["time"]) - float(start["time"])
    if duration < 0.45:
        return
    rows.append(
        {
            "start": start["time"],
            "end": points[-1]["time"],
            "duration": round(duration, 3),
            "from": {"x": start["focusX"], "y": start["focusY"]},
            "to": {"x": points[-1]["focusX"], "y": points[-1]["focusY"]},
            "intent": "drag or interaction sequence",
        }
    )


def _ui_importance(
    focus_events: list[dict[str, Any]],
    clicks: list[dict[str, Any]],
    scene_changes: list[dict[str, Any]],
    text_heavy: list[dict[str, Any]],
    cursor_intent: dict[str, Any],
    source_width: int,
    source_height: int,
    *,
    ocr_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_regions = _active_regions(focus_events)
    clicked = [_region_from_point(item.get("x", 0.5), item.get("y", 0.5), source_width, source_height, "clicked button/control", item["time"], item.get("confidence", 0.7)) for item in clicks[:24]]
    hovered = [_region_from_point(item.get("x", 0.5), item.get("y", 0.5), source_width, source_height, "hovered control", item["start"], 0.6) for item in cursor_intent.get("slowHover", [])[:16]]
    ocr_blocks = _ocr_text_blocks(ocr_report)
    status_blocks = _ocr_status_blocks(ocr_report)
    brand_blocks = _ocr_brand_blocks(ocr_report)
    return {
        "activeWindows": [_active_window_region(region, source_width, source_height) for region in active_regions[:6]],
        "clickedButtons": clicked,
        "hoveredControls": hovered,
        "menusOpening": [{"time": item["time"], "confidence": item.get("confidence", 0.5), "reason": "sudden localized layout change"} for item in scene_changes[:10]],
        "modalDialogs": [_modal_candidate(event, source_width, source_height) for event in focus_events if 0.28 <= float(event.get("x", 0.5)) <= 0.72 and 0.2 <= float(event.get("y", 0.5)) <= 0.78][:10],
        "loadingStates": [],
        "successErrorMessages": [{"start": item["start"], "end": item["end"], "reason": "text/status region changed"} for item in text_heavy[:10]] + status_blocks,
        "textBlocks": [{"start": item["start"], "end": item["end"], "duration": item["duration"], "importance": "readability protected"} for item in text_heavy] + ocr_blocks,
        "logoBrandAreas": _brand_area_candidates(focus_events, source_width, source_height) + brand_blocks,
    }


def _mistake_removal(idle_sections: list[dict[str, Any]], clicks: list[dict[str, Any]], scene_changes: list[dict[str, Any]], fast_motion: list[dict[str, Any]], duration: float) -> dict[str, Any]:
    removals = _recommended_dead_cuts(idle_sections, duration)
    for section in idle_sections:
        if float(section["duration"]) >= 2.0:
            removals.append({"start": section["start"], "end": section["end"], "action": "speed_up_or_trim", "reason": "long pause/loading wait"})
    for first, second in zip(clicks, clicks[1:]):
        if float(second["time"]) - float(first["time"]) < 0.55:
            removals.append({"start": first["time"], "end": second["time"], "action": "trim_if_repeated", "reason": "possible repeated/failed click"})
    for section in fast_motion:
        if float(section["duration"]) >= 1.2:
            removals.append({"start": section["start"], "end": section["end"], "action": "review", "reason": "possible alt-tab or wrong window movement"})
    return {
        "recommendedRemovals": _dedupe_sections(removals),
        "detectors": ["idle pauses", "loading waits", "repeated click attempts", "rapid wrong-window movement"],
        "note": "No destructive edits are applied to source media; generated JSON avoids or trims these ranges at render time.",
    }


def _region_from_point(x: Any, y: Any, width: int, height: int, label: str, time_s: Any, confidence: Any) -> dict[str, Any]:
    rect = _source_rect(float(x), float(y), width, height)
    return {"time": time_s, "label": label, "confidence": round(float(confidence), 3), "rect": rect}


def _active_window_region(region: dict[str, Any], width: int, height: int) -> dict[str, Any]:
    x = float(region.get("averageX", 0.5))
    y = float(region.get("averageY", 0.5))
    rect = _source_rect(x, y, width, height)
    rect["width"] = min(width, int(rect["width"] * 1.35))
    rect["height"] = min(height, int(rect["height"] * 1.25))
    return {"rect": rect, "confidence": min(1.0, 0.42 + int(region.get("count", 1)) * 0.08), "timeRange": region.get("timeRange")}


def _modal_candidate(event: dict[str, Any], width: int, height: int) -> dict[str, Any]:
    return {"time": event["time"], "rect": _source_rect(float(event.get("x", 0.5)), float(event.get("y", 0.5)), width, height), "confidence": event.get("score", 0.4), "reason": "centered high-importance UI region"}


def _brand_area_candidates(events: list[dict[str, Any]], width: int, height: int) -> list[dict[str, Any]]:
    candidates = []
    for event in events:
        x = float(event.get("x", 0.5))
        y = float(event.get("y", 0.5))
        if y <= 0.24 or x <= 0.22:
            candidates.append({"time": event["time"], "rect": _source_rect(x, y, width, height), "confidence": event.get("score", 0.35), "reason": "top or left UI branding area"})
    return candidates[:8]


def _ocr_text_blocks(ocr_report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not ocr_report or not ocr_report.get("available"):
        return []
    rows = []
    for block in ocr_report.get("textBlocks", [])[:24]:
        time_s = float(block.get("time", 0))
        rows.append(
            {
                "start": round(max(0.0, time_s - 0.35), 3),
                "end": round(time_s + 0.35, 3),
                "duration": 0.7,
                "importance": "ocr readability protected",
                "text": block.get("text"),
                "confidence": block.get("confidence", 0.5),
                "rect": block.get("rect"),
            }
        )
    return rows


def _ocr_status_blocks(ocr_report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not ocr_report or not ocr_report.get("available"):
        return []
    status_words = ("success", "error", "failed", "complete", "warning", "blocked", "done", "ready")
    rows = []
    for block in ocr_report.get("textBlocks", [])[:40]:
        text = str(block.get("text", "")).lower()
        if not any(word in text for word in status_words):
            continue
        time_s = float(block.get("time", 0))
        rows.append(
            {
                "start": round(max(0.0, time_s - 0.5), 3),
                "end": round(time_s + 0.5, 3),
                "reason": "local OCR detected status text",
                "text": block.get("text"),
                "confidence": block.get("confidence", 0.5),
                "rect": block.get("rect"),
            }
        )
    return rows[:10]


def _ocr_brand_blocks(ocr_report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not ocr_report or not ocr_report.get("available"):
        return []
    rows = []
    for block in ocr_report.get("textBlocks", [])[:20]:
        rect = block.get("rect") or {}
        x = int(rect.get("x", 0))
        y = int(rect.get("y", 0))
        if y <= 180 or x <= 220:
            rows.append(
                {
                    "time": block.get("time", 0),
                    "rect": rect,
                    "confidence": block.get("confidence", 0.45),
                    "reason": "local OCR found text in likely brand/navigation area",
                    "text": block.get("text"),
                }
            )
    return rows[:8]


def _path_distance(group: list[dict[str, Any]]) -> float:
    distance = 0.0
    for left, right in zip(group, group[1:]):
        distance += math.dist((float(left["focusX"]), float(left["focusY"])), (float(right["focusX"]), float(right["focusY"])))
    return distance


def _dedupe_sections(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in sorted(rows, key=lambda item: float(item.get("start", item.get("time", 0)))):
        start = float(row.get("start", row.get("time", 0)))
        end = float(row.get("end", start))
        if result and start <= float(result[-1].get("end", result[-1].get("time", 0))) + 0.25:
            result[-1]["end"] = max(float(result[-1].get("end", start)), end)
            result[-1]["duration"] = round(float(result[-1]["end"]) - float(result[-1].get("start", start)), 3)
            continue
        result.append(dict(row))
    return result


def _movement_summary(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if not samples:
        return {"pathDistance": 0, "averageIntensity": 0, "peakIntensity": 0}
    distance = 0.0
    previous = samples[0]
    for item in samples[1:]:
        distance += math.dist((float(previous["focusX"]), float(previous["focusY"])), (float(item["focusX"]), float(item["focusY"])))
        previous = item
    intensities = [float(item["intensity"]) for item in samples]
    return {
        "pathDistance": round(distance, 3),
        "averageIntensity": round(statistics.mean(intensities), 5),
        "peakIntensity": round(max(intensities), 5),
        "stability": round(max(0.0, min(1.0, 1 - distance / max(len(samples), 1))), 3),
    }


def _recommended_dead_cuts(idle_sections: list[dict[str, Any]], duration: float) -> list[dict[str, Any]]:
    cuts = []
    for section in idle_sections:
        start = float(section["start"])
        end = float(section["end"])
        if start < 0.5 or duration - end < 0.5:
            continue
        if float(section["duration"]) >= 1.5:
            cuts.append({"start": round(start + 0.25, 3), "end": round(end - 0.25, 3), "action": "trim"})
        else:
            cuts.append({"start": start, "end": end, "action": "speed_up"})
    return cuts


def _fallback_report(recording_path: Path, asset_report: dict[str, Any], duration: float, width: int, height: int, started: float) -> dict[str, Any]:
    return {
        "format": "automatic-video-editor-desktop-showcase-analysis",
        "createdAt": _now(),
        "recording": str(recording_path),
        "duration": round(duration, 3),
        "source": {"width": width, "height": height, "audioPresence": bool(asset_report.get("audioPresence")), "issues": asset_report.get("issues", [])},
        "sampling": {"fps": 0, "frameCount": 0},
        "summary": {"medianMotion": 0, "peakMotion": 0, "idleSeconds": 0, "sceneChangeCount": 0, "clickCandidateCount": 0, "textHeavyCount": 0, "focusEventCount": 0},
        "mouseMovement": {"pathDistance": 0, "averageIntensity": 0, "peakIntensity": 0},
        "clickTiming": [],
        "uiInteractions": [],
        "windowChanges": [],
        "sceneChanges": [],
        "idleMoments": [],
        "fastMotion": [],
        "importantUiFocusAreas": [{"time": round(max(duration * 0.5, 0), 3), "x": 0.5, "y": 0.5, "sourceRect": _source_rect(0.5, 0.5, width, height), "reason": "fallback center focus", "score": 0.2}],
        "activeUiRegions": [],
        "uiImportanceDetection": {
            "activeWindows": [],
            "clickedButtons": [],
            "hoveredControls": [],
            "menusOpening": [],
            "modalDialogs": [],
            "loadingStates": [],
            "successErrorMessages": [],
            "textBlocks": [],
            "logoBrandAreas": [],
        },
        "ocrDrivenUiDetection": {
            "available": False,
            "engine": "tesseract",
            "reason": "Frame sampling failed before OCR could run.",
            "sampledFrames": [],
            "textBlocks": [],
            "keywords": [],
            "warnings": ["Showcase analysis fell back to center focus because frames could not be sampled."],
        },
        "cursorIntent": {"slowHover": [], "repeatedMovement": [], "actionPoints": [], "dragSequences": [], "idleCursor": []},
        "textHeavyMoments": [],
        "deadTimeRemoval": {"recommendedCuts": [], "strategy": "fallback keeps source footage intact"},
        "mistakeRemoval": {"recommendedRemovals": [], "detectors": [], "note": "fallback analysis"},
        "analysisTimeSeconds": round(time.perf_counter() - started, 3),
    }


def _write_report(report: dict[str, Any], output_path: Path | None) -> None:
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
