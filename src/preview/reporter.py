from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from assets.resolver import AssetResolver
from parser.models import ProjectConfig


@dataclass(slots=True)
class PreviewResult:
    output_dir: Path
    summary_path: Path
    plan_path: Path
    summary: dict[str, Any]


def generate_preview(
    project: ProjectConfig,
    *,
    output_dir: Path | None = None,
    generate_placeholders: bool = False,
) -> PreviewResult:
    output_dir = output_dir or (Path(__file__).resolve().parents[2] / "output")
    output_dir.mkdir(parents=True, exist_ok=True)
    resolver = AssetResolver(project, generate_missing=generate_placeholders)
    assets = resolver.asset_usage_report()

    scenes = []
    estimated_duration = 0.0
    for scene in project.timeline:
        estimated_duration = max(estimated_duration, scene.start + scene.duration)
        scenes.append(
            {
                "id": scene.id,
                "start": scene.start,
                "duration": scene.duration,
                "layers": [
                    {
                        "type": layer.type,
                        "asset": layer.raw.get("asset"),
                        "text": layer.raw.get("text"),
                        "start": layer.raw.get("start", 0),
                        "duration": layer.raw.get("duration", scene.duration),
                    }
                    for layer in scene.layers
                ],
                "transitionOut": scene.transition_out,
            }
        )

    summary = {
        "project": {
            "file": str(project.path),
            "width": project.settings.width,
            "height": project.settings.height,
            "fps": project.settings.fps,
            "duration": project.settings.duration,
            "exportPreset": project.export_preset,
        },
        "estimatedTimelineDuration": round(estimated_duration, 3),
        "sceneCount": len(project.timeline),
        "audioTrackCount": len(project.audio),
        "scenes": scenes,
        "assets": assets,
        "missingAssets": [asset for asset in assets if not asset["exists"]],
    }

    summary_path = output_dir / "timeline_summary.json"
    plan_path = output_dir / "render_plan.txt"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
        handle.write("\n")
    with plan_path.open("w", encoding="utf-8") as handle:
        handle.write(_render_plan_text(summary))
    return PreviewResult(output_dir=output_dir, summary_path=summary_path, plan_path=plan_path, summary=summary)


def _render_plan_text(summary: dict[str, Any]) -> str:
    project = summary["project"]
    lines = [
        "Automatic Video Editor Render Plan",
        "=" * 36,
        f"Project: {project['file']}",
        f"Export: {project['width']}x{project['height']} at {project['fps']}fps",
        f"Preset: {project.get('exportPreset') or 'custom'}",
        f"Declared duration: {project['duration']}s",
        f"Estimated timeline duration: {summary['estimatedTimelineDuration']}s",
        "",
        "Scenes:",
    ]
    for scene in summary["scenes"]:
        lines.append(f"- {scene['id']} start={scene['start']}s duration={scene['duration']}s")
        for layer in scene["layers"]:
            detail = layer.get("asset") or layer.get("text") or ""
            lines.append(f"  - {layer['type']} {detail}")
        if scene.get("transitionOut"):
            lines.append(f"  - transitionOut {scene['transitionOut']}")
    lines.extend(["", "Assets:"])
    for asset in summary["assets"]:
        status = "ok" if asset["exists"] else "missing"
        lines.append(f"- [{status}] {asset['asset']} ({asset['mediaType']}): {asset.get('resolvedPath')}")
    if summary["missingAssets"]:
        lines.extend(["", "Missing assets detected. Re-run with --generate-placeholders for test media."])
    return "\n".join(lines) + "\n"
