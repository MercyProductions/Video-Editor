from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from captions.engine import smart_caption_items
from clips.selector import select_highlights
from content.profiles import load_profile
from content.suggestions import suggest_scene_improvements
from content.thumbnails import generate_thumbnail_set
from intelligence.beat_sync import analyze_audio, apply_beat_sync
from metrics.store import metrics_from_project, record_metric
from parser.project_parser import ProjectParser
from preview.reporter import generate_preview
from renderer.renderer import VideoRenderer
from schema.validator import validate_project
from storyboard.generator import generate_storyboard
from styles.presets import apply_style, normalize_style


PRESET_SIZES = {
    "youtube_1080p": (1920, 1080, 60),
    "tiktok_reels": (1080, 1920, 60),
    "shorts": (1080, 1920, 60),
    "square": (1080, 1080, 30),
    "discord_720p": (1280, 720, 30),
    "cinematic_4k": (3840, 2160, 60),
}


def run_project_pipeline(
    *,
    prompt: str,
    clips_folder: Path,
    music_path: Path | None = None,
    style: str | None = None,
    preset: str | None = None,
    duration: float | None = None,
    output_dir: Path,
    profile: str | Path | None = None,
    render: bool = False,
    quality: str = "preview",
) -> dict[str, Any]:
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    brief = _content_brief(prompt, style=style, preset=preset, duration=duration)
    profile_data = load_profile(profile)
    selected_style = normalize_style(style or brief["style"])
    selected_preset = preset or profile_data.get("exportSettings", {}).get("preset") or brief["preset"]
    width, height, fps = PRESET_SIZES.get(selected_preset, PRESET_SIZES["youtube_1080p"])
    scene_duration = _scene_duration_for_style(selected_style, brief["duration"])

    clip_report_path = output_dir / "clip_selection.json"
    clip_selection = select_highlights(
        clips_folder,
        scene_duration=scene_duration,
        max_clips=max(4, int(brief["duration"] / scene_duration) + 2),
        output_path=clip_report_path,
    )
    project = _build_project(
        brief,
        clip_selection,
        clips_folder=clips_folder,
        music_path=music_path,
        style=selected_style,
        preset=selected_preset,
        width=width,
        height=height,
        fps=fps,
        profile=profile_data,
    )
    if music_path:
        try:
            analysis = analyze_audio(music_path, output_path=output_dir / "music_analysis.json")
            project.setdefault("metadata", {}).setdefault("pipeline", {})["beatAnalysis"] = analysis
            project = apply_beat_sync(project, analysis)
        except Exception as exc:
            project.setdefault("metadata", {}).setdefault("pipeline", {}).setdefault("warnings", []).append(f"Beat sync skipped: {exc}")
    project = apply_style(project, selected_style)
    project["metadata"]["pipeline"]["suggestions"] = suggest_scene_improvements(project)["suggestions"]

    project_path = output_dir / "project.json"
    validate_project(project)
    _write_json(project_path, project)

    parsed = ProjectParser().load(project_path)
    preview = generate_preview(parsed, output_dir=output_dir / "preview")
    storyboard = generate_storyboard(parsed, output_dir=output_dir / "storyboard")

    render_path: Path | None = None
    thumbnail_report: dict[str, Any] | None = None
    render_seconds: float | None = None
    if render:
        render_path = output_dir / "final_video.mp4"
        render_started = time.perf_counter()
        VideoRenderer(parsed, output_path=render_path, quality=quality, use_cache=True, resume=True, generate_placeholders=False).render()
        render_seconds = round(time.perf_counter() - render_started, 3)
        thumbnail_report = generate_thumbnail_set(render_path, title=brief["title"], output_dir=output_dir / "thumbnails", accent_color=brief["accentColor"])

    summary = {
        "prompt": prompt,
        "projectPath": str(project_path.resolve()),
        "renderPath": str(render_path.resolve()) if render_path else None,
        "clipSelectionPath": str(clip_report_path.resolve()),
        "previewSummaryPath": str(preview.summary_path),
        "renderPlanPath": str(preview.plan_path),
        "storyboardPath": storyboard.get("storyboardPath"),
        "thumbnailReportPath": thumbnail_report.get("reportPath") if thumbnail_report else None,
        "duration": project["project"]["duration"],
        "style": selected_style,
        "preset": selected_preset,
        "warnings": project["metadata"]["pipeline"].get("warnings", []),
        "suggestions": project["metadata"]["pipeline"].get("suggestions", []),
        "elapsedSeconds": round(time.perf_counter() - started, 3),
    }
    _write_json(output_dir / "pipeline_summary.json", summary)
    metric_data = {**metrics_from_project(project), "style": selected_style, "preset": selected_preset, "duration": project["project"]["duration"]}
    if render_path and render_path.exists():
        metric_data["outputSize"] = render_path.stat().st_size
        metric_data["renderSeconds"] = render_seconds
        record_metric(
            "render",
            {
                **metric_data,
                "project": str(project_path.resolve()),
                "output": str(render_path.resolve()),
                "quality": quality,
            },
        )
    record_metric("pipeline", metric_data)
    return summary


