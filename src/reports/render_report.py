from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from assets.resolver import AssetResolver
from media.compat import export_format_from_path
from parser.models import ProjectConfig


def build_render_report(
    project: ProjectConfig,
    output_path: Path,
    *,
    render_time_seconds: float,
    warnings: list[str],
    missing_assets: list[dict[str, Any]],
    quality: str,
    cache_enabled: bool,
    gpu_enabled: bool,
) -> Path:
    resolver = AssetResolver(project)
    assets = resolver.asset_usage_report()
    report = {
        "output": str(output_path.resolve()),
        "outputFormat": export_format_from_path(output_path),
        "outputFileSize": _output_size(output_path),
        "totalDuration": project.settings.duration,
        "resolution": {"width": project.settings.width, "height": project.settings.height, "fps": project.settings.fps},
        "quality": quality,
        "cacheEnabled": cache_enabled,
        "gpuEnabled": gpu_enabled,
        "renderTimeSeconds": round(render_time_seconds, 3),
        "assetsUsed": assets,
        "missingAssets": missing_assets or [asset for asset in assets if not asset["exists"]],
        "effectsUsed": _effects_used(project),
        "sceneCount": len(project.timeline),
        "warnings": warnings,
    }
    report_path = output_path.parent / "render_report.json"
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    return report_path


def _output_size(output_path: Path) -> int:
    if output_path.exists():
        return output_path.stat().st_size
    if "%" in output_path.name:
        prefix = output_path.name.split("%", 1)[0]
        suffix = output_path.suffix
        return sum(path.stat().st_size for path in output_path.parent.glob(f"{prefix}*{suffix}") if path.is_file())
    return 0


def _effects_used(project: ProjectConfig) -> list[str]:
    effects: set[str] = set()
    for scene in project.timeline:
        if scene.transition_out:
            effects.add(f"transition:{scene.transition_out.get('type', 'cut')}")
        for layer in scene.layers:
            raw = layer.raw
            if raw.get("animation"):
                animation = raw["animation"]
                if isinstance(animation, str):
                    effects.add(f"animation:{animation}")
                elif isinstance(animation, dict):
                    for key in ("in", "out"):
                        if animation.get(key):
                            effects.add(f"animation:{animation[key]}")
            layer_effects = raw.get("effects")
            if isinstance(layer_effects, str):
                effects.add(f"effect:{layer_effects}")
            elif isinstance(layer_effects, list):
                for effect in layer_effects:
                    effects.add(f"effect:{effect}")
            for prop in ("blur", "brightness", "contrast", "opacity", "speed"):
                if prop in raw:
                    effects.add(f"media:{prop}")
    return sorted(effects)
