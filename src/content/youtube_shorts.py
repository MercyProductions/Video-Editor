from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from captions.engine import smart_caption_items
from clips.selector import select_highlights
from intelligence.beat_sync import analyze_audio
from parser.project_parser import ProjectParser
from preview.reporter import generate_preview
from renderer.renderer import VideoRenderer
from schema.validator import validate_project
from styles.presets import apply_style, list_styles, normalize_style


WIDTH = 1080
HEIGHT = 1920
FPS = 60


def run_youtube_shorts_auto(
    *,
    prompt: str,
    output_dir: Path,
    assets_folder: Path | None = None,
    music_path: Path | None = None,
    logo_path: Path | None = None,
    style: str | None = None,
    duration: float | None = None,
    render: bool = False,
    quality: str = "preview",
    cache: bool = True,
    gpu: bool = False,
) -> dict[str, Any]:
    """Create a structured YouTube Short from one local prompt and optional assets."""
    started = time.perf_counter()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    brief = build_shorts_brief(prompt, style=style, duration=duration)
    clip_report = _select_clips(assets_folder, output_dir=output_dir, target_duration=brief["duration"])
    music_analysis = _analyze_music(music_path, output_dir=output_dir)
    plan = _build_plan(brief, clip_report, music_analysis=music_analysis, logo_path=logo_path, music_path=music_path)
    project = build_shorts_project(plan, clip_report, music_path=music_path, logo_path=logo_path)

    validate_project(project)
    project_path = output_dir / "project.json"
    _write_json(project_path, project)
    _write_json(output_dir / "short_plan.json", plan)
    (output_dir / "review_summary.txt").write_text(_review_summary(plan, project_path), encoding="utf-8")

    parsed = ProjectParser().load(project_path)
    preview = generate_preview(parsed, output_dir=output_dir / "preview")

    render_path: Path | None = None
    if render:
        render_path = output_dir / "final_video.mp4"
        VideoRenderer(
            parsed,
            output_path=render_path,
            quality=quality,
            use_cache=cache,
            resume=cache,
            gpu=gpu,
        ).render()

    summary = {
        "mode": "youtube_shorts_auto",
        "prompt": prompt,
        "concept": plan["concept"],
        "hook": plan["hook"],
        "style": plan["editingStyle"]["stylePreset"],
        "duration": plan["duration"],
        "projectPath": str(project_path),
        "planPath": str(output_dir / "short_plan.json"),
        "reviewSummaryPath": str(output_dir / "review_summary.txt"),
        "previewSummaryPath": str(preview.summary_path),
        "renderPlanPath": str(preview.plan_path),
        "renderPath": str(render_path) if render_path else None,
        "elapsedSeconds": round(time.perf_counter() - started, 3),
        "warnings": plan.get("warnings", []),
    }
    _write_json(output_dir / "youtube_short_summary.json", summary)
    return summary


def build_shorts_brief(prompt: str, *, style: str | None = None, duration: float | None = None) -> dict[str, Any]:
    lower = prompt.lower()
    selected_style = _select_style(lower, style)
    target_duration = _target_duration(lower, duration)
    product = _product_name(prompt)
    features = _features(prompt)
    vibe = _vibe(prompt, selected_style)
    hook = _hook(product, features, lower)
    problem = _problem_line(product, features)
    result = _result_line(product, features)
    cta = _cta_line(product)
    script = [
        hook,
        problem,
        *[_feature_line(feature) for feature in features[:4]],
        result,
        cta,
    ]
    theme = _theme_for_style(selected_style, lower)
    return {
        "prompt": prompt,
        "productName": product,
        "features": features,
        "vibe": vibe,
        "duration": target_duration,
        "stylePreset": selected_style,
        "theme": theme,
        "concept": f"A vertical YouTube Short that positions {product} as a fast, premium tool with a clear hook, pain point, feature proof, payoff, and CTA.",
        "hook": hook,
        "problem": problem,
        "result": result,
        "cta": cta,
        "script": script,
    }


