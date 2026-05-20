from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from metrics.store import summarize_metrics
from stability.dependencies import offline_dependency_report


def performance_dashboard_report(*, output_path: Path | None = None) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    deps = offline_dependency_report()
    metrics = summarize_metrics()
    caches = _cache_report(root / "output")
    report = {
        "format": "automatic-video-editor-performance-dashboard",
        "createdAt": _now(),
        "cpu": {"logicalCores": os.cpu_count() or 1},
        "memory": deps.get("memory", {}),
        "gpu": deps.get("gpu", {}),
        "render": {
            "renderCount": metrics.get("renderCount", 0),
            "averageRenderSeconds": metrics.get("averageRenderSeconds", 0),
            "averageOutputSize": metrics.get("averageOutputSize", 0),
        },
        "cache": caches,
        "modelUsage": _model_usage(root),
        "process": _process_memory(),
        "bottlenecks": _bottlenecks(deps, metrics, caches),
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _cache_report(output: Path) -> dict[str, Any]:
    buckets = []
    if output.exists():
        for folder in output.rglob("*"):
            if not folder.is_dir():
                continue
            lowered = folder.name.lower()
            if any(token in lowered for token in ("cache", "proxy", "thumbnail", "waveform", "preview")):
                buckets.append({"path": str(folder.resolve()), "bytes": _dir_size(folder)})
    total = sum(item["bytes"] for item in buckets)
    return {"bucketCount": len(buckets), "totalBytes": total, "buckets": sorted(buckets, key=lambda item: item["bytes"], reverse=True)[:25]}


def _model_usage(root: Path) -> dict[str, Any]:
    registry = root / "output" / "local_models" / "model_registry.json"
    if not registry.exists():
        return {"registry": str(registry), "configured": False, "selections": {}}
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
        return {"registry": str(registry), "configured": True, "selections": data.get("selections", {})}
    except json.JSONDecodeError:
        return {"registry": str(registry), "configured": False, "error": "registry JSON is unreadable"}


def _process_memory() -> dict[str, Any]:
    pid = os.getpid()
    try:
        result = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            fields = [part.strip().strip('"') for part in result.stdout.strip().split(",")]
            return {"pid": pid, "workingSet": fields[4] if len(fields) >= 5 else None, "source": "tasklist"}
    except Exception:
        pass
    return {"pid": pid, "workingSet": None, "source": "unavailable"}


def _bottlenecks(deps: dict[str, Any], metrics: dict[str, Any], caches: dict[str, Any]) -> list[str]:
    warnings = []
    if not deps.get("ffmpeg", {}).get("supportsGpuEncoding"):
        warnings.append("CPU encoding is active; enable GPU only after confirming encoder support.")
    if (deps.get("storage", {}).get("freeBytes") or 0) < 5 * 1024**3:
        warnings.append("Low free disk space can break cache and final exports.")
    if caches.get("totalBytes", 0) > 15 * 1024**3:
        warnings.append("Render/cache folders exceed 15 GB. Run cache cleanup soon.")
    if metrics.get("renderCount", 0) and metrics.get("averageRenderSeconds", 0) > 120:
        warnings.append("Average render time is high; use preview quality, proxies, or scene cache for iteration.")
    return warnings


def _dir_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
