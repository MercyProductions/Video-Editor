from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


CURRENT_PROJECT_FORMAT = "0.6.0"


def generate_project_manifest(project_path: Path, *, output_path: Path | None = None) -> dict[str, Any]:
    project_path = project_path.resolve()
    data = json.loads(project_path.read_text(encoding="utf-8"))
    assets = []
    for key, value in (data.get("assets", {}) or {}).items():
        raw = Path(str(value))
        path = raw if raw.is_absolute() else project_path.parent / raw
        assets.append(
            {
                "key": key,
                "configuredPath": str(value),
                "resolvedPath": str(path.resolve()),
                "exists": path.exists(),
                "sha256": _sha256(path) if path.exists() and path.is_file() else None,
                "size": path.stat().st_size if path.exists() and path.is_file() else 0,
                "portable": not raw.is_absolute(),
            }
        )
    manifest = {
        "format": "automatic-video-editor-project",
        "formatVersion": CURRENT_PROJECT_FORMAT,
        "projectFile": str(project_path),
        "schema": "https://automatic-video-editor.local/project.schema.json",
        "declaredCompatibility": data.get("metadata", {}).get("formatVersion"),
        "assetCount": len(assets),
        "assets": assets,
        "checks": check_portability(project_path, data=data),
    }
    output_path = output_path or project_path.with_name("project_manifest.json")
    output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest["manifestPath"] = str(output_path.resolve())
    return manifest


def check_portability(project_path: Path, *, data: dict[str, Any] | None = None) -> dict[str, Any]:
    project_path = project_path.resolve()
    data = data or json.loads(project_path.read_text(encoding="utf-8"))
    issues = []
    for key, value in (data.get("assets", {}) or {}).items():
        raw = Path(str(value))
        path = raw if raw.is_absolute() else project_path.parent / raw
        if raw.is_absolute():
            issues.append({"severity": "warning", "asset": key, "message": "Asset uses an absolute path; package before sharing."})
        if not path.exists():
            issues.append({"severity": "error", "asset": key, "message": "Asset is missing and needs recovery."})
    declared = data.get("metadata", {}).get("formatVersion")
    if declared and str(declared) > CURRENT_PROJECT_FORMAT:
        issues.append({"severity": "error", "message": f"Project requires newer format {declared}; current is {CURRENT_PROJECT_FORMAT}."})
    return {
        "portable": not any(issue["severity"] == "error" for issue in issues),
        "versionCompatible": not any("newer format" in issue.get("message", "") for issue in issues),
        "missingAssetRecovery": [issue for issue in issues if issue.get("asset") and issue["severity"] == "error"],
        "issues": issues,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
