from __future__ import annotations

import json
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any


def prepare_local_folders(base_dir: Path | None = None, *, output_path: Path | None = None) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    base = base_dir or root / "output" / "local_app_data"
    folders = {
        "projects": base / "projects",
        "assets": base / "assets",
        "cache": base / "cache",
        "models": base / "models",
        "exports": base / "exports",
        "logs": base / "logs",
        "docs": base / "docs",
        "plugins": base / "plugins",
    }
    for folder in folders.values():
        folder.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": "automatic-video-editor-local-folders",
        "createdAt": _now(),
        "baseDir": str(base.resolve()),
        "folders": {key: str(value.resolve()) for key, value in folders.items()},
        "localOnly": True,
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def create_first_run_setup(base_dir: Path | None = None, *, output_path: Path | None = None) -> dict[str, Any]:
    folders = prepare_local_folders(base_dir)
    setup = {
        "format": "automatic-video-editor-first-run-setup",
        "createdAt": _now(),
        "steps": [
            {"id": "privacy", "title": "Local privacy", "complete": True, "summary": "No accounts, telemetry, cloud render, or online sync are required."},
            {"id": "dependencies", "title": "Dependency check", "complete": False, "summary": "Run `python render.py dependency-check` to verify FFmpeg, codecs, fonts, and storage."},
            {"id": "folders", "title": "Local folders", "complete": True, "summary": folders["baseDir"]},
            {"id": "sample_project", "title": "Sample render", "complete": False, "summary": "Render examples/project.json to verify the pipeline."},
        ],
        "folders": folders["folders"],
    }
    output = output_path or Path(folders["folders"]["projects"]).parent / "first_run_setup.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(setup, indent=2) + "\n", encoding="utf-8")
    setup["path"] = str(output.resolve())
    return setup


def create_installer_manifest(*, bundled_ffmpeg: Path | None = None, output_path: Path | None = None) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    desktop = root / "desktop-app"
    manifest = {
        "format": "automatic-video-editor-installer-manifest",
        "createdAt": _now(),
        "platform": "windows",
        "localOnly": True,
        "buildCommands": {
            "desktopDependencies": "cd desktop-app && npm install",
            "windowsInstaller": "cd desktop-app && npm run dist",
            "portableZip": "python render.py installer portable",
        },
        "electronBuilder": {
            "config": str((desktop / "package.json").resolve()),
            "targets": ["nsis", "zip"],
            "publish": None,
        },
        "bundledFfmpeg": str(bundled_ffmpeg.resolve()) if bundled_ffmpeg else None,
        "requiredLocalFolders": prepare_local_folders()["folders"],
        "notes": [
            "Installer packaging is local-only and does not publish builds.",
            "Bundled FFmpeg is optional; system FFmpeg or imageio-ffmpeg can be used.",
        ],
    }
    output = output_path or root / "output" / "installer" / "installer_manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest["path"] = str(output.resolve())
    return manifest


def create_portable_zip(*, output_path: Path | None = None) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    output = output_path or root / "output" / "installer" / "automatic-video-editor-portable.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    include_roots = [
        root / "render.py",
        root / "README.md",
        root / "requirements.txt",
        root / "src",
        root / "examples" / "project.json",
        root / "examples" / "demos",
        root / "docs",
        root / "luts",
        root / "desktop-app" / "assets",
    ]
    entries = []
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in include_roots:
            if not item.exists():
                continue
            if item.is_file():
                archive.write(item, item.relative_to(root).as_posix())
                entries.append(item.relative_to(root).as_posix())
            else:
                for path in item.rglob("*"):
                    if _skip(path):
                        continue
                    if path.is_file():
                        archive.write(path, path.relative_to(root).as_posix())
                        entries.append(path.relative_to(root).as_posix())
    return {"path": str(output.resolve()), "entryCount": len(entries), "bytes": output.stat().st_size, "entries": entries[:50]}


def _skip(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    return "__pycache__" in parts or "node_modules" in parts or ".git" in parts or path.suffix.lower() in {".pyc", ".pyo"}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
