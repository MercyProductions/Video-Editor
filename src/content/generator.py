from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from captions.engine import smart_caption_items
from clips.selector import select_highlights
from content.review import (
    apply_review_locks,
    build_ai_reasoning,
    build_generation_review,
    compare_content_versions,
    set_review_status,
    write_review_outputs,
)
from intelligence.beat_sync import analyze_audio
from media.compat import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from parser.project_parser import ProjectParser
from preview.reporter import generate_preview
from renderer.renderer import VideoRenderer
from repair.repairer import repair_project_data
from schema.validator import ProjectValidationError, validate_project
from styles.presets import apply_style, list_styles, normalize_style


MODES = {"youtube_shorts", "tiktok", "product_showcase", "tutorial", "promo_ad"}
TONES = {"minimal", "cinematic", "aggressive", "clean"}

MODE_DEFAULTS: dict[str, dict[str, Any]] = {
    "youtube_shorts": {
        "platform": "shorts",
        "duration": 35.0,
        "minDuration": 15.0,
        "maxDuration": 60.0,
        "pacing": "fast",
        "sections": [("hook", 0.12), ("problem", 0.18), ("feature", 0.45), ("result", 0.15), ("cta", 0.10)],
    },
    "tiktok": {
        "platform": "tiktok",
        "duration": 24.0,
        "minDuration": 10.0,
        "maxDuration": 60.0,
        "pacing": "trend_fast",
        "sections": [("hook", 0.14), ("setup", 0.18), ("feature", 0.44), ("payoff", 0.14), ("cta", 0.10)],
    },
    "product_showcase": {
        "platform": "shorts",
        "duration": 35.0,
        "minDuration": 12.0,
        "maxDuration": 75.0,
        "pacing": "cinematic",
        "sections": [("intro", 0.16), ("feature", 0.54), ("result", 0.18), ("cta", 0.12)],
    },
    "tutorial": {
        "platform": "shorts",
        "duration": 45.0,
        "minDuration": 20.0,
        "maxDuration": 90.0,
        "pacing": "clear_steps",
        "sections": [("intro", 0.12), ("step", 0.68), ("recap", 0.12), ("cta", 0.08)],
    },
    "promo_ad": {
        "platform": "shorts",
        "duration": 30.0,
        "minDuration": 12.0,
        "maxDuration": 60.0,
        "pacing": "benefit_driven",
        "sections": [("hook", 0.16), ("problem", 0.20), ("solution", 0.42), ("benefit", 0.14), ("cta", 0.08)],
    },
}

PLATFORMS: dict[str, dict[str, Any]] = {
    "shorts": {"preset": "shorts", "width": 1080, "height": 1920, "fps": 60},
    "youtube_shorts": {"preset": "shorts", "width": 1080, "height": 1920, "fps": 60},
    "tiktok": {"preset": "tiktok_reels", "width": 1080, "height": 1920, "fps": 60},
    "reels": {"preset": "tiktok_reels", "width": 1080, "height": 1920, "fps": 60},
    "instagram_reels": {"preset": "tiktok_reels", "width": 1080, "height": 1920, "fps": 60},
    "instagram": {"preset": "instagram_reels", "width": 1080, "height": 1920, "fps": 60},
    "youtube": {"preset": "youtube_1080p", "width": 1920, "height": 1080, "fps": 60},
    "youtube_landscape": {"preset": "youtube_1080p", "width": 1920, "height": 1080, "fps": 60},
    "landscape": {"preset": "youtube_1080p", "width": 1920, "height": 1080, "fps": 60},
    "square": {"preset": "square", "width": 1080, "height": 1080, "fps": 30},
}

