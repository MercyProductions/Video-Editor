from __future__ import annotations

import json
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from content.generator import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, run_content_generator


SUPPORTED_ASSET_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS


@dataclass(frozen=True)
class BeginnerTemplate:
    key: str
    name: str
    mode: str
    target_platform: str
    tone: str
    style: str
    aspect_ratio: str
    pacing: str
    caption_style: str
    intro_style: str
    outro_style: str
    transition_type: str
    lighting_color: str
    title_card_format: str
    default_scene_structure: list[str]
    export_settings: dict[str, Any]


BEGINNER_TEMPLATES: dict[str, BeginnerTemplate] = {
    "premium_product_showcase": BeginnerTemplate(
        key="premium_product_showcase",
        name="Premium Product Showcase",
        mode="product_showcase",
        target_platform="youtube",
        tone="cinematic",
        style="luxury_promo",
        aspect_ratio="16:9",
        pacing="medium cinematic reveals with smooth zooms",
        caption_style="polished lower-third captions with high contrast",
        intro_style="clean logo reveal and product title card",
        outro_style="premium CTA card with soft fadeout",
        transition_type="crossfade and smooth zoom",
        lighting_color="subtle bloom, vignette, warm premium contrast",
        title_card_format="large product title, short benefit subtitle",
        default_scene_structure=["intro", "feature reveal", "interaction highlight", "result", "CTA"],
        export_settings={"preset": "youtube_1080p", "width": 1920, "height": 1080, "fps": 60},
    ),
    "youtube_short": BeginnerTemplate(
        key="youtube_short",
        name="YouTube Short",
        mode="youtube_shorts",
        target_platform="shorts",
        tone="aggressive",
        style="red_black_aegis",
        aspect_ratio="9:16",
        pacing="fast short-form hook/body/payoff structure",
        caption_style="large centered TikTok-style captions",
        intro_style="0-3 second hook card",
        outro_style="short CTA with progress bar",
        transition_type="quick cuts and beat-aware crossfades",
        lighting_color="high contrast accent lighting",
        title_card_format="bold hook line with compact subtitle",
        default_scene_structure=["hook", "problem", "feature showcase", "result", "CTA"],
        export_settings={"preset": "shorts", "width": 1080, "height": 1920, "fps": 60},
    ),
    "tiktok_reels_edit": BeginnerTemplate(
        key="tiktok_reels_edit",
        name="TikTok/Reels Edit",
        mode="tiktok",
        target_platform="tiktok",
        tone="aggressive",
        style="gaming_montage",
        aspect_ratio="9:16",
        pacing="trend-fast cuts with punchy caption hits",
        caption_style="large caption bursts with highlighted keywords",
        intro_style="quick pattern interrupt",
        outro_style="fast follow/comment CTA",
        transition_type="fast cuts, punch zooms, and slide hits",
        lighting_color="energetic contrast and saturated accent color",
        title_card_format="short punchline style card",
        default_scene_structure=["hook", "setup", "quick hits", "payoff", "CTA"],
        export_settings={"preset": "tiktok_reels", "width": 1080, "height": 1920, "fps": 60},
    ),
    "software_demo": BeginnerTemplate(
        key="software_demo",
        name="Software Demo",
        mode="tutorial",
        target_platform="youtube",
        tone="clean",
        style="minimal_tech",
        aspect_ratio="16:9",
        pacing="clear feature walkthrough with readable timing",
        caption_style="quiet captions below the active UI area",
        intro_style="simple product title and goal",
        outro_style="summary card with next action",
        transition_type="clean cuts and gentle crossfades",
        lighting_color="neutral tech contrast with subtle blue accents",
        title_card_format="feature name plus one benefit",
        default_scene_structure=["intro", "step 1", "step 2", "result", "CTA"],
        export_settings={"preset": "youtube_1080p", "width": 1920, "height": 1080, "fps": 60},
    ),
    "cybersecurity_tool_showcase": BeginnerTemplate(
        key="cybersecurity_tool_showcase",
        name="Cybersecurity Tool Showcase",
        mode="product_showcase",
        target_platform="shorts",
        tone="cinematic",
        style="red_black_aegis",
        aspect_ratio="9:16",
        pacing="premium threat-to-resolution showcase pacing",
        caption_style="bold red/white captions with strong outline",
        intro_style="dark logo reveal and threat hook",
        outro_style="secure result CTA with red accent fadeout",
        transition_type="cinematic crossfades, zoom hits, and dark wipes",
        lighting_color="premium red/black glow, vignette, contrast lift",
        title_card_format="security claim, short proof point",
        default_scene_structure=["hook", "risk", "scan", "result", "CTA"],
        export_settings={"preset": "shorts", "width": 1080, "height": 1920, "fps": 60},
    ),
    "gaming_montage": BeginnerTemplate(
        key="gaming_montage",
        name="Gaming Montage",
        mode="tiktok",
        target_platform="shorts",
        tone="aggressive",
        style="gaming_montage",
        aspect_ratio="9:16",
        pacing="fast energetic highlights with impact beats",
        caption_style="short hype captions with accent highlights",
        intro_style="high-energy hook card",
        outro_style="quick subscribe/follow CTA",
        transition_type="fast cuts, shake hits, and zoom transitions",
        lighting_color="high contrast, vibrant accent pulses",
        title_card_format="one-line hype card",
        default_scene_structure=["hook", "setup", "highlight run", "payoff", "CTA"],
        export_settings={"preset": "shorts", "width": 1080, "height": 1920, "fps": 60},
    ),
    "tutorial_walkthrough": BeginnerTemplate(
        key="tutorial_walkthrough",
        name="Tutorial Walkthrough",
        mode="tutorial",
        target_platform="youtube",
        tone="clean",
        style="clean_cinematic",
        aspect_ratio="16:9",
        pacing="slower step-by-step pacing",
        caption_style="readable captions with careful safe-zone placement",
        intro_style="what you will learn title card",
        outro_style="recap and next step",
        transition_type="simple cuts and soft fades",
        lighting_color="clean contrast and mild vignette",
        title_card_format="step number and action",
        default_scene_structure=["intro", "steps", "recap", "CTA"],
        export_settings={"preset": "youtube_1080p", "width": 1920, "height": 1080, "fps": 60},
    ),
    "minimal_saas_promo": BeginnerTemplate(
        key="minimal_saas_promo",
        name="Minimal SaaS Promo",
        mode="promo_ad",
        target_platform="youtube",
        tone="minimal",
        style="minimal_tech",
        aspect_ratio="16:9",
        pacing="restrained problem/solution/benefit pacing",
        caption_style="small premium captions with generous spacing",
        intro_style="minimal product statement",
        outro_style="simple CTA card",
        transition_type="clean cuts and restrained fades",
        lighting_color="low saturation, soft tech contrast",
        title_card_format="short benefit statement",
        default_scene_structure=["problem", "solution", "benefits", "CTA"],
        export_settings={"preset": "youtube_1080p", "width": 1920, "height": 1080, "fps": 60},
    ),
    "cinematic_trailer": BeginnerTemplate(
        key="cinematic_trailer",
        name="Cinematic Trailer",
        mode="product_showcase",
        target_platform="youtube",
        tone="cinematic",
        style="clean_cinematic",
        aspect_ratio="16:9",
        pacing="slow build into a polished reveal",
        caption_style="cinematic title captions with strong readability",
        intro_style="atmospheric opening title",
        outro_style="fadeout with final brand card",
        transition_type="crossfades, fades to black, and zoom reveals",
        lighting_color="cinematic contrast, vignette, subtle bloom",
        title_card_format="short dramatic statement",
        default_scene_structure=["cold open", "build", "feature reveal", "payoff", "CTA"],
        export_settings={"preset": "youtube_1080p", "width": 1920, "height": 1080, "fps": 60},
    ),
    "before_after_reveal": BeginnerTemplate(
        key="before_after_reveal",
        name="Before/After Reveal",
        mode="promo_ad",
        target_platform="shorts",
        tone="cinematic",
        style="red_black_aegis",
        aspect_ratio="9:16",
        pacing="problem-first reveal with a clear payoff",
        caption_style="before/after captions with highlighted result words",
        intro_style="before-state title card",
        outro_style="after-state CTA",
        transition_type="split reveal, crossfade, and zoom payoff",
        lighting_color="dark before state, brighter accent result",
        title_card_format="before line, after line, outcome",
        default_scene_structure=["before", "problem", "solution", "after", "CTA"],
        export_settings={"preset": "shorts", "width": 1080, "height": 1920, "fps": 60},
    ),
}


