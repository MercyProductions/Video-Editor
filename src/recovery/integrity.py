from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from assets.resolver import AssetResolver
from parser.project_parser import ProjectParser
from schema.validator import ProjectValidationError, validate_project


def check_project_integrity(project_path: Path, *, output_path: Path | None = None) -> dict[str, Any]:
    project_path = project_path.resolve()
    issues = []
    data: dict[str, Any] | None = None
    try:
        data = json.loads(project_path.read_text(encoding="utf-8"))
        validate_project(data)
    except json.JSONDecodeError as exc:
        issues.append({"severity": "error", "type": "json", "message": str(exc)})
    except ProjectValidationError as exc:
        issues.append({"severity": "error", "type": "schema", "message": str(exc)})

    assets = []
    if data:
        project = ProjectParser().load(project_path)
        resolver = AssetResolver(project, generate_missing=False)
        assets = resolver.asset_usage_report()
        for asset in assets:
            if not asset.get("exists"):
                issues.append({"severity": "error", "type": "missing_asset", "asset": asset["key"], "path": asset["resolvedPath"]})
        _check_timeline(issues, data)

    report = {
        "project": str(project_path),
        "valid": not any(issue["severity"] == "error" for issue in issues),
        "issueCount": len(issues),
        "issues": issues,
        "assetCount": len(assets),
        "missingAssetCount": sum(1 for asset in assets if not asset.get("exists")),
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def relink_missing_assets(project_path: Path, search_folder: Path, *, output_path: Path | None = None) -> dict[str, Any]:
    data = json.loads(project_path.read_text(encoding="utf-8"))
    assets = data.get("assets", {})
    if not isinstance(assets, dict):
        raise ValueError("Project assets must be an object before relinking.")
    candidates = {path.name.lower(): path for path in search_folder.rglob("*") if path.is_file()}
    relinked = []
    for key, value in list(assets.items()):
        raw = Path(str(value))
        resolved = raw if raw.is_absolute() else project_path.parent / raw
        if resolved.exists():
            continue
        match = candidates.get(raw.name.lower())
        if not match:
            continue
        try:
            assets[key] = str(match.resolve().relative_to(project_path.parent.resolve())).replace("\\", "/")
        except ValueError:
            assets[key] = str(match.resolve())
        relinked.append({"asset": key, "old": str(value), "new": assets[key]})
    output = output_path or project_path.with_name(f"{project_path.stem}.relinked.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {"project": str(project_path.resolve()), "output": str(output.resolve()), "relinkedCount": len(relinked), "relinked": relinked}


def _check_timeline(issues: list[dict[str, Any]], data: dict[str, Any]) -> None:
    cursor = 0.0
    for scene in data.get("timeline", []):
        start = float(scene.get("start", 0) or 0)
        duration = float(scene.get("duration", 0) or 0)
        if abs(start - cursor) > 0.05:
            issues.append({"severity": "warning", "type": "timeline_gap", "scene": scene.get("id"), "message": f"Expected start {cursor:.3f}, found {start:.3f}."})
        if duration <= 0:
            issues.append({"severity": "error", "type": "timeline_duration", "scene": scene.get("id"), "message": "Scene duration must be positive."})
        cursor = start + max(duration, 0)