def build_shorts_project(
    plan: dict[str, Any],
    clip_report: dict[str, Any],
    *,
    music_path: Path | None,
    logo_path: Path | None,
) -> dict[str, Any]:
    assets: dict[str, str] = {}
    selected_clips = clip_report.get("selected") or []
    for index, clip in enumerate(selected_clips, start=1):
        assets[f"clip_{index}"] = str(Path(clip["path"]).resolve())
    if music_path:
        assets["music"] = str(music_path.resolve())
    if logo_path:
        assets["logo"] = str(logo_path.resolve())

    scenes = []
    feature_clip_index = 0
    for scene_plan in plan["scenes"]:
        scene_id = scene_plan["id"]
        if scene_plan["section"] in {"hook", "problem", "result", "cta"}:
            scenes.append(_title_scene(scene_plan, plan, has_logo=bool(logo_path)))
            continue
        clip = selected_clips[feature_clip_index % len(selected_clips)] if selected_clips else None
        asset_key = f"clip_{feature_clip_index % len(selected_clips) + 1}" if selected_clips else None
        scenes.append(_feature_scene(scene_plan, plan, clip=clip, asset_key=asset_key))
        feature_clip_index += 1

    scenes[-1].pop("transitionOut", None)

    project = {
        "metadata": {
            "youtubeShortAuto": {
                "prompt": plan["prompt"],
                "concept": plan["concept"],
                "hook": plan["hook"],
                "script": plan["script"],
                "sceneList": plan["scenes"],
                "titleCards": plan["titleCards"],
                "captions": plan["captions"],
                "timing": plan["structure"],
                "editingStyle": plan["editingStyle"],
                "reviewSummary": plan["reviewSummary"],
                "warnings": plan.get("warnings", []),
            },
            "stylePreset": plan["editingStyle"]["stylePreset"],
        },
        "exportPreset": "shorts",
        "stylePreset": plan["editingStyle"]["stylePreset"],
        "project": {
            "width": WIDTH,
            "height": HEIGHT,
            "fps": FPS,
            "duration": plan["duration"],
            "background": plan["editingStyle"]["background"],
            "crf": 19,
        },
        "assets": assets,
        "timeline": scenes,
        "audio": [],
    }
    if music_path:
        project["audio"].append({"asset": "music", "start": 0, "volume": 0.42, "fadeIn": 0.25, "fadeOut": 1.2, "loop": True})
    styled = apply_style(project, plan["editingStyle"]["stylePreset"])
    _apply_music_sync_markers(styled["timeline"], plan.get("musicSync", {}))
    styled["timeline"][-1].pop("transitionOut", None)
    return styled


def _build_plan(
    brief: dict[str, Any],
    clip_report: dict[str, Any],
    *,
    music_analysis: dict[str, Any] | None,
    logo_path: Path | None,
    music_path: Path | None,
) -> dict[str, Any]:
    structure = _structure(brief["duration"])
    feature_slots = _feature_slots(structure["feature"], brief["features"])
    scenes = [
        _scene_plan("hook", "hook", structure["hook"], brief["hook"], "Hook", brief["hook"]),
        _scene_plan("problem", "problem", structure["problem"], "The problem", "Problem", brief["problem"]),
        *feature_slots,
        _scene_plan("result_payoff", "result", structure["result"], "Result", "Result/Payoff", brief["result"]),
        _scene_plan("cta_outro", "cta", structure["cta"], brief["productName"], "CTA/Outro", brief["cta"]),
    ]
    title_cards = [
        {"sceneId": scene["id"], "text": scene["title"], "start": scene["start"], "duration": scene["duration"]}
        for scene in scenes
        if scene["section"] in {"hook", "problem", "result", "cta"}
    ]
    captions = [
        {"sceneId": scene["id"], "text": scene["caption"], "start": scene["start"], "duration": scene["duration"]}
        for scene in scenes
    ]
    theme = brief["theme"]
    music_sync = {
        "enabled": bool(music_analysis),
        "music": str(music_path.resolve()) if music_path else None,
        "bpm": music_analysis.get("bpm") if music_analysis else None,
        "bassDrops": music_analysis.get("bassDrops", [])[:8] if music_analysis else [],
        "beats": music_analysis.get("beats", [])[:24] if music_analysis else [],
    }
    warnings = []
    if not clip_report.get("selected"):
        warnings.append("No usable video clips were selected; the Short will render as motion title cards.")
    if not music_path:
        warnings.append("No music provided; music sync metadata is disabled.")
    return {
        "mode": "youtube_shorts_auto",
        "prompt": brief["prompt"],
        "productName": brief["productName"],
        "concept": brief["concept"],
        "hook": brief["hook"],
        "script": brief["script"],
        "duration": brief["duration"],
        "structure": structure,
        "scenes": scenes,
        "titleCards": title_cards,
        "captions": captions,
        "editingStyle": {
            "stylePreset": brief["stylePreset"],
            "vibe": brief["vibe"],
            "background": theme["background"],
            "accent": theme["accent"],
            "secondary": theme["secondary"],
            "transitionType": "zoom" if brief["stylePreset"] in {"red_black_aegis", "gaming_montage"} else "crossfade",
            "pacing": "short_form_fast",
            "layout": "caption_heavy_vertical",
            "exportPreset": "shorts",
        },
        "musicSync": music_sync,
        "assets": {
            "clipCount": len(clip_report.get("selected", [])),
            "logo": str(logo_path.resolve()) if logo_path else None,
            "music": str(music_path.resolve()) if music_path else None,
        },
        "reviewSummary": {
            "needsReview": ["Hook strength", "Feature wording", "CTA wording", "Asset relevance"],
            "safeDefaults": ["Vertical 1080x1920", "Large captions", "Title safe placement", "Source media left untouched"],
        },
        "warnings": warnings + clip_report.get("warnings", []),
    }


