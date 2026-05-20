from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any


CACHE_TOKENS = ("cache", "proxy", "thumbnail", "waveform", "preview")


def cache_report(root: Path | None = None, *, output_path: Path | None = None) -> dict[str, Any]:
    project_root = Path(__file__).resolve().parents[2]
    scan_root = root or project_root / "output"
    buckets = _buckets(scan_root)
    report = {
        "format": "automatic-video-editor-cache-report",
        "createdAt": _now(),
        "root": str(scan_root.resolve()),
        "bucketCount": len(buckets),
        "totalBytes": sum(item["bytes"] for item in buckets),
        "buckets": buckets,
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def cleanup_caches(root: Path | None = None, *, max_bytes: int = 5 * 1024**3, dry_run: bool = False) -> dict[str, Any]:
    project_root = Path(__file__).resolve().parents[2]
    scan_root = root or project_root / "output"
    buckets = sorted(_buckets(scan_root), key=lambda item: item["modifiedAtEpoch"])
    total = sum(item["bytes"] for item in buckets)
    deleted = []
    for bucket in buckets:
        if total <= max_bytes:
            break
        path = Path(bucket["path"])
        if not dry_run:
            shutil.rmtree(path, ignore_errors=True)
        total -= int(bucket["bytes"])
        deleted.append(bucket)
    return {
        "root": str(scan_root.resolve()),
        "dryRun": dry_run,
        "maxBytes": max_bytes,
        "deletedCount": len(deleted),
        "deletedBytes": sum(item["bytes"] for item in deleted),
        "remainingBytes": max(total, 0),
        "deleted": deleted,
    }


def _buckets(root: Path) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    buckets = []
    for folder in root.rglob("*"):
        if not folder.is_dir():
            continue
        lowered = folder.name.lower()
        if not any(token in lowered for token in CACHE_TOKENS):
            continue
        stat = folder.stat()
        buckets.append(
            {
                "path": str(folder.resolve()),
                "bytes": _dir_size(folder),
                "modifiedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stat.st_mtime)),
                "modifiedAtEpoch": stat.st_mtime,
            }
        )
    return sorted(buckets, key=lambda item: item["bytes"], reverse=True)


def _dir_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
