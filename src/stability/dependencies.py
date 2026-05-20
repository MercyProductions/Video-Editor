from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from utils.media import ffmpeg_binary


GPU_ENCODERS = {
    "nvidia": ["h264_nvenc", "hevc_nvenc", "av1_nvenc"],
    "intel": ["h264_qsv", "hevc_qsv", "av1_qsv"],
    "amd": ["h264_amf", "hevc_amf", "av1_amf"],
}


def offline_dependency_report(*, output_path: Path | None = None) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    report = {
        "format": "automatic-video-editor-offline-dependency-report",
        "createdAt": _now(),
        "localOnly": True,
        "system": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "machine": platform.machine(),
        },
        "ffmpeg": _ffmpeg_report(),
        "fonts": _font_report(),
        "storage": _storage_report(root),
        "memory": _ram_report(),
        "gpu": _gpu_report(),
    }
    report["readiness"] = _readiness(report)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _ffmpeg_report() -> dict[str, Any]:
    try:
        binary = ffmpeg_binary()
    except Exception as exc:
        return {"installed": False, "error": str(exc), "encoders": [], "codecs": [], "gpuEncoders": {}}
    version = _run([binary, "-version"], timeout=8)
    encoders_text = _run([binary, "-hide_banner", "-encoders"], timeout=10)["stdout"]
    codecs_text = _run([binary, "-hide_banner", "-codecs"], timeout=10)["stdout"]
    encoders = sorted(set(re.findall(r"\s([a-zA-Z0-9_]+)\s+", encoders_text)))
    codecs = sorted(set(re.findall(r"\s([a-zA-Z0-9_]+)\s+", codecs_text)))[:400]
    gpu = {vendor: [encoder for encoder in names if encoder in encoders_text] for vendor, names in GPU_ENCODERS.items()}
    return {
        "installed": True,
        "binary": binary,
        "version": (version["stdout"] or version["stderr"]).splitlines()[0] if (version["stdout"] or version["stderr"]) else "",
        "encoders": encoders[:500],
        "codecs": codecs,
        "gpuEncoders": gpu,
        "supportsGpuEncoding": any(gpu.values()),
    }


def _font_report() -> dict[str, Any]:
    roots = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
        Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts",
    ]
    fonts = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.glob("*"):
            if path.suffix.lower() in {".ttf", ".otf", ".ttc"}:
                fonts.append({"name": path.stem, "path": str(path.resolve())})
    return {"fontRoots": [str(root) for root in roots], "fontCount": len(fonts), "sample": fonts[:20], "available": bool(fonts)}


def _storage_report(root: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(root)
    return {
        "path": str(root.resolve()),
        "totalBytes": usage.total,
        "usedBytes": usage.used,
        "freeBytes": usage.free,
        "freeGb": round(usage.free / (1024**3), 2),
    }


def _ram_report() -> dict[str, Any]:
    result = _run(["wmic", "OS", "get", "FreePhysicalMemory,TotalVisibleMemorySize", "/Value"], timeout=5)
    if result["returnCode"] == 0:
        values: dict[str, int] = {}
        for line in result["stdout"].splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                if value.strip().isdigit():
                    values[key.strip()] = int(value.strip()) * 1024
        if values:
            total = values.get("TotalVisibleMemorySize")
            free = values.get("FreePhysicalMemory")
            return {"available": True, "totalBytes": total, "freeBytes": free, "source": "wmic"}
    return {"available": False, "totalBytes": None, "freeBytes": None, "source": "unavailable"}


def _gpu_report() -> dict[str, Any]:
    result = _run(["wmic", "path", "win32_VideoController", "get", "Name,AdapterRAM", "/format:list"], timeout=5)
    adapters = []
    current: dict[str, Any] = {}
    if result["returnCode"] == 0:
        for line in result["stdout"].splitlines():
            if not line.strip():
                if current:
                    adapters.append(current)
                    current = {}
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key == "AdapterRAM":
                try:
                    current["adapterRamBytes"] = int(value)
                except ValueError:
                    current["adapterRamBytes"] = None
            elif key == "Name":
                current["name"] = value.strip()
        if current:
            adapters.append(current)
    return {"available": bool(adapters), "adapters": adapters, "source": "wmic" if adapters else "unavailable"}


def _readiness(report: dict[str, Any]) -> dict[str, Any]:
    warnings = []
    ffmpeg = report["ffmpeg"]
    if not ffmpeg.get("installed"):
        warnings.append("FFmpeg is missing. Rendering cannot run until FFmpeg or imageio-ffmpeg is available.")
    if not ffmpeg.get("supportsGpuEncoding"):
        warnings.append("No hardware encoder was detected. CPU rendering will still work.")
    if not report["fonts"].get("available"):
        warnings.append("No system fonts were found. Text rendering may fall back to FFmpeg defaults.")
    if (report["storage"].get("freeBytes") or 0) < 5 * 1024**3:
        warnings.append("Less than 5 GB of free storage is available. Large renders may fail.")
    free_ram = report["memory"].get("freeBytes")
    if free_ram is not None and free_ram < 2 * 1024**3:
        warnings.append("Less than 2 GB RAM is currently free. Preview and render performance may suffer.")
    return {"ready": ffmpeg.get("installed", False), "warningCount": len(warnings), "warnings": warnings}


def _run(cmd: list[str], *, timeout: float) -> dict[str, Any]:
    try:
        result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return {"returnCode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    except Exception as exc:
        return {"returnCode": -1, "stdout": "", "stderr": str(exc)}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