def _scene_plan(scene_id: str, section: str, timing: dict[str, float], title: str, role: str, caption: str) -> dict[str, Any]:
    return {
        "id": scene_id,
        "section": section,
        "role": role,
        "start": timing["start"],
        "duration": timing["duration"],
        "end": timing["end"],
        "title": _fit_title(title),
        "caption": _fit_caption(caption),
    }


def _feature_slots(feature_timing: dict[str, float], features: list[str]) -> list[dict[str, Any]]:
    clean_features = features[:4] or ["Fast scan", "Clear diagnosis", "One-click fixes"]
    slot_duration = feature_timing["duration"] / len(clean_features)
    scenes = []
    for index, feature in enumerate(clean_features):
        start = round(feature_timing["start"] + index * slot_duration, 3)
        end = round(feature_timing["start"] + (index + 1) * slot_duration, 3)
        scenes.append(
            _scene_plan(
                f"feature_{index + 1}",
                "feature",
                {"start": start, "end": end, "duration": round(end - start, 3)},
                _feature_title(feature),
                "Feature Showcase",
                _feature_line(feature),
            )
        )
    return scenes


def _title_scene(scene_plan: dict[str, Any], plan: dict[str, Any], *, has_logo: bool) -> dict[str, Any]:
    theme = plan["editingStyle"]
    duration = float(scene_plan["duration"])
    layers: list[dict[str, Any]] = [
        {"type": "animated_background", "color": theme["accent"], "opacity": 0.11, "speed": 88, "start": 0, "duration": duration},
        {"type": "particle", "color": theme["secondary"], "opacity": 0.22, "count": 20, "start": 0, "duration": duration},
    ]
    if has_logo and scene_plan["section"] in {"hook", "cta"}:
        layers.append({"type": "image", "asset": "logo", "x": "center", "y": 210, "width": 260, "height": 260, "fit": "contain", "animation": {"in": "fade", "out": "fade", "duration": 0.35}})
    layers.extend(
        [
            {
                "type": "text",
                "text": scene_plan["title"],
                "x": "center",
                "y": 610 if has_logo and scene_plan["section"] in {"hook", "cta"} else "center",
                "fontSize": 86 if scene_plan["section"] == "hook" else 76,
                "color": "#ffffff" if scene_plan["section"] != "problem" else theme["accent"],
                "strokeColor": "#000000",
                "strokeWidth": 4,
                "box": True,
                "boxColor": "#00000099",
                "boxPadding": 22,
                "lineSpacing": 12,
                "animation": {"in": "typewriter", "out": "fade", "duration": 0.45},
            },
            _caption_layer(scene_plan["caption"], duration, theme, y=1380),
            _progress_layer(theme, duration),
        ]
    )
    return {
        "id": scene_plan["id"],
        "start": scene_plan["start"],
        "duration": duration,
        "layers": layers,
        "transitionOut": _transition(theme),
        "effectGraphPreset": _effect_preset(theme["stylePreset"]),
    }


