from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path
from typing import Any


PACK_TYPES = {
    "template": ".templatepack",
    "effect": ".effectpack",
    "transition": ".transitionpack",
    "creator": ".creatorpack",
    "brandkit": ".brandkitpack",
    "caption": ".captionpack",
    "motion": ".motionpack",
    "export_preset": ".presetpack",
    "automation": ".automationpack",
}


def default_pack_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "examples" / "packs"


def export_pack(source: Path, *, pack_type: str, output_path: Path | None = None, name: str | None = None, author: str = "local") -> dict[str, Any]:
    if pack_type not in PACK_TYPES:
        raise ValueError(f"Unsupported pack type '{pack_type}'. Expected one of: {', '.join(sorted(PACK_TYPES))}")
    source = source.resolve()
    pack_name = name or source.stem
    output_path = output_path or (default_pack_dir() / f"{_slug(pack_name)}{PACK_TYPES[pack_type]}")
    manifest = {
        "format": f"automatic-video-editor-{pack_type}-pack",
        "version": 1,
        "name": pack_name,
        "type": pack_type,
        "author": author,
        "createdAt": _now(),
        "sourceName": source.name,
        "entries": _entries(source),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("pack_manifest.json", json.dumps(manifest, indent=2) + "\n")
        if source.is_dir():
            for path in source.rglob("*"):
                if path.is_file():
                    archive.write(path, f"payload/{path.relative_to(source).as_posix()}")
        else:
            archive.write(source, f"payload/{source.name}")
    manifest["path"] = str(output_path.resolve())
    return manifest


def import_pack(package_path: Path, *, install_dir: Path | None = None) -> dict[str, Any]:
    package_path = package_path.resolve()
    with zipfile.ZipFile(package_path, "r") as archive:
        manifest = json.loads(archive.read("pack_manifest.json").decode("utf-8"))
        pack_type = manifest.get("type", "unknown")
        target = (install_dir or default_pack_dir() / "installed") / pack_type / _slug(str(manifest.get("name", package_path.stem)))
        target.mkdir(parents=True, exist_ok=True)
        archive.extractall(target)
    manifest["installedTo"] = str(target.resolve())
    manifest["packagePath"] = str(package_path)
    return manifest


def list_installed_packs(root: Path | None = None) -> list[dict[str, Any]]:
    root = root or default_pack_dir()
    rows = []
    for manifest_path in sorted(root.rglob("pack_manifest.json")):
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        data["path"] = str(manifest_path.parent.resolve())
        rows.append(data)
    return rows


def _entries(source: Path) -> list[dict[str, Any]]:
    if source.is_file():
        return [{"path": source.name, "size": source.stat().st_size}]
    return [{"path": path.relative_to(source).as_posix(), "size": path.stat().st_size} for path in sorted(source.rglob("*")) if path.is_file()]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "pack"
