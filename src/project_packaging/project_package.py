from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any


def export_project_package(project_path: Path, output_path: Path) -> dict[str, Any]:
    project_path = project_path.resolve()
    output_path = output_path.resolve()
    with project_path.open("r", encoding="utf-8") as handle:
        project = json.load(handle)
    packaged_project = json.loads(json.dumps(project))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "format": "automatic-video-editor-local-project-package",
        "version": 1,
        "projectFile": "project.json",
        "assets": [],
        "includedReports": [],
        "templatesUsed": _templates_used(project),
        "versionHistory": [],
        "thumbnails": [],
    }
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        packaged_assets = packaged_project.setdefault("assets", {})
        for key, raw in (project.get("assets", {}) or {}).items():
            source = Path(str(raw))
            source = source if source.is_absolute() else project_path.parent / source
            if source.exists() and source.is_file():
                target = f"assets/{key}{source.suffix.lower()}"
                archive.write(source, target)
                packaged_assets[key] = target
                manifest["assets"].append({"key": key, "path": target, "source": str(source.resolve())})
        archive.writestr("project.json", json.dumps(packaged_project, indent=2) + "\n")
        for report in _report_candidates(project_path):
            if report.exists():
                target = f"reports/{report.name}"
                archive.write(report, target)
                manifest["includedReports"].append(target)
        for thumbnail in _thumbnail_candidates(project_path):
            target = f"thumbnails/{thumbnail.name}"
            archive.write(thumbnail, target)
            manifest["thumbnails"].append(target)
        history_dir = project_path.parent / ".ave_history"
        if history_dir.exists():
            for item in history_dir.rglob("*"):
                if item.is_file():
                    target = f"version_history/{item.relative_to(history_dir).as_posix()}"
                    archive.write(item, target)
                    manifest["versionHistory"].append(target)
        archive.writestr("package_manifest.json", json.dumps(manifest, indent=2) + "\n")
    manifest["packagePath"] = str(output_path)
    return manifest


def open_project_package(package_path: Path, output_dir: Path) -> dict[str, Any]:
    package_path = package_path.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package_path, "r") as archive:
        archive.extractall(output_dir)
    manifest_path = output_dir / "package_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    manifest["openedTo"] = str(output_dir)
    manifest["projectPath"] = str(output_dir / manifest.get("projectFile", "project.json"))
    return manifest


def _templates_used(project: dict[str, Any]) -> list[str]:
    metadata = project.get("metadata", {})
    values = []
    if isinstance(metadata, dict):
        for key in ("template", "templateKey", "sourceTemplate"):
            if metadata.get(key):
                values.append(str(metadata[key]))
    return sorted(set(values))


def _report_candidates(project_path: Path) -> list[Path]:
    root = project_path.parents[1] if project_path.parent.name == "generated" else project_path.parent
    return [
        project_path.with_suffix(".director_report.json"),
        root / "output" / "render_report.json",
        root / "output" / "timeline_summary.json",
        root / "output" / "render_plan.txt",
    ]


def _thumbnail_candidates(project_path: Path) -> list[Path]:
    root = project_path.parents[1] if project_path.parent.name == "generated" else project_path.parent
    candidates = []
    for folder in [project_path.parent, root / "output", root / "output" / "thumbnails"]:
        if folder.exists():
            candidates.extend(path for path in folder.glob("*") if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and "thumb" in path.stem.lower())
    return sorted(set(candidates))