def _feature_scene(scene_plan: dict[str, Any], plan: dict[str, Any], *, clip: dict[str, Any] | None, asset_key: str | None) -> dict[str, Any]:
    theme = plan["editingStyle"]
    duration = float(scene_plan["duration"])
    layers: list[dict[str, Any]] = []
    if clip and asset_key:
        trim_start = float(clip.get("highlightStart", 0) or 0)
        layers.append(
            {
                "type": "video",
                "asset": asset_key,
                "x": 0,
                "y": 0,
                "width": WIDTH,
                "height": HEIGHT,
                "fit": "cover",
                "trimStart": trim_start,
                "trimEnd": round(trim_start + duration, 3),
                "contrast": 1.14,
                "brightness": -0.02 if theme["stylePreset"] == "red_black_aegis" else 0.0,
                "camera": {"mode": "dynamic_zoom", "zoom": 1.06, "duration": duration},
                "animation": {"in": "zoomIn", "out": "fade", "duration": 0.25},
            }
        )
        layers.append({"type": "shape", "x": 0, "y": 0, "width": WIDTH, "height": HEIGHT, "color": "#000000", "opacity": 0.24})
    else:
        layers.extend(
            [
                {"type": "animated_background", "color": theme["accent"], "opacity": 0.13, "speed": 120, "start": 0, "duration": duration},
                {"type": "particle", "color": theme["secondary"], "opacity": 0.28, "count": 28, "start": 0, "duration": duration},
            ]
        )
    layers.extend(
        [
            {
                "type": "lower_third",
                "title": scene_plan["title"],
                "subtitle": "Feature highlight",
                "x": 70,
                "y": 170,
                "width": 940,
                "height": 138,
                "fontSize": 54,
                "subtitleSize": 30,
                "boxColor": "#050000cc" if theme["stylePreset"] == "red_black_aegis" else "#05070dcc",
                "color": theme["accent"],
                "subtitleColor": "#e5e7eb",
                "start": 0.15,
                "duration": max(duration - 0.3, 0.5),
            },
            _caption_layer(scene_plan["caption"], duration, theme, y=1370),
            _progress_layer(theme, duration),
        ]
    )
    return {
        "id": scene_plan["id"],
        "start": scene_plan["start"],
        "duration": duration,
        "layers": layers,
        "transitionOut": _transition(theme),
        "effectGraphPreset": _effect_preset(theme["stylePreset"]),
        "analysis": {"source": "youtube_shorts_auto", "caption": scene_plan["caption"]},
    }


def _caption_layer(text: str, duration: float, theme: dict[str, Any], *, y: int) -> dict[str, Any]:
    return {
        "type": "caption",
        "layout": "lower_third",
        "x": "center",
        "y": y,
        "fontSize": 58,
        "color": "#ffffff",
        "strokeColor": "#000000",
        "strokeWidth": 5,
        "box": True,
        "boxColor": "#000000b5",
        "boxPadding": 18,
        "captionMode": "smart",
        "safeZone": "title",
        "animation": {"in": "slideUp", "out": "fade", "duration": 0.18},
        "items": smart_caption_items(text, duration=max(duration - 0.45, 1.0), max_words=5),
        "highlightColor": theme["accent"],
    }


def _progress_layer(theme: dict[str, Any], duration: float) -> dict[str, Any]:
    return {
        "type": "progress",
        "x": "center",
        "y": 1804,
        "width": 740,
        "height": 10,
        "color": theme["accent"],
        "backgroundColor": "#ffffff33",
        "opacity": 0.85,
        "start": 0,
        "duration": duration,
    }


def _transition(theme: dict[str, Any]) -> dict[str, Any]:
    if theme["stylePreset"] in {"red_black_aegis", "gaming_montage"}:
        return {"type": "zoom", "duration": 0.22}
    if theme["stylePreset"] == "minimal_tech":
        return {"type": "crossfade", "duration": 0.28}
    return {"type": "crossfade", "duration": 0.32}


def _apply_music_sync_markers(scenes: list[dict[str, Any]], music_sync: dict[str, Any]) -> None:
    if not music_sync.get("enabled"):
        return
    hit_times = [float(item["time"]) for item in music_sync.get("bassDrops", []) + music_sync.get("beats", []) if "time" in item]
    for scene in scenes:
        scene_start = float(scene["start"])
        hit_near_scene = any(abs(hit - scene_start) <= 0.35 for hit in hit_times)
        if not hit_near_scene:
            continue
        if scene.get("transitionOut"):
            scene["transitionOut"] = {"type": "zoom", "duration": 0.2}
        for layer in scene.get("layers", []):
            if layer.get("type") == "text":
                layer.setdefault("effects", [])
                if "shake" not in layer["effects"]:
                    layer["effects"].append("shake")
                layer["animation"] = {"in": "pulse", "out": "fade", "duration": 0.22}
            if layer.get("type") in {"video", "image"}:
                layer.setdefault("animation", {"in": "zoomIn", "out": "fade", "duration": 0.22})