def run_content_generator(
    *,
    idea: str,
    output_dir: Path,
    mode: str = "youtube_shorts",
    product_name: str | None = None,
    target_platform: str | None = None,
    goal: str | None = None,
    bullet_points: list[str] | None = None,
    assets_folder: Path | None = None,
    music_path: Path | None = None,
    logo_path: Path | None = None,
    duration: float | None = None,
    tone: str = "cinematic",
    style: str | None = None,
    existing_plan_path: Path | None = None,
    regenerate: str = "full",
    locks: list[str] | None = None,
    approved: bool = False,
    render: bool = False,
    quality: str = "preview",
    cache: bool = True,
    gpu: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    clean_mode = _normalize_mode(mode)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    locks = locks or []

    previous = _read_existing_plan(existing_plan_path)
    brief = create_content_brief(
        idea,
        mode=clean_mode,
        product_name=product_name,
        target_platform=target_platform,
        goal=goal,
        bullet_points=bullet_points or [],
        duration=duration,
        tone=tone,
        style=style,
    )
    script = create_script(brief)
    scene_plan = create_scene_plan(brief, script)
    plan = create_generation_plan(brief, script, scene_plan, music_path=music_path, logo_path=logo_path)
    plan = _merge_locked_plan(plan, previous, regenerate=regenerate, locks=locks)

    clip_report = _select_media(
        assets_folder,
        output_dir=output_dir,
        scene_duration=_media_scene_duration(plan),
        max_clips=max(1, _media_scene_count(plan)),
    )
    plan.setdefault("warnings", []).extend(clip_report.get("warnings", []))
    music_analysis = _analyze_music(music_path, output_dir=output_dir)
    if music_analysis:
        plan.setdefault("warnings", []).extend(music_analysis.get("warnings", []))
        plan["editingStyle"]["musicSync"] = {
            "enabled": True,
            "bpm": music_analysis.get("bpm"),
            "beats": music_analysis.get("beats", [])[:24],
            "bassDrops": music_analysis.get("bassDrops", [])[:8],
        }
    project = build_project_from_plan(plan, clip_report, music_path=music_path, logo_path=logo_path)
    project, repair_report = _validate_or_repair(project)
    plan.setdefault("warnings", []).extend(repair_report.get("warnings", []))
    plan["reasoning"] = build_ai_reasoning(plan, project)
    review = build_generation_review(plan, project)
    review = apply_review_locks(review, locks)
    if approved:
        review = set_review_status(review, "all", "approved")
    plan["approval"] = review

    comparison = None
    if previous:
        comparison = compare_content_versions(previous, plan, next_project=project)

    paths = _write_generation_outputs(output_dir, brief, script, scene_plan, plan, project, comparison=comparison)
    parsed = ProjectParser().load(paths["project"])
    preview = generate_preview(parsed, output_dir=output_dir / "preview")

    render_path: Path | None = None
    if render:
        readiness = plan.get("approval", {}).get("readiness", {})
        if quality == "final" and not readiness.get("readyForFinalRender"):
            unresolved = ", ".join(readiness.get("unresolvedSections", [])[:8])
            raise RuntimeError(
                "Final render blocked until generated sections are approved. "
                f"Unresolved sections: {unresolved or 'unknown'}"
            )
        render_path = output_dir / "final_video.mp4"
        VideoRenderer(parsed, output_path=render_path, quality=quality, use_cache=cache, resume=cache, gpu=gpu).render()

    summary = {
        "mode": clean_mode,
        "productName": plan["contentBrief"]["productName"],
        "targetPlatform": plan["contentBrief"]["targetPlatform"],
        "hook": plan["hook"],
        "style": plan["editingStyle"]["stylePreset"],
        "tone": plan["editingStyle"]["tone"],
        "duration": plan["duration"],
        "projectPath": str(paths["project"]),
        "contentBriefPath": str(paths["brief"]),
        "scriptPath": str(paths["script"]),
        "scenePlanPath": str(paths["scene_plan"]),
        "contentPlanPath": str(paths["plan"]),
        "reviewSummaryPath": str(paths["review"]),
        "generationReviewPath": str(paths["generation_review"]),
        "approvalStatePath": str(paths["approval_state"]),
        "aiReasoningPath": str(paths["ai_reasoning"]),
        "versionComparisonPath": str(paths.get("version_comparison")) if paths.get("version_comparison") else None,
        "approvalReady": plan.get("approval", {}).get("readiness", {}).get("readyForFinalRender", False),
        "unresolvedReviewSections": plan.get("approval", {}).get("readiness", {}).get("unresolvedSections", []),
        "previewSummaryPath": str(preview.summary_path),
        "renderPlanPath": str(preview.plan_path),
        "renderPath": str(render_path) if render_path else None,
        "regenerate": regenerate,
        "locks": locks,
        "warnings": plan.get("warnings", []),
        "elapsedSeconds": round(time.perf_counter() - started, 3),
    }
    _write_json(output_dir / "content_generation_summary.json", summary)
    return summary


def create_content_brief(
    idea: str,
    *,
    mode: str,
    product_name: str | None,
    target_platform: str | None,
    goal: str | None,
    bullet_points: list[str],
    duration: float | None,
    tone: str,
    style: str | None,
) -> dict[str, Any]:
    defaults = MODE_DEFAULTS[mode]
    clean_tone = tone if tone in TONES else "cinematic"
    platform = _platform(target_platform or defaults["platform"])
    target_duration = _duration(idea, duration, defaults)
    product = product_name or _product_name(idea)
    bullets = _features(idea, bullet_points)
    selected_style = _style_for(mode, clean_tone, style, idea)
    goal_text = goal or _goal_for(mode, product)
    theme = _theme(selected_style, clean_tone, idea)
    return {
        "mode": mode,
        "idea": idea,
        "productName": product,
        "targetPlatform": platform["key"],
        "exportPreset": platform["preset"],
        "width": platform["width"],
        "height": platform["height"],
        "fps": platform["fps"],
        "goal": goal_text,
        "bulletPoints": bullets,
        "duration": target_duration,
        "tone": clean_tone,
        "stylePreset": selected_style,
        "theme": theme,
        "pacing": defaults["pacing"],
        "concept": _concept(mode, product, goal_text, clean_tone),
    }


def create_script(brief: dict[str, Any]) -> dict[str, Any]:
    mode = brief["mode"]
    product = brief["productName"]
    features = brief["bulletPoints"]
    hook = _hook(mode, product, features, brief["idea"])
    cta = _cta(mode, product)
    if mode == "tutorial":
        lines = [hook, *[f"Step {index + 1}: {_sentence(feature)}." for index, feature in enumerate(features[:5])], f"Now {product} feels easier to use.", cta]
    elif mode == "product_showcase":
        lines = [hook, *[f"{_sentence(feature)} gets a clean reveal." for feature in features[:5]], f"{product} turns the workflow into a polished experience.", cta]
    elif mode == "promo_ad":
        lines = [hook, _problem(product, features), f"{product} gives you the fix path faster.", *[_benefit(feature) for feature in features[:3]], cta]
    elif mode == "tiktok":
        lines = [hook, "Here is the quick version.", *[f"{_sentence(feature)}. Done fast." for feature in features[:4]], cta]
    else:
        lines = [hook, _problem(product, features), *[f"{_sentence(feature)} is scanned, shown, and explained." for feature in features[:4]], _payoff(product, features), cta]
    return {
        "hook": hook,
        "lines": [_fit_caption(line) for line in lines],
        "cta": cta,
        "captionStyle": _caption_style(brief),
    }


def create_scene_plan(brief: dict[str, Any], script: dict[str, Any]) -> list[dict[str, Any]]:
    timings = _timings(brief)
    features = brief["bulletPoints"]
    scenes: list[dict[str, Any]] = []
    if brief["mode"] == "tutorial":
        scenes.append(_scene("intro", "hook", timings["intro"], "Start Here", script["hook"], "title_card"))
        scenes.extend(_split_section("step", timings["step"], features, "Tutorial Step", lambda feature: f"Step: {_sentence(feature)}."))
        scenes.append(_scene("recap", "result", timings["recap"], "Clean Finish", _payoff(brief["productName"], features), "title_card"))
        scenes.append(_scene("cta", "cta", timings["cta"], brief["productName"], script["cta"], "title_card"))
    elif brief["mode"] == "product_showcase":
        timings = _showcase_timings(brief, features)
        scenes.append(_scene("intro", "hook", timings["intro"], brief["productName"], script["hook"], "title_card"))
        scenes.extend(_split_section("feature", timings["feature"], features, "Feature Reveal", lambda feature: f"{_sentence(feature)} gets the spotlight."))
        scenes.append(_scene("result", "result", timings["result"], "The Payoff", _payoff(brief["productName"], features), "media"))
        scenes.append(_scene("cta", "cta", timings["cta"], brief["productName"], script["cta"], "title_card"))
    elif brief["mode"] == "promo_ad":
        scenes.append(_scene("hook", "hook", timings["hook"], "Problem?", script["hook"], "title_card"))
        scenes.append(_scene("problem", "problem", timings["problem"], "The Blocker", _problem(brief["productName"], features), "title_card"))
        scenes.extend(_split_section("solution", timings["solution"], features, "Solution", lambda feature: f"{_sentence(feature)} becomes easier to act on."))
        scenes.append(_scene("benefit", "result", timings["benefit"], "The Result", _payoff(brief["productName"], features), "title_card"))
        scenes.append(_scene("cta", "cta", timings["cta"], brief["productName"], script["cta"], "title_card"))
    elif brief["mode"] == "tiktok":
        scenes.append(_scene("hook", "hook", timings["hook"], "Wait for it", script["hook"], "title_card"))
        scenes.append(_scene("setup", "problem", timings["setup"], "The Issue", _problem(brief["productName"], features), "title_card"))
        scenes.extend(_split_section("feature", timings["feature"], features, "Quick Hit", lambda feature: f"{_sentence(feature)}. Fast."))
        scenes.append(_scene("payoff", "result", timings["payoff"], "Payoff", _payoff(brief["productName"], features), "title_card"))
        scenes.append(_scene("cta", "cta", timings["cta"], brief["productName"], script["cta"], "title_card"))
    else:
        scenes.append(_scene("hook", "hook", timings["hook"], "Stop Scrolling", script["hook"], "title_card"))
        scenes.append(_scene("problem", "problem", timings["problem"], "The Problem", _problem(brief["productName"], features), "title_card"))
        scenes.extend(_split_section("feature", timings["feature"], features, "Feature", lambda feature: f"{_sentence(feature)} is highlighted clearly."))
        scenes.append(_scene("result", "result", timings["result"], "Result", _payoff(brief["productName"], features), "title_card"))
        scenes.append(_scene("cta", "cta", timings["cta"], brief["productName"], script["cta"], "title_card"))
    return _retime_scene_ids(scenes)


def create_generation_plan(
    brief: dict[str, Any],
    script: dict[str, Any],
    scene_plan: list[dict[str, Any]],
    *,
    music_path: Path | None,
    logo_path: Path | None,
) -> dict[str, Any]:
    captions = [{"sceneId": scene["id"], "text": scene["caption"], "start": scene["start"], "duration": scene["duration"]} for scene in scene_plan]
    overlays = [{"sceneId": scene["id"], "text": scene["title"], "role": scene["role"], "start": scene["start"], "duration": scene["duration"]} for scene in scene_plan]
    visual_directions = [_visual_direction(brief, scene) for scene in scene_plan]
    return {
        "contentPlanVersion": 1,
        "contentBrief": brief,
        "concept": brief["concept"],
        "hook": script["hook"],
        "script": script,
        "scenePlan": scene_plan,
        "captions": captions,
        "textOverlays": overlays,
        "visualDirections": visual_directions,
        "editingStyle": {
            "stylePreset": brief["stylePreset"],
            "tone": brief["tone"],
            "pacing": brief["pacing"],
            "captionStyle": script["captionStyle"],
            "background": brief["theme"]["background"],
            "accent": brief["theme"]["accent"],
            "secondary": brief["theme"]["secondary"],
            "transitionType": _transition_type(brief),
            "musicSync": {"enabled": bool(music_path)},
            "logo": str(logo_path.resolve()) if logo_path else None,
        },
        "duration": brief["duration"],
        "warnings": [],
        "reviewSummary": {
            "mustReview": ["Hook", "Script", "Scene timing", "Captions", "CTA", "Asset relevance"],
            "lockedSections": [],
        },
    }


def build_project_from_plan(
    plan: dict[str, Any],
    clip_report: dict[str, Any],
    *,
    music_path: Path | None,
    logo_path: Path | None,
) -> dict[str, Any]:
    brief = plan["contentBrief"]
    width = int(brief["width"])
    height = int(brief["height"])
    style = plan["editingStyle"]["stylePreset"]
    assets: dict[str, str] = {}
    selected_clips = clip_report.get("selected", [])
    images = clip_report.get("images", [])
    for index, clip in enumerate(selected_clips, start=1):
        assets[f"clip_{index}"] = str(Path(clip["path"]).resolve())
    for index, image in enumerate(images, start=1):
        assets[f"image_{index}"] = str(Path(image).resolve())
    if music_path:
        assets["music"] = str(music_path.resolve())
    if logo_path:
        assets["logo"] = str(logo_path.resolve())

    scenes = []
    media_index = 0
    for scene in plan["scenePlan"]:
        media_key: str | None = None
        media_type: str | None = None
        clip: dict[str, Any] | None = None
        if selected_clips:
            clip = selected_clips[media_index % len(selected_clips)]
            media_key = f"clip_{media_index % len(selected_clips) + 1}"
            media_type = "video"
        elif images:
            media_key = f"image_{media_index % len(images) + 1}"
            media_type = "image"
        if scene.get("mediaRole") != "title_card":
            media_index += 1
        scenes.append(_project_scene(scene, plan, media_key=media_key, media_type=media_type, clip=clip, width=width, height=height))
    scenes[-1].pop("transitionOut", None)

    project = {
        "metadata": {
            "contentGenerator": {
                "mode": brief["mode"],
                "contentBrief": brief,
                "script": plan["script"],
                "scenePlan": plan["scenePlan"],
                "captions": plan["captions"],
                "textOverlays": plan["textOverlays"],
                "visualDirections": plan["visualDirections"],
                "reviewSummary": plan["reviewSummary"],
                "warnings": plan.get("warnings", []),
            },
            "stylePreset": style,
        },
        "exportPreset": brief["exportPreset"],
        "stylePreset": style,
        "project": {
            "width": width,
            "height": height,
            "fps": int(brief["fps"]),
            "duration": plan["duration"],
            "background": plan["editingStyle"]["background"],
            "crf": 19 if brief["exportPreset"] in {"shorts", "tiktok_reels"} else 18,
        },
        "assets": assets,
        "timeline": scenes,
        "audio": [],
    }
    if music_path:
        project["audio"].append({"asset": "music", "start": 0, "volume": 0.42, "fadeIn": 0.25, "fadeOut": 1.2, "loop": True})
    styled = apply_style(project, style)
    _apply_music_sync(styled["timeline"], plan["editingStyle"].get("musicSync", {}))
    styled["timeline"][-1].pop("transitionOut", None)
    return styled


def _project_scene(
    scene: dict[str, Any],
    plan: dict[str, Any],
    *,
    media_key: str | None,
    media_type: str | None,
    clip: dict[str, Any] | None,
    width: int,
    height: int,
) -> dict[str, Any]:
    style = plan["editingStyle"]
    duration = float(scene["duration"])
    layers: list[dict[str, Any]] = []
    is_title = scene.get("mediaRole") == "title_card"
    if not is_title and media_key and media_type:
        layer = {
            "type": media_type,
            "asset": media_key,
            "x": 0,
            "y": 0,
            "width": width,
            "height": height,
            "fit": "cover",
            "contrast": 1.04,
            "brightness": 0.015,
            "camera": _camera_for(style, scene),
            "animation": {"in": "zoomIn", "out": "fade", "duration": 0.25},
        }
        if media_type == "video":
            trim_start = float((clip or {}).get("highlightStart", 0) or 0)
            source_duration = float((clip or {}).get("duration", 0) or 0)
            if source_duration > 0:
                trim_start = min(trim_start, max(source_duration - duration, 0))
            layer["trimStart"] = trim_start
            layer["trimEnd"] = round(trim_start + duration, 3)
        layers.append(layer)
        layers.append({"type": "shape", "x": 0, "y": 0, "width": width, "height": height, "color": "#000000", "opacity": 0.07})
    else:
        layers.append({"type": "animated_background", "color": style["accent"], "opacity": 0.12, "speed": 100, "start": 0, "duration": duration})
        layers.append({"type": "particle", "color": style["secondary"], "opacity": 0.22, "count": 22, "start": 0, "duration": duration})
    if plan["editingStyle"].get("logo") and scene["section"] in {"hook", "intro", "cta"}:
        size = int(min(width, height) * 0.14)
        layers.append({"type": "image", "asset": "logo", "x": "center", "y": int(height * 0.09), "width": size, "height": size, "fit": "contain", "animation": {"in": "fade", "out": "fade", "duration": 0.3}})
    if is_title:
        layers.append(_title_text_layer(scene, style, width, height))
    else:
        layers.append(_lower_third_layer(scene, style, width, height))
    layers.append(_caption_layer(scene["caption"], duration, style, width, height))
    layers.append(_progress_layer(style, duration, width, height))
    return {
        "id": scene["id"],
        "start": scene["start"],
        "duration": duration,
        "layers": layers,
        "transitionOut": _transition(style),
        "effectGraphPreset": _effect_preset(style["stylePreset"]),
        "analysis": {"source": "content_generator", "section": scene["section"], "visualDirection": scene.get("visualDirection")},
    }


def _title_text_layer(scene: dict[str, Any], style: dict[str, Any], width: int, height: int) -> dict[str, Any]:
    return {
        "type": "text",
        "text": scene["title"],
        "x": "center",
        "y": "center",
        "fontSize": 82 if height >= width else 68,
        "color": "#ffffff",
        "strokeColor": "#000000",
        "strokeWidth": 4,
        "box": True,
        "boxColor": "#00000099",
        "boxPadding": 22,
        "lineSpacing": 12,
        "animation": {"in": "typewriter", "out": "fade", "duration": 0.45},
    }


def _lower_third_layer(scene: dict[str, Any], style: dict[str, Any], width: int, height: int) -> dict[str, Any]:
    vertical = height > width
    return {
        "type": "lower_third",
        "title": scene["title"],
        "subtitle": scene["role"],
        "x": int(width * 0.065),
        "y": int(height * (0.10 if vertical else 0.08)),
        "width": int(width * 0.87),
        "height": 138 if vertical else 118,
        "fontSize": 52 if vertical else 44,
        "subtitleSize": 30 if vertical else 26,
        "boxColor": "#050000cc" if style["stylePreset"] == "red_black_aegis" else "#05070dcc",
        "color": style["accent"],
        "subtitleColor": "#e5e7eb",
        "start": 0.12,
        "duration": max(float(scene["duration"]) - 0.24, 0.5),
    }


def _caption_layer(text: str, duration: float, style: dict[str, Any], width: int, height: int) -> dict[str, Any]:
    vertical = height > width
    return {
        "type": "caption",
        "layout": "lower_third",
        "x": "center",
        "y": int(height * (0.72 if vertical else 0.76)),
        "fontSize": 58 if vertical else 44,
        "color": "#ffffff",
        "strokeColor": "#000000",
        "strokeWidth": 5 if vertical else 3,
        "box": True,
        "boxColor": "#000000b5",
        "boxPadding": 18 if vertical else 14,
        "captionMode": "smart",
        "safeZone": "title",
        "animation": {"in": "slideUp", "out": "fade", "duration": 0.18},
        "items": _caption_items(
            text,
            duration=max(duration - 0.35, 1.0),
            accent=style["accent"],
            max_words=5 if vertical else 7,
        ),
        "highlightColor": style["accent"],
    }


def _caption_items(text: str, *, duration: float, accent: str, max_words: int) -> list[dict[str, Any]]:
    items = smart_caption_items(text, duration=duration, max_words=max_words)
    for item in items:
        item["highlightColor"] = accent
    return items


def _progress_layer(style: dict[str, Any], duration: float, width: int, height: int) -> dict[str, Any]:
    return {
        "type": "progress",
        "x": "center",
        "y": int(height * 0.94),
        "width": int(width * 0.68),
        "height": max(8, int(height * 0.005)),
        "color": style["accent"],
        "backgroundColor": "#ffffff33",
        "opacity": 0.85,
        "start": 0,
        "duration": duration,
    }


def _timings(brief: dict[str, Any]) -> dict[str, dict[str, float]]:
    sections = MODE_DEFAULTS[brief["mode"]]["sections"]
    cursor = 0.0
    timings: dict[str, dict[str, float]] = {}
    for index, (name, weight) in enumerate(sections):
        end = brief["duration"] if index == len(sections) - 1 else cursor + brief["duration"] * weight
        timings[name] = {"start": round(cursor, 3), "end": round(end, 3), "duration": round(max(end - cursor, 0.2), 3)}
        cursor = end
    return timings


def _showcase_timings(brief: dict[str, Any], features: list[str]) -> dict[str, dict[str, float]]:
    total = float(brief["duration"])
    intro = min(3.5, max(1.4, total * 0.10))
    cta = min(3.5, max(1.2, total * 0.08))
    result = min(6.0, max(1.6, total * 0.12))
    reserved = intro + result + cta
    max_reserved = max(total * 0.42, min(total - 0.8, reserved))
    if reserved > max_reserved and reserved > 0:
        scale = max_reserved / reserved
        intro = max(0.8, intro * scale)
        cta = max(0.8, cta * scale)
        result = max(0.8, result * scale)
    feature = max(total - intro - result - cta, 0.8)
    cursor = 0.0
    timings = {
        "intro": {"start": cursor, "end": cursor + intro, "duration": intro},
    }
    cursor += intro
    timings["feature"] = {"start": cursor, "end": cursor + feature, "duration": feature}
    cursor += feature
    timings["result"] = {"start": cursor, "end": cursor + result, "duration": result}
    cursor += result
    timings["cta"] = {"start": cursor, "end": total, "duration": max(total - cursor, 0.6)}
    return {
        key: {inner_key: round(inner_value, 3) for inner_key, inner_value in value.items()}
        for key, value in timings.items()
    }


def _split_section(prefix: str, timing: dict[str, float], features: list[str], role: str, caption_fn: Any) -> list[dict[str, Any]]:
    clean = features[:5] or ["Clear value", "Simple workflow", "Fast result"]
    scene_count = max(len(clean), min(10, int((timing["duration"] + 5.999) // 6)))
    duration = timing["duration"] / scene_count
    scenes = []
    for index in range(scene_count):
        feature = clean[index % len(clean)]
        start = round(timing["start"] + index * duration, 3)
        end = round(timing["start"] + (index + 1) * duration, 3)
        scenes.append(_scene(f"{prefix}_{index + 1}", prefix, {"start": start, "end": end, "duration": round(end - start, 3)}, _fit_title(feature), caption_fn(feature), "media", role=role))
    return scenes


def _scene(scene_id: str, section: str, timing: dict[str, float], title: str, caption: str, media_role: str, *, role: str | None = None) -> dict[str, Any]:
    return {
        "id": scene_id,
        "section": section,
        "role": role or section.replace("_", " ").title(),
        "start": timing["start"],
        "end": timing["end"],
        "duration": timing["duration"],
        "title": _fit_title(title),
        "caption": _fit_caption(caption),
        "mediaRole": media_role,
        "visualDirection": "",
    }


def _retime_scene_ids(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, int] = {}
    for scene in scenes:
        base = re.sub(r"[^a-z0-9_]+", "_", scene["id"].lower()).strip("_") or "scene"
        seen[base] = seen.get(base, 0) + 1
        scene["id"] = base if seen[base] == 1 else f"{base}_{seen[base]}"
    return scenes


def _merge_locked_plan(plan: dict[str, Any], previous: dict[str, Any] | None, *, regenerate: str, locks: list[str]) -> dict[str, Any]:
    locked = {item.strip() for item in locks if item.strip()}
    if not previous:
        if locks:
            plan.setdefault("warnings", []).append("Locks were provided but no existing plan was supplied.")
            plan["reviewSummary"]["lockedSections"] = sorted(locked)
        return plan
    target = regenerate.strip().lower().replace("-", "_")
    if target == "scene_plan":
        target = "scenes"
    if target in {"none", "approved", "existing"}:
        plan = json.loads(json.dumps(previous))
    if target in {"hook", "captions", "style", "script", "scenes"}:
        base = json.loads(json.dumps(previous))
        base.setdefault("contentBrief", plan.get("contentBrief", {}))
        base.setdefault("reviewSummary", plan.get("reviewSummary", {}))
        base["warnings"] = list(plan.get("warnings", []))
        if target == "hook":
            base["hook"] = plan.get("hook", base.get("hook", ""))
            base.setdefault("script", {}).setdefault("lines", [])
            if plan.get("script", {}).get("lines"):
                if base["script"]["lines"]:
                    base["script"]["lines"][0] = plan["script"]["lines"][0]
                else:
                    base["script"]["lines"].append(plan["script"]["lines"][0])
            base["script"]["hook"] = plan.get("hook", base.get("hook", ""))
        elif target == "captions":
            _replace_caption_text(base, plan)
        elif target == "style":
            base["editingStyle"] = plan.get("editingStyle", base.get("editingStyle", {}))
            base["contentBrief"]["stylePreset"] = plan.get("contentBrief", {}).get("stylePreset", base["contentBrief"].get("stylePreset"))
            base["contentBrief"]["tone"] = plan.get("contentBrief", {}).get("tone", base["contentBrief"].get("tone"))
            base["contentBrief"]["theme"] = plan.get("contentBrief", {}).get("theme", base["contentBrief"].get("theme"))
        elif target == "script":
            base["script"] = plan.get("script", base.get("script", {}))
            base["hook"] = plan.get("hook", base.get("hook", ""))
        elif target == "scenes":
            base["scenePlan"] = plan.get("scenePlan", base.get("scenePlan", []))
            base["duration"] = plan.get("duration", base.get("duration"))
        plan = base
    _apply_section_locks(plan, previous, locked)
    plan["reviewSummary"]["lockedSections"] = sorted(locked)
    return _sync_plan_derivatives(plan)


def _replace_caption_text(base: dict[str, Any], fresh: dict[str, Any]) -> None:
    fresh_scenes = {scene.get("id"): scene for scene in fresh.get("scenePlan", []) if isinstance(scene, dict)}
    for scene in base.get("scenePlan", []):
        fresh_scene = fresh_scenes.get(scene.get("id"))
        if fresh_scene:
            scene["caption"] = fresh_scene.get("caption", scene.get("caption", ""))
    base.setdefault("script", {})["captionStyle"] = fresh.get("script", {}).get("captionStyle", base.get("script", {}).get("captionStyle", {}))


def _apply_section_locks(plan: dict[str, Any], previous: dict[str, Any], locked: set[str]) -> None:
    previous_script = previous.get("script", {})
    current_script = plan.setdefault("script", {})
    if "script" in locked:
        plan["script"] = previous_script
        plan["hook"] = previous.get("hook", plan.get("hook", ""))
    elif "hook" in locked:
        plan["hook"] = previous.get("hook", plan.get("hook", ""))
        current_script["hook"] = previous.get("hook", current_script.get("hook", ""))
        old_lines = previous_script.get("lines", [])
        if old_lines:
            current_script.setdefault("lines", [])
            if current_script["lines"]:
                current_script["lines"][0] = old_lines[0]
            else:
                current_script["lines"].append(old_lines[0])
    for item in locked:
        if item.startswith("script:"):
            try:
                index = int(item.split(":", 1)[1])
            except ValueError:
                continue
            old_lines = previous_script.get("lines", [])
            new_lines = current_script.setdefault("lines", [])
            if 0 <= index < len(old_lines):
                while len(new_lines) <= index:
                    new_lines.append("")
                new_lines[index] = old_lines[index]
    if "style" in locked:
        plan["editingStyle"] = previous.get("editingStyle", plan.get("editingStyle", {}))
    if "music" in locked:
        plan.setdefault("editingStyle", {})["musicSync"] = previous.get("editingStyle", {}).get("musicSync", plan.get("editingStyle", {}).get("musicSync", {}))

    old_scenes = {scene.get("id"): scene for scene in previous.get("scenePlan", []) if isinstance(scene, dict)}
    for scene in plan.get("scenePlan", []):
        scene_id = scene.get("id")
        old = old_scenes.get(scene_id)
        if not old:
            continue
        if f"scene:{scene_id}" in locked or scene_id in locked:
            scene.clear()
            scene.update(old)
            continue
        if "captions" in locked or f"caption:{scene_id}" in locked:
            scene["caption"] = old.get("caption", scene.get("caption", ""))
        if "timing" in locked or f"timing:{scene_id}" in locked:
            scene["start"] = old.get("start", scene.get("start"))
            scene["end"] = old.get("end", scene.get("end"))
            scene["duration"] = old.get("duration", scene.get("duration"))
        if "titlecards" in locked or "title_cards" in locked or f"title:{scene_id}" in locked:
            scene["title"] = old.get("title", scene.get("title", ""))


def _sync_plan_derivatives(plan: dict[str, Any]) -> dict[str, Any]:
    scenes = plan.get("scenePlan", [])
    plan["captions"] = [
        {"sceneId": scene["id"], "text": scene.get("caption", ""), "start": scene.get("start", 0), "duration": scene.get("duration", 0)}
        for scene in scenes
    ]
    plan["textOverlays"] = [
        {"sceneId": scene["id"], "text": scene.get("title", ""), "role": scene.get("role", ""), "start": scene.get("start", 0), "duration": scene.get("duration", 0)}
        for scene in scenes
    ]
    plan["visualDirections"] = [_visual_direction(plan.get("contentBrief", {}), scene) for scene in scenes]
    plan.setdefault("reviewSummary", {}).setdefault("mustReview", ["Hook", "Script", "Scene timing", "Captions", "CTA", "Asset relevance"])
    plan["duration"] = round(max((float(scene.get("end", 0)) for scene in scenes), default=float(plan.get("duration", 0) or 0)), 3)
    return plan


def _select_media(assets_folder: Path | None, *, output_dir: Path, scene_duration: float, max_clips: int = 8) -> dict[str, Any]:
    if not assets_folder:
        return {"folder": None, "selected": [], "images": [], "warnings": []}
    assets_folder = assets_folder.resolve()
    if not assets_folder.exists():
        return {"folder": str(assets_folder), "selected": [], "images": [], "warnings": [f"Assets folder does not exist: {assets_folder}"]}
    warnings: list[str] = []
    selected: list[dict[str, Any]] = []
    try:
        report = select_highlights(assets_folder, scene_duration=scene_duration, max_clips=max_clips)
        raw_selected = report.get("selected", [])
        selected = _expand_selected_segments(raw_selected, max_clips=max_clips, scene_duration=scene_duration)
        report["rawSelectedClipCount"] = len(raw_selected)
        report["selectedClipCount"] = len(selected)
        report["selected"] = selected
        report["expandedSegments"] = selected
        report["untrimmedSourceSupport"] = {
            "enabled": True,
            "reason": "Long OBS/Streamlabs captures are sampled into multiple non-destructive trimStart/trimEnd segments.",
        }
        _write_json(output_dir / "clip_selection.json", report)
        warnings.extend(report.get("warnings", []))
    except Exception as exc:
        warnings.append(f"Video highlight selection skipped: {exc}")
    images = [str(path.resolve()) for path in sorted(assets_folder.rglob("*")) if path.suffix.lower() in IMAGE_EXTENSIONS][:8]
    return {"folder": str(assets_folder), "selected": selected, "images": images, "warnings": warnings}


def _expand_selected_segments(selected: list[dict[str, Any]], *, max_clips: int, scene_duration: float) -> list[dict[str, Any]]:
    if not selected or max_clips <= len(selected):
        return selected[:max_clips]
    expanded: list[dict[str, Any]] = []
    for clip in selected:
        starts = _candidate_starts_for_clip(clip, scene_duration)
        for start in starts:
            clone = dict(clip)
            clone["highlightStart"] = round(start, 3)
            clone["highlightDuration"] = round(min(scene_duration, float(clip.get("duration", scene_duration) or scene_duration)), 3)
            clone["highlightReason"] = "motion/intent segment" if start != float(clip.get("highlightStart", 0) or 0) else clip.get("highlightReason", "highlight segment")
            expanded.append(clone)
            if len(expanded) >= max_clips:
                return expanded
    return expanded or selected[:max_clips]


def _candidate_starts_for_clip(clip: dict[str, Any], scene_duration: float) -> list[float]:
    duration = float(clip.get("duration", 0) or 0)
    max_start = max(duration - scene_duration, 0)
    raw_candidates = [float(clip.get("highlightStart", 0) or 0)]
    for spike in clip.get("motionSpikes", []) or []:
        if isinstance(spike, dict):
            raw_candidates.append(float(spike.get("time", 0) or 0) - scene_duration / 2)
    if duration > 0:
        quarters = [duration * 0.18, duration * 0.34, duration * 0.50, duration * 0.66, duration * 0.82]
        raw_candidates.extend(time - scene_duration / 2 for time in quarters)
    if duration > scene_duration * 4:
        early_cutoff = max(8.0, min(duration * 0.08, 30.0))
        later_candidates = [candidate for candidate in raw_candidates if candidate >= early_cutoff]
        if later_candidates:
            raw_candidates = later_candidates
    starts: list[float] = []
    for candidate in raw_candidates:
        start = max(0.0, min(candidate, max_start))
        if any(abs(start - existing) < max(scene_duration * 0.75, 1.5) for existing in starts):
            continue
        starts.append(start)
    return starts


def _analyze_music(music_path: Path | None, *, output_dir: Path) -> dict[str, Any] | None:
    if not music_path:
        return None
    try:
        return analyze_audio(music_path.resolve(), output_path=output_dir / "music_analysis.json")
    except Exception as exc:
        return {"audio": str(music_path), "beats": [], "bassDrops": [], "warnings": [f"Music analysis skipped: {exc}"]}


def _validate_or_repair(project: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        validate_project(project)
        return project, {"repaired": False, "warnings": []}
    except ProjectValidationError as exc:
        repaired = repair_project_data(project)
        if not repaired.valid:
            raise ProjectValidationError("Generated project could not be repaired", repaired.errors_after) from exc
        return repaired.data, {"repaired": True, "warnings": ["Generated JSON needed automatic repair before writing."]}


def _write_generation_outputs(
    output_dir: Path,
    brief: dict[str, Any],
    script: dict[str, Any],
    scene_plan: list[dict[str, Any]],
    plan: dict[str, Any],
    project: dict[str, Any],
    *,
    comparison: dict[str, Any] | None = None,
) -> dict[str, Path]:
    paths = {
        "brief": output_dir / "content_brief.json",
        "script": output_dir / "script.json",
        "scene_plan": output_dir / "scene_plan.json",
        "plan": output_dir / "content_plan.json",
        "project": output_dir / "project.json",
        "review": output_dir / "review_summary.txt",
    }
    _write_json(paths["brief"], brief)
    _write_json(paths["script"], script)
    _write_json(paths["scene_plan"], {"scenes": scene_plan})
    _write_json(paths["plan"], plan)
    _write_json(paths["project"], project)
    paths["review"].write_text(_review_text(plan, paths["project"]), encoding="utf-8")
    paths.update(write_review_outputs(output_dir, plan, project, comparison=comparison))
    return paths


def _review_text(plan: dict[str, Any], project_path: Path) -> str:
    lines = [
        "Content Generator Review",
        "=" * 32,
        f"Project JSON: {project_path}",
        f"Mode: {plan['contentBrief']['mode']}",
        f"Product: {plan['contentBrief']['productName']}",
        f"Goal: {plan['contentBrief']['goal']}",
        f"Hook: {plan['hook']}",
        f"Style: {plan['editingStyle']['stylePreset']} ({plan['editingStyle']['tone']})",
        f"Platform: {plan['contentBrief']['targetPlatform']} / {plan['contentBrief']['exportPreset']}",
        f"Duration: {plan['duration']}s",
        "",
        "Script:",
    ]
    lines.extend(f"- {line}" for line in plan["script"]["lines"])
    lines.extend(["", "Scene Plan:"])
    for scene in plan["scenePlan"]:
        lines.append(f"- {scene['id']} [{scene['start']}s-{scene['end']}s] {scene['role']}: {scene['caption']}")
    lines.extend(["", "Review Before Final Render:"])
    lines.extend(f"- {item}" for item in plan["reviewSummary"].get("mustReview", []))
    if plan["reviewSummary"].get("lockedSections"):
        lines.extend(["", "Locked Sections:"])
        lines.extend(f"- {item}" for item in plan["reviewSummary"]["lockedSections"])
    if plan.get("warnings"):
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in plan["warnings"])
    return "\n".join(lines) + "\n"


def _visual_direction(brief: dict[str, Any], scene: dict[str, Any]) -> dict[str, Any]:
    if scene["mediaRole"] == "title_card":
        direction = "Animated title card with large readable text, subtle motion, and safe-zone placement."
    elif brief["mode"] == "tutorial":
        direction = "Use clear UI focus, slower zooms, readable captions, and minimal distractions."
    elif brief["mode"] == "product_showcase":
        direction = "Use smooth zooms, premium lighting, clean lower thirds, and feature reveal pacing."
    elif brief["mode"] == "tiktok":
        direction = "Use fast cuts, punchy captions, and beat-aware motion."
    else:
        direction = "Use benefit-driven overlays, clear captions, and polished CTA pacing."
    scene["visualDirection"] = direction
    return {"sceneId": scene["id"], "direction": direction}


def _read_existing_plan(path: Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    return json.loads(path.resolve().read_text(encoding="utf-8"))


def _normalize_mode(mode: str) -> str:
    key = mode.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {"shorts": "youtube_shorts", "youtube_short": "youtube_shorts", "product": "product_showcase", "promo": "promo_ad", "ad": "promo_ad"}
    key = aliases.get(key, key)
    if key not in MODES:
        raise ValueError(f"Unknown content mode '{mode}'. Valid modes: {', '.join(sorted(MODES))}")
    return key


def _platform(value: str) -> dict[str, Any]:
    key = value.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in PLATFORMS:
        key = "shorts"
    return {"key": key, **PLATFORMS[key]}


def _duration(idea: str, override: float | None, defaults: dict[str, Any]) -> float:
    if override is None:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:sec|second|seconds|s)\b", idea.lower())
        override = float(match.group(1)) if match else None
    value = override if override is not None else float(defaults["duration"])
    return round(max(float(defaults["minDuration"]), min(float(defaults["maxDuration"]), float(value))), 3)


def _product_name(idea: str) -> str:
    patterns = [
        r"for my ([^.]+?)(?:\.|,| that | with | make | about |$)",
        r"for an? ([^.]+?)(?:\.|,| that | with | make | about |$)",
        r"about ([^.]+?)(?:\.|,| that | with | make |$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, idea, flags=re.IGNORECASE)
        if match:
            return _title_case(match.group(1))
    return _title_case(idea[:48] or "Product")


def _features(idea: str, bullets: list[str]) -> list[str]:
    clean = [_sentence(item) for item in bullets if item.strip()]
    if clean:
        return clean[:6]
    match = re.search(r"\b(?:scans|detects|checks|fixes|shows|handles|includes|features)\s+([^.]*)", idea, flags=re.IGNORECASE)
    source = match.group(1) if match else idea
    source = re.sub(r"\b(?:and|plus)\b", ",", source, flags=re.IGNORECASE)
    parts = []
    for item in source.split(","):
        item = item.strip(" .")
        lower = item.lower()
        if len(item) < 3 or len(item) > 84:
            continue
        if any(skip in lower for skip in ["youtube short", "tiktok", "make it", "seconds", "cinematic", "premium"]):
            continue
        parts.append(_sentence(item))
    return parts[:6] or ["Clear problem detection", "Fast visual proof", "Simple result"]


def _style_for(mode: str, tone: str, style: str | None, idea: str) -> str:
    if style and style != "auto":
        key = normalize_style(style)
        if key not in list_styles():
            raise ValueError(f"Unknown style '{style}'. Valid styles: {', '.join(list_styles())}")
        return key
    lower = idea.lower()
    tokens = _word_tokens(lower)
    if "blue" in tokens and ("black" in tokens or "cyber" in tokens):
        return "blue_black_cyber"
    if "red" in tokens or "cyber" in tokens or "security" in tokens:
        return "red_black_aegis"
    if tone == "minimal" or mode == "tutorial":
        return "minimal_tech"
    if tone == "aggressive" or mode == "tiktok":
        return "gaming_montage"
    if "luxury" in lower or "premium" in lower or mode == "product_showcase":
        return "luxury_promo" if "luxury" in lower else "clean_cinematic"
    return "clean_cinematic"


def _theme(style: str, tone: str, idea: str) -> dict[str, str]:
    lower = idea.lower()
    tokens = _word_tokens(lower)
    if style == "blue_black_cyber":
        return {"background": "#020617", "accent": "#38bdf8", "secondary": "#dbeafe"}
    if style == "red_black_aegis":
        return {"background": "#050000", "accent": "#ef4444", "secondary": "#f8fafc"}
    if "blue" in tokens and ("black" in tokens or "cyber" in tokens):
        return {"background": "#020617", "accent": "#38bdf8", "secondary": "#dbeafe"}
    if "red" in tokens and "black" in tokens:
        return {"background": "#050000", "accent": "#ef4444", "secondary": "#f8fafc"}
    if style == "gaming_montage" or tone == "aggressive":
        return {"background": "#050000", "accent": "#f97316", "secondary": "#ef4444"}
    if style == "minimal_tech" or tone == "minimal":
        return {"background": "#f8fafc", "accent": "#0f172a", "secondary": "#2563eb"}
    if style == "luxury_promo":
        return {"background": "#090806", "accent": "#f5d46b", "secondary": "#ffffff"}
    return {"background": "#05070d", "accent": "#6db5a5", "secondary": "#f8fafc"}


def _word_tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.replace("_", " ").replace("/", " ")))


def _goal_for(mode: str, product: str) -> str:
    goals = {
        "youtube_shorts": f"Create a fast hook-driven vertical short for {product}.",
        "tiktok": f"Create a punchy caption-heavy TikTok edit for {product}.",
        "product_showcase": f"Create a cinematic product showcase for {product}.",
        "tutorial": f"Create a clear step-by-step tutorial for {product}.",
        "promo_ad": f"Create a benefit-driven promo/ad for {product}.",
    }
    return goals[mode]


def _concept(mode: str, product: str, goal: str, tone: str) -> str:
    return f"A {tone} {mode.replace('_', ' ')} for {product}: {goal}"


def _hook(mode: str, product: str, features: list[str], idea: str) -> str:
    lower = idea.lower()
    if mode == "tiktok":
        return f"You are checking {product} the slow way."
    if mode == "tutorial":
        return f"Here is the clean way to use {product}."
    if mode == "product_showcase":
        return f"Meet {product}, built for cleaner demos."
    if "troubleshooter" in lower:
        return "Stop guessing why apps will not launch."
    if features:
        return f"{features[0]} should not slow you down."
    return f"Here is {product} in motion."


def _problem(product: str, features: list[str]) -> str:
    if features:
        return f"{features[0]} can hide the real problem."
    return f"The hard part is knowing what to fix first."


def _payoff(product: str, features: list[str]) -> str:
    if len(features) >= 2:
        return f"{features[0]} and {features[1]} become a clear next step."
    return f"{product} turns the workflow into a clear next step."


def _benefit(feature: str) -> str:
    return f"{_sentence(feature)} becomes easier to explain, show, and act on."


def _cta(mode: str, product: str) -> str:
    if mode == "tutorial":
        return f"Save this workflow for your next {product} session."
    if mode == "tiktok":
        return f"Follow for more fast {product} breakdowns."
    if mode == "promo_ad":
        return f"Try {product} before the next blocker costs time."
    return f"Use {product} before the next failed launch."


def _caption_style(brief: dict[str, Any]) -> dict[str, Any]:
    if brief["mode"] == "tutorial":
        return {"density": "readable", "size": "medium_large", "pace": "clear"}
    if brief["mode"] == "tiktok":
        return {"density": "high", "size": "large", "pace": "fast"}
    return {"density": "medium_high", "size": "large", "pace": brief["pacing"]}


def _transition_type(brief: dict[str, Any]) -> str:
    if brief["tone"] == "aggressive" or brief["mode"] == "tiktok":
        return "zoom"
    if brief["mode"] == "tutorial":
        return "crossfade"
    return "crossfade"


def _transition(style: dict[str, Any]) -> dict[str, Any]:
    if style["transitionType"] == "zoom":
        return {"type": "zoom", "duration": 0.22}
    return {"type": "crossfade", "duration": 0.32}


def _camera_for(style: dict[str, Any], scene: dict[str, Any]) -> dict[str, Any]:
    if style["tone"] == "aggressive":
        return {"mode": "dynamic_zoom", "zoom": 1.08, "duration": scene["duration"]}
    if style["tone"] == "minimal":
        return {"mode": "smooth_pan", "zoom": 1.025, "duration": scene["duration"], "panX": 10, "panY": 0}
    return {"mode": "dynamic_zoom", "zoom": 1.05, "duration": scene["duration"]}


def _effect_preset(style: str) -> str:
    if style == "red_black_aegis":
        return "premium_red_black"
    if style == "blue_black_cyber":
        return "cinematic_polish"
    if style == "luxury_promo":
        return "soft_luxury"
    return "cinematic_polish"


def _apply_music_sync(timeline: list[dict[str, Any]], music_sync: dict[str, Any]) -> None:
    if not music_sync.get("enabled"):
        return
    hits = [float(item["time"]) for item in music_sync.get("bassDrops", []) + music_sync.get("beats", []) if "time" in item]
    for scene in timeline:
        if not any(abs(hit - float(scene["start"])) <= 0.35 for hit in hits):
            continue
        if scene.get("transitionOut"):
            scene["transitionOut"] = {"type": "zoom", "duration": 0.2}
        for layer in scene.get("layers", []):
            if layer.get("type") == "text":
                layer["animation"] = {"in": "pulse", "out": "fade", "duration": 0.22}


def _media_scene_duration(plan: dict[str, Any]) -> float:
    media = [float(scene["duration"]) for scene in plan["scenePlan"] if scene.get("mediaRole") != "title_card"]
    return max(min(sum(media) / max(len(media), 1), 8.0), 1.5)


def _media_scene_count(plan: dict[str, Any]) -> int:
    return sum(1 for scene in plan.get("scenePlan", []) if scene.get("mediaRole") != "title_card")


def _fit_title(text: str) -> str:
    words = text.strip().split()
    return " ".join(words[:8]) if len(words) > 8 else " ".join(words)


def _fit_caption(text: str) -> str:
    text = " ".join(text.strip().split())
    return text if len(text) <= 96 else text[:93].rstrip() + "..."


def _title_case(text: str) -> str:
    small = {"a", "an", "and", "for", "of", "the", "to", "with"}
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9-]*", text)
    if not words:
        return "Product"
    return " ".join(word.lower() if index and word.lower() in small else word[:1].upper() + word[1:].lower() for index, word in enumerate(words[:7]))


def _sentence(text: str) -> str:
    clean = " ".join(text.strip().strip(".").split())
    return clean[:1].upper() + clean[1:] if clean else "Clear value"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
