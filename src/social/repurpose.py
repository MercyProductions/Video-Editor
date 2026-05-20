from __future__ import annotations

import copy
import json
import re
import time
from pathlib import Path
from typing import Any

from content.thumbnails import generate_thumbnail_set
from metrics.store import record_metric
from parser.project_parser import ProjectParser
from presets.export_presets import ExportPreset, get_export_preset
from renderer.renderer import VideoRenderer
from schema.validator import validate_project
from social.posting_package import create_posting_package


PLATFORM_PRESETS = {
    "youtube_shorts": "shorts",
    "tiktok": "tiktok_reels",
    "instagram_reels": "instagram_reels",
    "youtube_landscape": "youtube_1080p",
    "discord": "discord_720p",
    "x_twitter": "youtube_1080p",
}

PLATFORM_PACKAGES = {
    "youtube_shorts": "youtube_shorts",
    "tiktok": "tiktok",
    "instagram_reels": "instagram_reels",
    "youtube_landscape": "youtube_landscape",
    "discord": "discord",
    "x_twitter": "x_twitter",
}

ALIASES = {
    "all": "all",
    "shorts": "youtube_shorts",
    "youtube_shorts": "youtube_shorts",
    "youtube": "youtube_landscape",
    "youtube_landscape": "youtube_landscape",
    "youtube_1080p": "youtube_landscape",
    "tiktok": "tiktok",
    "reels": "instagram_reels",
    "instagram": "instagram_reels",
    "instagram_reels": "instagram_reels",
    "discord": "discord",
    "x": "x_twitter",
    "twitter": "x_twitter",
    "x_twitter": "x_twitter",
}

HOOK_VARIANTS = {
    "serious": "{product} fixes the blockers you cannot afford to miss.",
    "curiosity": "What is stopping {product} from launching cleanly?",
    "problem_solution": "Stop guessing. {product} finds the issue and shows the fix.",
    "fast_aggressive": "Scan. Detect. Fix. {product} moves fast.",
    "clean_professional": "{product} gives every troubleshooting step a cleaner path.",
}

CTA_VARIANTS = {
    "subscribe": "Subscribe for more clean troubleshooting workflows.",
    "visit_website": "Visit the site and try the workflow today.",
    "download": "Download {product} and run your first scan.",
    "comment": "Comment which blocker you want checked next.",
    "follow": "Follow for more product demos and creator tools.",
}