def _select_clips(assets_folder: Path | None, *, output_dir: Path, target_duration: float) -> dict[str, Any]:
    if not assets_folder:
        return {"folder": None, "selected": [], "warnings": []}
    assets_folder = assets_folder.resolve()
    if not assets_folder.exists():
        return {"folder": str(assets_folder), "selected": [], "warnings": [f"Assets folder does not exist: {assets_folder}"]}
    try:
        return select_highlights(
            assets_folder,
            scene_duration=max(1.5, min(5.0, target_duration / 7)),
            max_clips=6,
            output_path=output_dir / "clip_selection.json",
        )
    except Exception as exc:
        return {"folder": str(assets_folder), "selected": [], "warnings": [f"Clip selection skipped: {exc}"]}


def _analyze_music(music_path: Path | None, *, output_dir: Path) -> dict[str, Any] | None:
    if not music_path:
        return None
    try:
        return analyze_audio(music_path.resolve(), output_path=output_dir / "music_analysis.json")
    except Exception as exc:
        return {"audio": str(music_path), "beats": [], "bassDrops": [], "warnings": [f"Music analysis skipped: {exc}"]}


def _structure(duration: float) -> dict[str, dict[str, float]]:
    if duration >= 40:
        timings = [
            ("hook", 0, 3),
            ("problem", 3, 10),
            ("feature", 10, min(30, duration - 12)),
            ("result", min(30, duration - 12), min(40, duration - 4)),
            ("cta", min(40, duration - 4), duration),
        ]
    else:
        weights = [3, 7, 20, 10, 5]
        sections = ["hook", "problem", "feature", "result", "cta"]
        cursor = 0.0
        timings = []
        for index, (section, weight) in enumerate(zip(sections, weights)):
            end = duration if index == len(sections) - 1 else cursor + duration * weight / sum(weights)
            timings.append((section, cursor, end))
            cursor = end
    return {name: {"start": round(start, 3), "end": round(end, 3), "duration": round(max(end - start, 0.2), 3)} for name, start, end in timings}


def _target_duration(lower: str, override: float | None) -> float:
    if override is not None:
        return round(max(8.0, min(45.0, float(override))), 3)
    match = re.search(r"(?:under|less than|below)\s+(\d+(?:\.\d+)?)\s*(?:sec|second|seconds|s)\b", lower)
    if match:
        return round(max(8.0, min(44.5, float(match.group(1)) - 0.5)), 3)
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:sec|second|seconds|s)\b", lower)
    if match:
        return round(max(8.0, min(45.0, float(match.group(1)))), 3)
    return 45.0


def _select_style(lower: str, requested: str | None) -> str:
    if requested and requested != "auto":
        key = normalize_style(requested)
        if key not in list_styles():
            valid = ", ".join(list_styles())
            raise ValueError(f"Unknown style '{requested}'. Valid styles: {valid}")
        return key
    if any(word in lower for word in ["red", "black", "cyber", "security", "hacker", "troubleshooter"]):
        return "red_black_aegis"
    if any(word in lower for word in ["gaming", "montage", "kill", "clip"]):
        return "gaming_montage"
    if "luxury" in lower or "premium" in lower:
        return "luxury_promo"
    if "minimal" in lower or "clean" in lower:
        return "minimal_tech"
    return "clean_cinematic"


def _theme_for_style(style: str, lower: str) -> dict[str, str]:
    if style == "red_black_aegis" or ("red" in lower and "black" in lower):
        return {"background": "#050000", "accent": "#ef4444", "secondary": "#f8fafc"}
    if style == "gaming_montage":
        return {"background": "#050000", "accent": "#f97316", "secondary": "#ef4444"}
    if style == "minimal_tech":
        return {"background": "#f8fafc", "accent": "#0f172a", "secondary": "#2563eb"}
    if style == "luxury_promo":
        return {"background": "#090806", "accent": "#f5d46b", "secondary": "#ffffff"}
    return {"background": "#05070d", "accent": "#6db5a5", "secondary": "#f8fafc"}


def _vibe(prompt: str, style: str) -> str:
    lower = prompt.lower()
    if "apple" in lower:
        return "minimal premium product reveal"
    if "cyber" in lower or "security" in lower or "red" in lower:
        return "premium red/black cybersecurity showcase"
    if style == "gaming_montage":
        return "fast aggressive gaming short"
    if style == "luxury_promo":
        return "polished premium promo"
    return "clean cinematic short"