def template_names() -> list[str]:
    return sorted(BEGINNER_TEMPLATES)


def template_catalog() -> list[dict[str, Any]]:
    return [asdict(BEGINNER_TEMPLATES[key]) for key in template_names()]


def get_template(key: str) -> BeginnerTemplate:
    normalized = _normalize_template_key(key)
    if normalized not in BEGINNER_TEMPLATES:
        expected = ", ".join(template_names())
        raise KeyError(f"Unknown beginner template '{key}'. Expected one of: {expected}")
    return BEGINNER_TEMPLATES[normalized]


def run_beginner_auto_template(
    *,
    output_dir: Path,
    template: str,
    product_name: str,
    video_goal: str,
    key_features: list[str] | None = None,
    desired_vibe: str = "",
    target_platform: str | None = None,
    media_file: Path | None = None,
    image_folder: Path | None = None,
    asset_folder: Path | None = None,
    music_path: Path | None = None,
    logo_path: Path | None = None,
    duration: float | None = None,
    render: bool = False,
    quality: str = "preview",
    cache: bool = True,
    gpu: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    preset = get_template(template)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    smart = smart_defaults_for(preset, target_platform or preset.target_platform)

    staged = _stage_beginner_assets(
        output_dir / "beginner_inputs",
        media_file=media_file,
        image_folder=image_folder,
        asset_folder=asset_folder,
    )
    features = _clean_features(key_features or [], video_goal)
    idea = _compose_idea(
        preset,
        product_name=product_name,
        video_goal=video_goal,
        desired_vibe=desired_vibe,
        features=features,
        duration=duration,
    )
    result = run_content_generator(
        idea=idea,
        output_dir=output_dir,
        mode=preset.mode,
        product_name=product_name,
        target_platform=target_platform or preset.target_platform,
        goal=video_goal,
        bullet_points=features,
        assets_folder=staged["assetsFolder"] if staged["assetCount"] else None,
        music_path=music_path.resolve() if music_path else None,
        logo_path=logo_path.resolve() if logo_path else None,
        duration=duration,
        tone=preset.tone,
        style=preset.style,
        approved=render and quality == "final",
        render=render,
        quality=quality,
        cache=cache,
        gpu=gpu,
    )
    project_path = Path(result["projectPath"])
    _annotate_project(project_path, preset, staged, desired_vibe=desired_vibe, target_platform=target_platform or preset.target_platform, smart_defaults=smart)

    summary = {
        "mode": "beginner_auto_template",
        "template": asdict(preset),
        "smartDefaults": smart,
        "beginnerInputs": {
            "productName": product_name,
            "videoGoal": video_goal,
            "keyFeatures": features,
            "desiredVibe": desired_vibe,
            "targetPlatform": target_platform or preset.target_platform,
            "duration": duration,
            "mediaFile": str(media_file.resolve()) if media_file else None,
            "imageFolder": str(image_folder.resolve()) if image_folder else None,
            "assetFolder": str(asset_folder.resolve()) if asset_folder else None,
            "musicPath": str(music_path.resolve()) if music_path else None,
            "logoPath": str(logo_path.resolve()) if logo_path else None,
        },
        "stagedAssets": {
            "assetsFolder": str(staged["assetsFolder"]) if staged["assetsFolder"] else None,
            "files": [str(path) for path in staged["files"]],
            "warnings": staged["warnings"],
        },
        "outputs": {
            "projectJson": result.get("projectPath"),
            "reviewSummary": result.get("reviewSummaryPath"),
            "script": result.get("scriptPath"),
            "scenePlan": result.get("scenePlanPath"),
            "previewSummary": result.get("previewSummaryPath"),
            "renderPlan": result.get("renderPlanPath"),
            "renderedVideo": result.get("renderPath"),
        },
        "userFacingSummary": _user_summary(preset, result, staged),
        "warnings": [*staged["warnings"], *result.get("warnings", [])],
        "elapsedSeconds": round(time.perf_counter() - started, 3),
    }
    summary_path = output_dir / "beginner_auto_template_summary.json"
    _write_json(summary_path, summary)
    result["beginnerSummaryPath"] = str(summary_path)
    result["beginnerSummary"] = summary
    return result


def smart_defaults_for(template: BeginnerTemplate, target_platform: str | None = None) -> dict[str, Any]:
    platform = (target_platform or template.target_platform).strip().lower().replace("-", "_")
    vertical = platform in {"shorts", "youtube_shorts", "tiktok", "reels", "instagram", "instagram_reels"}
    square = platform == "square"
    if vertical:
        width, height, preset, caption_size = 1080, 1920, "tiktok_reels" if platform == "tiktok" else "shorts", 64
    elif square:
        width, height, preset, caption_size = 1080, 1080, "square", 54
    else:
        width, height, preset, caption_size = 1920, 1080, "youtube_1080p", 46
    transition_intensity = 0.75 if template.tone == "aggressive" else 0.55 if template.tone == "cinematic" else 0.35
    return {
        "aspectRatio": "9:16" if vertical else "1:1" if square else "16:9",
        "width": width,
        "height": height,
        "fps": 60 if not square else 30,
        "exportPreset": preset,
        "pacing": template.pacing,
        "captionSize": caption_size,
        "captionStyle": template.caption_style,
        "transitionIntensity": transition_intensity,
        "transitionType": template.transition_type,
        "audioNormalization": {"enabled": True, "targetLufs": -14 if vertical else -16, "peakDb": -1.0},
        "previewMode": "balanced",
        "safeDefaults": ["burned-in captions", "safe-zone text", "cache enabled", "preview before final"],
    }


def _normalize_template_key(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _stage_beginner_assets(
    target_dir: Path,
    *,
    media_file: Path | None,
    image_folder: Path | None,
    asset_folder: Path | None,
) -> dict[str, Any]:
    target_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    warnings: list[str] = []
    if media_file:
        _copy_supported_file(media_file, target_dir, files, warnings)
    if image_folder:
        _copy_supported_folder(image_folder, target_dir / "images", files, warnings, allowed=IMAGE_EXTENSIONS)
    if asset_folder:
        _copy_supported_folder(asset_folder, target_dir / "assets", files, warnings, allowed=SUPPORTED_ASSET_EXTENSIONS)
    return {"assetsFolder": target_dir, "files": files, "warnings": warnings, "assetCount": len(files)}


def _copy_supported_folder(source: Path, target_dir: Path, files: list[Path], warnings: list[str], *, allowed: set[str]) -> None:
    source = source.resolve()
    if not source.exists() or not source.is_dir():
        warnings.append(f"Folder does not exist: {source}")
        return
    for path in sorted(source.rglob("*")):
        if path.is_file() and path.suffix.lower() in allowed:
            _copy_supported_file(path, target_dir, files, warnings)


def _copy_supported_file(source: Path, target_dir: Path, files: list[Path], warnings: list[str]) -> None:
    source = source.resolve()
    if not source.exists() or not source.is_file():
        warnings.append(f"File does not exist: {source}")
        return
    if source.suffix.lower() not in SUPPORTED_ASSET_EXTENSIONS:
        warnings.append(f"Skipped unsupported beginner asset: {source}")
        return
    target_dir.mkdir(parents=True, exist_ok=True)
    target = _unique_path(target_dir / source.name)
    if source != target:
        shutil.copy2(source, target)
    files.append(target.resolve())


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not create unique asset name for {path}")


def _compose_idea(
    preset: BeginnerTemplate,
    *,
    product_name: str,
    video_goal: str,
    desired_vibe: str,
    features: list[str],
    duration: float | None,
) -> str:
    feature_text = ", ".join(features[:6]) if features else "the most important benefits"
    duration_text = f" Target duration is {duration:g} seconds." if duration else ""
    vibe_text = f" Desired vibe: {desired_vibe}." if desired_vibe else ""
    return (
        f"Create a {preset.name} for {product_name}. "
        f"Goal: {video_goal}. "
        f"Use the {preset.pacing} template with {preset.caption_style}. "
        f"Key features: {feature_text}.{vibe_text}{duration_text}"
    )


def _clean_features(features: list[str], goal: str) -> list[str]:
    clean = [item.strip() for item in features if item and item.strip()]
    if clean:
        return clean[:8]
    words = [part.strip(" .") for part in goal.replace(";", ",").split(",") if part.strip()]
    return words[:5] or ["core workflow", "key feature", "final result"]


def _annotate_project(project_path: Path, preset: BeginnerTemplate, staged: dict[str, Any], *, desired_vibe: str, target_platform: str, smart_defaults: dict[str, Any]) -> None:
    data = json.loads(project_path.read_text(encoding="utf-8"))
    metadata = data.setdefault("metadata", {})
    metadata["beginnerAutoTemplate"] = {
        "template": asdict(preset),
        "desiredVibe": desired_vibe,
        "targetPlatform": target_platform,
        "smartDefaults": smart_defaults,
        "jsonSourceOfTruth": True,
        "advancedModeAvailable": True,
        "stagedAssetCount": staged["assetCount"],
    }
    data["project"] = {
        **data.get("project", {}),
        "width": smart_defaults["width"],
        "height": smart_defaults["height"],
        "fps": smart_defaults["fps"],
        "exportPreset": smart_defaults["exportPreset"],
    }
    data["exportPreset"] = smart_defaults["exportPreset"]
    project_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _user_summary(preset: BeginnerTemplate, result: dict[str, Any], staged: dict[str, Any]) -> dict[str, Any]:
    return {
        "templateName": preset.name,
        "projectJsonHiddenByDefault": True,
        "assetCount": staged["assetCount"],
        "hook": result.get("hook"),
        "style": result.get("style"),
        "duration": result.get("duration"),
        "renderedVideo": result.get("renderPath"),
        "nextStep": "Review the preview, then render final quality when approved.",
    }


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