def repurpose_project(
    project_path: Path,
    *,
    output_dir: Path,
    platforms: list[str] | None = None,
    hook_variants: list[str] | None = None,
    cta_variants: list[str] | None = None,
    reuse_style: bool = True,
    render: bool = False,
    quality: str = "preview",
    package: bool = False,
    generate_placeholders: bool = False,
    max_variants: int | None = None,
) -> dict[str, Any]:
    project_path = project_path.resolve()
    output_dir = output_dir.resolve()
    source = _read_json(project_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    selected_platforms = _normalize_platforms(platforms or ["all"])
    selected_hooks = _normalize_variants(hook_variants, HOOK_VARIANTS)
    selected_ctas = _normalize_variants(cta_variants, CTA_VARIANTS)
    product = _product_name(source)
    outputs: list[dict[str, Any]] = []
    count = 0

    for platform in selected_platforms:
        preset = get_export_preset(PLATFORM_PRESETS[platform])
        base_variants = [("base", "default", None)]
        base_variants.extend(("hook", key, HOOK_VARIANTS[key].format(product=product)) for key in selected_hooks)
        base_variants.extend(("cta", key, CTA_VARIANTS[key].format(product=product)) for key in selected_ctas)
        for variant_type, variant_key, replacement in base_variants:
            if max_variants is not None and count >= max_variants:
                break
            project = _platform_project(
                source,
                source_path=project_path,
                platform=platform,
                preset=preset,
                variant_type=variant_type,
                variant_key=variant_key,
                replacement=replacement,
                reuse_style=reuse_style,
            )
            variant_dir = output_dir / platform / _variant_folder(variant_type, variant_key)
            variant_dir.mkdir(parents=True, exist_ok=True)
            project_json = variant_dir / "project.json"
            _relocate_assets_for_output(project, project_path, project_json)
            validate_project(project)
            _write_json(project_json, project)
            item: dict[str, Any] = {
                "platform": platform,
                "preset": preset.key,
                "variantType": variant_type,
                "variant": variant_key,
                "projectPath": str(project_json.resolve()),
                "folder": str(variant_dir.resolve()),
                "renderedVideo": None,
                "packageDir": None,
                "thumbnailReport": None,
            }
            if render:
                video_path = _render_variant(project_json, variant_dir, quality=quality, generate_placeholders=generate_placeholders)
                item["renderedVideo"] = str(video_path.resolve())
                item["thumbnailReport"] = generate_thumbnail_set(video_path, title=_variant_title(project, product), output_dir=variant_dir / "thumbnails", accent_color=_accent_color(project)).get("reportPath")
                if package:
                    package_dir = variant_dir / "upload_package"
                    create_posting_package(project_json, video_path, output_dir=package_dir, platforms=[PLATFORM_PACKAGES[platform]], title=_variant_title(project, product))
                    item["packageDir"] = str(package_dir.resolve())
            outputs.append(item)
            count += 1
        if max_variants is not None and count >= max_variants:
            break

    summary = {
        "repurposeVersion": 1,
        "localOnly": True,
        "createdAt": _now(),
        "sourceProject": str(project_path),
        "outputDir": str(output_dir),
        "platforms": selected_platforms,
        "hookVariants": selected_hooks,
        "ctaVariants": selected_ctas,
        "reuseStyle": reuse_style,
        "rendered": render,
        "packaged": package and render,
        "count": len(outputs),
        "outputs": outputs,
    }
    _write_json(output_dir / "repurpose_summary.json", summary)
    record_metric("content_repurpose", {"platforms": len(selected_platforms), "variants": len(outputs), "rendered": render})
    return summary


def _platform_project(
    source: dict[str, Any],
    *,
    source_path: Path,
    platform: str,
    preset: ExportPreset,
    variant_type: str,
    variant_key: str,
    replacement: str | None,
    reuse_style: bool,
) -> dict[str, Any]:
    project = copy.deepcopy(source)
    project["exportPreset"] = preset.key
    project["project"] = {
        **project.get("project", {}),
        "width": preset.width,
        "height": preset.height,
        "fps": preset.fps,
        "crf": preset.crf,
        "duration": min(_project_duration(project), _duration_cap(platform)),
    }
    if project["project"]["duration"] < _project_duration(project):
        _trim_project(project, float(project["project"]["duration"]))
    _adapt_layers(project, preset, platform)
    if variant_type == "hook" and replacement:
        _replace_first_text(project, replacement)
    elif variant_type == "cta" and replacement:
        _replace_last_text(project, replacement)
    metadata = project.setdefault("metadata", {})
    metadata["repurpose"] = {
        "sourceProject": str(source_path),
        "platform": platform,
        "preset": preset.key,
        "variantType": variant_type,
        "variant": variant_key,
        "reuseStyle": reuse_style,
        "safeZones": _safe_zones(preset),
        "thumbnailIntent": _thumbnail_intent(platform, variant_type, variant_key),
    }
    if not reuse_style:
        metadata.pop("brandKit", None)
        metadata.pop("lighting", None)
        project.pop("stylePreset", None)
    return project


def _adapt_layers(project: dict[str, Any], preset: ExportPreset, platform: str) -> None:
    vertical = preset.height > preset.width
    square = preset.height == preset.width
    for scene in project.get("timeline", []) or []:
        scene_duration = float(scene.get("duration", 0) or 0)
        for layer in scene.get("layers", []) or []:
            if layer.get("type") in {"video", "image"}:
                layer["x"] = 0
                layer["y"] = 0
                layer["width"] = preset.width
                layer["height"] = preset.height
                layer["autoFit"] = "cover" if vertical or square else "contain"
                layer.setdefault("framing", {"mode": "smart_center", "safe": True})
            if layer.get("type") in {"text", "caption", "captions"}:
                layer["x"] = "center"
                layer["maxWidth"] = int(preset.width * (0.82 if vertical else 0.72))
                layer["safeZone"] = "shorts_caption" if vertical else "landscape_title_safe"
                if vertical:
                    layer["y"] = int(preset.height * 0.72)
                    layer["fontSize"] = min(76, max(48, int(float(layer.get("fontSize", 58) or 58))))
                    layer["strokeWidth"] = max(3, int(float(layer.get("strokeWidth", 2) or 2)))
                    layer.setdefault("background", {"color": "#000000", "opacity": 0.32, "padding": 18})
                elif square:
                    layer["y"] = int(preset.height * 0.72)
                    layer["fontSize"] = min(58, max(38, int(float(layer.get("fontSize", 48) or 48))))
                else:
                    layer["y"] = min(int(preset.height * 0.78), int(layer.get("y", preset.height * 0.72) if isinstance(layer.get("y"), (int, float)) else preset.height * 0.72))
                    layer["fontSize"] = min(64, max(34, int(float(layer.get("fontSize", 48) or 48))))
                if layer.get("type") == "captions":
                    for item in layer.get("items", []) or []:
                        item["duration"] = max(float(item.get("duration", 1.2) or 1.2), 1.1 if platform != "discord" else 1.4)
            if scene_duration and float(layer.get("start", 0) or 0) > scene_duration:
                layer["start"] = max(0, scene_duration - 0.2)


def _render_variant(project_json: Path, output_dir: Path, *, quality: str, generate_placeholders: bool) -> Path:
    parsed = ProjectParser().load(project_json)
    output = output_dir / "final_video.mp4"
    VideoRenderer(
        parsed,
        output_path=output,
        quality=quality,
        use_cache=True,
        resume=True,
        generate_placeholders=generate_placeholders,
    ).render()
    return output


def _trim_project(project: dict[str, Any], target: float) -> None:
    start = 0.0
    timeline = []
    for scene in project.get("timeline", []) or []:
        duration = float(scene.get("duration", 0) or 0)
        if start >= target:
            break
        item = copy.deepcopy(scene)
        item["start"] = round(start, 3)
        item["duration"] = round(min(duration, max(0.4, target - start)), 3)
        timeline.append(item)
        start += float(item["duration"])
    project["timeline"] = timeline
    project.setdefault("project", {})["duration"] = round(start, 3)


def _replace_first_text(project: dict[str, Any], text: str) -> None:
    for scene in project.get("timeline", []) or []:
        for layer in scene.get("layers", []) or []:
            if layer.get("type") == "text" and layer.get("text"):
                layer["text"] = text
                return


def _replace_last_text(project: dict[str, Any], text: str) -> None:
    for scene in reversed(project.get("timeline", []) or []):
        for layer in reversed(scene.get("layers", []) or []):
            if layer.get("type") == "text" and layer.get("text"):
                layer["text"] = text
                return


def _normalize_platforms(platforms: list[str]) -> list[str]:
    result = []
    for platform in platforms:
        key = ALIASES.get(platform.strip().lower().replace("-", "_").replace("/", "_"), platform)
        if key == "all":
            return list(PLATFORM_PRESETS)
        if key not in PLATFORM_PRESETS:
            raise ValueError(f"Unknown repurpose platform '{platform}'. Valid platforms: {', '.join(PLATFORM_PRESETS)}")
        if key not in result:
            result.append(key)
    return result or list(PLATFORM_PRESETS)


def _normalize_variants(values: list[str] | None, catalog: dict[str, str]) -> list[str]:
    if not values:
        return list(catalog)
    result = []
    for value in values:
        if value == "all":
            return list(catalog)
        key = value.strip().lower().replace("-", "_").replace("/", "_")
        if key not in catalog:
            raise ValueError(f"Unknown variant '{value}'. Valid variants: {', '.join(catalog)}")
        if key not in result:
            result.append(key)
    return result


def _duration_cap(platform: str) -> float:
    return {
        "youtube_shorts": 60.0,
        "tiktok": 60.0,
        "instagram_reels": 90.0,
        "youtube_landscape": 7200.0,
        "discord": 600.0,
        "x_twitter": 140.0,
    }[platform]


def _safe_zones(preset: ExportPreset) -> dict[str, int]:
    return {
        "left": int(preset.width * 0.08),
        "right": int(preset.width * 0.92),
        "top": int(preset.height * 0.09),
        "bottom": int(preset.height * 0.86),
    }


def _thumbnail_intent(platform: str, variant_type: str, variant_key: str) -> dict[str, Any]:
    return {
        "platform": platform,
        "layout": "vertical_title_safe" if platform in {"youtube_shorts", "tiktok", "instagram_reels"} else "landscape_center_title",
        "variant": f"{variant_type}:{variant_key}",
        "generateOnRender": True,
    }


def _project_duration(project: dict[str, Any]) -> float:
    duration = project.get("project", {}).get("duration")
    if duration:
        return float(duration)
    end = 0.0
    for scene in project.get("timeline", []) or []:
        end = max(end, float(scene.get("start", 0) or 0) + float(scene.get("duration", 0) or 0))
    return round(end, 3)


def _product_name(project: dict[str, Any]) -> str:
    metadata = project.get("metadata", {}) if isinstance(project.get("metadata"), dict) else {}
    content = metadata.get("contentGenerator", {}) if isinstance(metadata.get("contentGenerator"), dict) else {}
    brief = content.get("contentBrief", {}) if isinstance(content.get("contentBrief"), dict) else {}
    return str(brief.get("productName") or metadata.get("productName") or metadata.get("title") or "this product")


def _variant_title(project: dict[str, Any], product: str) -> str:
    metadata = project.get("metadata", {}).get("repurpose", {})
    return f"{product} {str(metadata.get('platform', 'variant')).replace('_', ' ').title()}"


def _accent_color(project: dict[str, Any]) -> str:
    metadata = project.get("metadata", {}) if isinstance(project.get("metadata"), dict) else {}
    content = metadata.get("contentGenerator", {}) if isinstance(metadata.get("contentGenerator"), dict) else {}
    brief = content.get("contentBrief", {}) if isinstance(content.get("contentBrief"), dict) else {}
    theme = brief.get("theme", {}) if isinstance(brief.get("theme"), dict) else {}
    return str(theme.get("accent") or "#ef4444")


def _variant_folder(variant_type: str, variant_key: str) -> str:
    return "base" if variant_type == "base" else f"{variant_type}_{variant_key}"


def _relocate_assets_for_output(data: dict[str, Any], source_project_path: Path, output_path: Path) -> None:
    if source_project_path.parent.resolve() == output_path.parent.resolve():
        return
    for key, value in list((data.get("assets", {}) or {}).items()):
        raw = Path(str(value))
        if not raw.is_absolute():
            data["assets"][key] = str((source_project_path.parent / raw).resolve())


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_") or "item"