def _product_name(prompt: str) -> str:
    cleaned = prompt.strip().strip('"')
    patterns = [
        r"for my ([^.]+?)(?:\.|,| that | with | make | under |$)",
        r"for an? ([^.]+?)(?:\.|,| that | with | make | under |$)",
        r"about ([^.]+?)(?:\.|,| that | with | make | under |$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if match:
            return _title_case(match.group(1))
    return _title_case(cleaned[:48] or "Product")


def _features(prompt: str) -> list[str]:
    match = re.search(r"\b(?:scans|detects|checks|fixes|shows|handles|includes)\s+([^.]*)", prompt, flags=re.IGNORECASE)
    source = match.group(1) if match else prompt
    source = re.sub(r"\b(?:and|plus)\b", ",", source, flags=re.IGNORECASE)
    candidates = [part.strip(" .") for part in source.split(",") if 3 <= len(part.strip()) <= 72]
    filtered = []
    for item in candidates:
        lower = item.lower()
        if any(skip in lower for skip in ["youtube short", "make it", "under ", "seconds", "premium", "cinematic"]):
            continue
        filtered.append(_sentence_case(item))
    return filtered[:5] or ["Missing runtimes", "Launch blockers", "Security settings"]


def _hook(product: str, features: list[str], lower: str) -> str:
    if "troubleshooter" in lower:
        return "Stop guessing why apps will not launch."
    if "security" in lower or "cyber" in lower:
        return "Find the blocker before it becomes a problem."
    if features:
        return f"{features[0]} should not slow you down."
    return f"Meet {product} in 45 seconds."


def _problem_line(product: str, features: list[str]) -> str:
    if features:
        return f"{features[0]} can hide the real launch issue."
    return f"Most tools show noise before they show the answer."


def _feature_line(feature: str) -> str:
    subject = _sentence_case(feature)
    verb = "are" if subject.lower().endswith("s") else "is"
    return f"{subject} {verb} scanned, explained, and surfaced fast."


def _feature_title(feature: str) -> str:
    return _fit_title(_sentence_case(feature))


def _result_line(product: str, features: list[str]) -> str:
    if len(features) >= 2:
        return f"{features[0]} and {features[1]} become a clear fix path."
    return f"{product} turns hidden blockers into clear next steps."


def _cta_line(product: str) -> str:
    return f"Use {product} before the next failed launch."


def _effect_preset(style: str) -> str:
    if style == "red_black_aegis":
        return "premium_red_black"
    if style == "luxury_promo":
        return "soft_luxury"
    return "cinematic_polish"


def _fit_title(text: str) -> str:
    words = text.strip().split()
    if len(words) <= 8:
        return " ".join(words)
    return " ".join(words[:8])


def _fit_caption(text: str) -> str:
    text = " ".join(text.strip().split())
    return text if len(text) <= 92 else text[:89].rstrip() + "..."


def _title_case(text: str) -> str:
    small = {"a", "an", "and", "for", "of", "the", "to", "with"}
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9-]*", text)
    if not words:
        return "Product"
    titled = [word.lower() if index and word.lower() in small else word[:1].upper() + word[1:].lower() for index, word in enumerate(words[:7])]
    return " ".join(titled)


def _sentence_case(text: str) -> str:
    clean = " ".join(text.strip().split())
    if not clean:
        return clean
    return clean[:1].upper() + clean[1:]


def _review_summary(plan: dict[str, Any], project_path: Path) -> str:
    lines = [
        "YouTube Shorts Auto-Creation Review",
        "=" * 40,
        f"Project JSON: {project_path}",
        f"Concept: {plan['concept']}",
        f"Hook: {plan['hook']}",
        f"Style: {plan['editingStyle']['stylePreset']} ({plan['editingStyle']['vibe']})",
        f"Duration: {plan['duration']}s",
        "",
        "Script:",
    ]
    lines.extend(f"- {line}" for line in plan["script"])
    lines.extend(["", "Scenes:"])
    for scene in plan["scenes"]:
        lines.append(f"- {scene['id']} [{scene['start']}s-{scene['end']}s] {scene['role']}: {scene['caption']}")
    if plan.get("warnings"):
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in plan["warnings"])
    return "\n".join(lines) + "\n"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
