from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from templates.catalog import create_project_from_template, list_templates, template_names


def template_pack_catalog() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for template in list_templates():
        key = str(template["key"])
        rows.append(
            {
                "key": key,
                "name": template["name"],
                "author": "Aegis",
                "version": "1.0.0",
                "tags": _tags_for(key),
                "previewThumbnail": f"packs/thumbnails/{key}.png",
                "requiredAssets": template["requiredAssets"],
                "exportPreset": template["exportPreset"],
                "transitionStyle": template["transitionStyle"],
                "installState": "bundled",
            }
        )
    return rows


def export_template_pack(template_name: str, output_zip: Path) -> dict[str, Any]:
    template = create_project_from_template(template_name)
    metadata = next((item for item in template_pack_catalog() if item["key"] == template_name), None)
    if not metadata:
        raise KeyError(f"Unknown template pack: {template_name}")

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ave_template_pack_") as temp_dir:
        root = Path(temp_dir)
        (root / "template.json").write_text(json.dumps(template, indent=2), encoding="utf-8")
        (root / "pack.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in root.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(root))
    return {"path": str(output_zip.resolve()), "metadata": metadata}


def install_template_pack(package_zip: Path, output_dir: Path | None = None) -> dict[str, Any]:
    if not package_zip.exists():
        raise FileNotFoundError(f"Template pack does not exist: {package_zip}")
    target = output_dir or Path("templates/installed").resolve()
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(package_zip, "r") as archive:
        archive.extractall(target)
    metadata_path = target / "pack.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    if output_dir is None:
        archive_copy = target / package_zip.name
        shutil.copy2(package_zip, archive_copy)
    return {"installedTo": str(target.resolve()), "metadata": metadata}


def _tags_for(key: str) -> list[str]:
    lookup = {
        "youtube_intro": ["youtube", "intro", "creator"],
        "tiktok_reels_short": ["vertical", "shorts", "captions"],
        "gaming_montage": ["gaming", "fast", "montage"],
        "product_promo": ["product", "promo", "square"],
        "lyric_video": ["music", "lyrics", "karaoke"],
        "slideshow": ["photos", "memory", "simple"],
        "meme_edit": ["meme", "reaction", "square"],
        "tutorial_video": ["tutorial", "screen", "education"],
    }
    return lookup.get(key, ["template"])