def run_batch_generation(
    *,
    prompt: str,
    clips_folder: Path,
    music_path: Path | None,
    styles: list[str],
    presets: list[str],
    versions: int,
    output_dir: Path,
    render: bool = False,
    quality: str = "preview",
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    styles = styles or ["clean_cinematic"]
    presets = presets or ["shorts"]
    for version in range(1, max(versions, 1) + 1):
        for style in styles:
            for preset in presets:
                run_dir = output_dir / f"v{version}_{normalize_style(style)}_{preset}"
                version_prompt = f"{prompt} Version {version}: {_variant_instruction(version)}"
                outputs.append(
                    run_project_pipeline(
                        prompt=version_prompt,
                        clips_folder=clips_folder,
                        music_path=music_path,
                        style=style,
                        preset=preset,
                        output_dir=run_dir,
                        render=render,
                        quality=quality,
                    )
                )
    report = {"prompt": prompt, "count": len(outputs), "outputs": outputs}
    _write_json(output_dir / "batch_summary.json", report)
    record_metric("batch", {"count": len(outputs), "styles": styles, "presets": presets})
    return report


def _build_project(
    brief: dict[str, Any],
    clip_selection: dict[str, Any],
    *,
    clips_folder: Path,
    music_path: Path | None,
    style: str,
    preset: str,
    width: int,
    height: int,
    fps: int,
    profile: dict[str, Any],
) -> dict[str, Any]:
    selected = clip_selection.get("selected") or clip_selection.get("clips") or []
    scene_duration = _scene_duration_for_style(style, brief["duration"])
    assets: dict[str, str] = {}
    if music_path:
        assets["music"] = str(music_path.resolve())
    timeline: list[dict[str, Any]] = []
    cursor = 0.0
    intro_duration = min(2.6, max(1.6, brief["duration"] * 0.12))
    timeline.append(_title_scene("hook", cursor, intro_duration, brief["hook"], width, height, style, brief["accentColor"]))
    cursor += intro_duration
    usable_duration = max(brief["duration"] - intro_duration - 2.4, 2.0)
    max_highlights = max(1, int(usable_duration / scene_duration))
    for index, clip in enumerate(selected[:max_highlights]):
        asset_key = f"clip_{index + 1}"
        assets[asset_key] = clip["path"]
        length = min(scene_duration, max(brief["duration"] - cursor - 2.2, 0.75))
        caption_text = brief["sceneCaptions"][index % len(brief["sceneCaptions"])]
        timeline.append(_highlight_scene(index + 1, cursor, length, clip, asset_key, caption_text, width, height, style, profile))
        cursor += length
        if cursor >= brief["duration"] - 2.1:
            break
    outro_duration = max(1.8, min(2.8, brief["duration"] - cursor))
    if outro_duration > 0.5:
        timeline.append(_title_scene("outro", cursor, outro_duration, brief["cta"], width, height, style, brief["accentColor"], outro=True))
        cursor += outro_duration
    _retime_transitions(timeline)
    project = {
        "metadata": {
            "pipeline": {
                "prompt": brief["prompt"],
                "title": brief["title"],
                "hook": brief["hook"],
                "script": brief["script"],
                "clipsFolder": str(clips_folder.resolve()),
                "clipSelection": clip_selection,
                "profile": profile.get("name"),
            },
            "stylePreset": style,
        },
        "exportPreset": preset,
        "stylePreset": style,
        "project": {"width": width, "height": height, "fps": fps, "duration": round(cursor, 3), "background": brief["background"]},
        "assets": assets,
        "timeline": timeline,
        "audio": [],
    }
    if music_path:
        music = profile.get("preferredMusicBehavior", {})
        project["audio"].append(
            {
                "asset": "music",
                "start": 0,
                "volume": float(music.get("volume", 0.42)),
                "fadeIn": float(music.get("fadeIn", 0.2)),
                "fadeOut": float(music.get("fadeOut", 1.0)),
                "loop": bool(music.get("loop", True)),
            }
        )
    return project


def _highlight_scene(
    index: int,
    start: float,
    duration: float,
    clip: dict[str, Any],
    asset_key: str,
    caption_text: str,
    width: int,
    height: int,
    style: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    caption_items = smart_caption_items(caption_text, duration=duration, max_words=6)
    caption_style = profile.get("captionStyle", {})
    transition = {"type": "zoom" if style in {"gaming_montage", "red_black_aegis"} else "crossfade", "duration": 0.28}
    return {
        "id": f"highlight_{index}",
        "start": round(start, 3),
        "duration": round(duration, 3),
        "layers": [
            {
                "type": "video",
                "asset": asset_key,
                "x": 0,
                "y": 0,
                "width": width,
                "height": height,
                "trimStart": float(clip.get("highlightStart", 0) or 0),
                "trimEnd": round(float(clip.get("highlightStart", 0) or 0) + duration, 3),
                "contrast": 1.12,
                "animation": {"in": "zoomIn", "duration": 0.35} if style in {"gaming_montage", "red_black_aegis"} else {"in": "fade", "duration": 0.2},
            },
            {
                "type": "caption",
                "layout": "lower_third",
                "x": "center",
                "y": int(height * 0.78),
                **caption_style,
                "items": caption_items,
            },
        ],
        "transitionOut": transition,
        "analysis": {
            "highlightReason": clip.get("highlightReason"),
            "tags": clip.get("tags", []),
            "highlightScore": clip.get("highlightScore"),
        },
    }


def _title_scene(
    scene_id: str,
    start: float,
    duration: float,
    text: str,
    width: int,
    height: int,
    style: str,
    accent: str,
    *,
    outro: bool = False,
) -> dict[str, Any]:
    return {
        "id": scene_id,
        "start": round(start, 3),
        "duration": round(duration, 3),
        "layers": [
            {
                "type": "text",
                "text": text,
                "x": "center",
                "y": "center" if not outro else int(height * 0.42),
                "fontSize": 82 if height >= 1600 else 72,
                "color": "#ffffff" if style != "red_black_aegis" else accent,
                "strokeColor": "#000000",
                "strokeWidth": 4,
                "box": True,
                "boxColor": "#000000aa",
                "boxPadding": 22,
                "animation": {"in": "typewriter", "out": "fade", "duration": 0.55},
            }
        ],
        "transitionOut": {"type": "zoom" if style in {"gaming_montage", "red_black_aegis"} else "crossfade", "duration": 0.35},
    }


def _content_brief(prompt: str, *, style: str | None, preset: str | None, duration: float | None) -> dict[str, Any]:
    lower = prompt.lower()
    selected_style = style or _style_from_prompt(lower)
    selected_preset = preset or ("shorts" if any(word in lower for word in ["short", "tiktok", "reels", "vertical"]) else "youtube_1080p")
    target_duration = duration or _duration_from_prompt(lower) or (45 if selected_preset in {"shorts", "tiktok_reels"} else 30)
    subject = _subject_from_prompt(prompt)
    title = _title_from_subject(subject)
    hook = _hook_for_prompt(subject, lower)
    features = _features_from_prompt(prompt)
    scene_captions = [
        f"{feature} gets a clean cinematic highlight." for feature in features[:4]
    ] or [f"Watch {subject} move from raw footage to polished edit."]
    script = [hook, *scene_captions, f"{subject} is ready to show."]
    return {
        "prompt": prompt,
        "subject": subject,
        "title": title,
        "hook": hook,
        "script": script,
        "sceneCaptions": scene_captions,
        "cta": f"Try {subject} today.",
        "style": selected_style,
        "preset": selected_preset,
        "duration": float(target_duration),
        "accentColor": "#ef4444" if "red" in lower or "cyber" in lower else "#f5d46b" if "luxury" in lower else "#6db5a5",
        "background": "#050000" if "red" in lower or "cyber" in lower else "#05070d",
    }


def _style_from_prompt(lower: str) -> str:
    if any(word in lower for word in ["gaming", "kill", "montage"]):
        return "gaming_montage"
    if any(word in lower for word in ["red", "cyber", "security", "hacker"]):
        return "red_black_aegis"
    if "luxury" in lower or "premium" in lower:
        return "luxury_promo"
    if "minimal" in lower or "clean" in lower:
        return "minimal_tech"
    return "clean_cinematic"


def _duration_from_prompt(lower: str) -> float | None:
    import re

    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:sec|second|seconds|s)\b", lower)
    if match:
        return max(6.0, min(90.0, float(match.group(1))))
    return None


def _subject_from_prompt(prompt: str) -> str:
    cleaned = prompt.strip().strip('"')
    if not cleaned:
        return "the project"
    for marker in [" for ", " about ", " showcasing ", " showcase "]:
        if marker in cleaned.lower():
            part = cleaned.lower().split(marker, 1)[1]
            return part.split(".")[0][:54].strip() or "the project"
    return cleaned[:54]


def _title_from_subject(subject: str) -> str:
    title = " ".join(word.capitalize() for word in subject.replace("_", " ").split()[:6])
    return title or "Auto Showcase"


def _hook_for_prompt(subject: str, lower: str) -> str:
    if "troubleshooter" in lower:
        return "Stop guessing why apps fail."
    if "security" in lower or "cyber" in lower:
        return "Your system check just got cinematic."
    if "gaming" in lower:
        return "These are the moments worth replaying."
    return f"Here is {subject} in motion."


def _features_from_prompt(prompt: str) -> list[str]:
    cleaned = prompt.replace(" and ", ", ")
    parts = [part.strip(" .") for part in cleaned.split(",") if 3 <= len(part.strip()) <= 80]
    return parts[1:6] if len(parts) > 1 else parts[:4]


def _scene_duration_for_style(style: str, duration: float) -> float:
    if style == "gaming_montage":
        return 1.8 if duration <= 30 else 2.4
    if style == "minimal_tech":
        return 3.4
    if style == "luxury_promo":
        return 3.2
    return 2.6


def _retime_transitions(timeline: list[dict[str, Any]]) -> None:
    for index, scene in enumerate(timeline):
        if index == len(timeline) - 1:
            scene.pop("transitionOut", None)
        else:
            transition = scene.get("transitionOut", {})
            transition["duration"] = min(float(transition.get("duration", 0.3)), max(float(scene["duration"]) * 0.35, 0.05))
            scene["transitionOut"] = transition


def _variant_instruction(version: int) -> str:
    variants = {
        1: "balanced pacing",
        2: "stronger hook and faster cuts",
        3: "cleaner captions and softer transitions",
        4: "more cinematic title cards",
    }
    return variants.get(version, "alternate pacing")


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
