from __future__ import annotations

import csv
import shutil
import tempfile
from pathlib import Path
from subprocess import PIPE, STDOUT, run
from typing import Any

from utils.media import run_ffmpeg


def analyze_screen_text(
    recording_path: Path,
    *,
    sample_times: list[float],
    source_width: int,
    source_height: int,
    max_frames: int = 8,
) -> dict[str, Any]:
    """Run optional local OCR over selected desktop recording frames.

    This is deliberately best-effort and local-only. If Tesseract is not
    installed, callers still receive a structured report explaining why OCR
    is unavailable instead of failing the showcase analysis pipeline.
    """

    executable = shutil.which("tesseract")
    if not executable:
        return {
            "available": False,
            "engine": "tesseract",
            "reason": "Tesseract OCR was not found on PATH.",
            "sampledFrames": [],
            "textBlocks": [],
            "keywords": [],
            "warnings": ["Install Tesseract locally to enable OCR-driven UI detection."],
        }

    clean_times = _sample_times(sample_times, max_frames=max_frames)
    if not clean_times:
        return {
            "available": True,
            "engine": "tesseract",
            "sampledFrames": [],
            "textBlocks": [],
            "keywords": [],
            "warnings": ["No stable sample times were available for OCR."],
        }

    blocks: list[dict[str, Any]] = []
    sampled_frames: list[dict[str, Any]] = []
    warnings: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ave_ocr_") as folder:
        temp_dir = Path(folder)
        for index, time_s in enumerate(clean_times):
            frame_path = temp_dir / f"frame_{index:03d}.png"
            result = run_ffmpeg(
                [
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-ss",
                    f"{time_s:.3f}",
                    "-i",
                    str(recording_path),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale='min(1920,iw)':-2",
                    str(frame_path),
                ]
            )
            if result.returncode != 0 or not frame_path.exists():
                warnings.append(f"Could not extract OCR frame at {time_s:.3f}s.")
                continue
            sampled_frames.append({"time": round(time_s, 3)})
            blocks.extend(_ocr_frame(executable, frame_path, time_s, source_width, source_height))

    merged = _merge_text_blocks(blocks)
    return {
        "available": True,
        "engine": "tesseract",
        "sampledFrames": sampled_frames,
        "textBlocks": merged,
        "keywords": _keywords(merged),
        "warnings": warnings,
    }


def _sample_times(times: list[float], *, max_frames: int) -> list[float]:
    cleaned = sorted({round(max(0.0, float(item)), 2) for item in times if float(item) >= 0})
    if len(cleaned) <= max_frames:
        return cleaned
    step = max(len(cleaned) / max_frames, 1)
    selected = [cleaned[min(int(round(index * step)), len(cleaned) - 1)] for index in range(max_frames)]
    return sorted(set(selected))


def _ocr_frame(executable: str, frame_path: Path, time_s: float, source_width: int, source_height: int) -> list[dict[str, Any]]:
    result = run(
        [executable, str(frame_path), "stdout", "--psm", "6", "tsv"],
        text=True,
        stdout=PIPE,
        stderr=STDOUT,
        timeout=20,
    )
    if result.returncode != 0 or not result.stdout:
        return []

    rows = csv.DictReader(result.stdout.splitlines(), delimiter="\t")
    words: list[dict[str, Any]] = []
    for row in rows:
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        confidence = _confidence(row.get("conf"))
        if confidence < 45:
            continue
        scale = min(1920, source_width) / max(source_width, 1)
        left = int(_number(row.get("left")) / max(scale, 0.001))
        top = int(_number(row.get("top")) / max(scale, 0.001))
        width = max(int(_number(row.get("width")) / max(scale, 0.001)), 1)
        height = max(int(_number(row.get("height")) / max(scale, 0.001)), 1)
        words.append(
            {
                "time": round(time_s, 3),
                "text": text,
                "confidence": round(confidence / 100, 3),
                "rect": {
                    "x": int(left),
                    "y": int(top),
                    "width": int(width),
                    "height": int(height),
                },
            }
        )

    if not words:
        return []
    return [_group_words(words, source_width, source_height)]


def _group_words(words: list[dict[str, Any]], source_width: int, source_height: int) -> dict[str, Any]:
    left = min(int(word["rect"]["x"]) for word in words)
    top = min(int(word["rect"]["y"]) for word in words)
    right = max(int(word["rect"]["x"]) + int(word["rect"]["width"]) for word in words)
    bottom = max(int(word["rect"]["y"]) + int(word["rect"]["height"]) for word in words)
    text = " ".join(str(word["text"]) for word in words)
    confidence = sum(float(word["confidence"]) for word in words) / max(len(words), 1)
    return {
        "time": words[0]["time"],
        "text": text[:500],
        "confidence": round(confidence, 3),
        "rect": {
            "x": max(0, min(left, source_width)),
            "y": max(0, min(top, source_height)),
            "width": max(1, min(right - left, source_width)),
            "height": max(1, min(bottom - top, source_height)),
        },
        "source": "local_ocr",
    }


def _merge_text_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for block in sorted(blocks, key=lambda item: (float(item["time"]), -float(item["confidence"]))):
        if any(abs(float(block["time"]) - float(existing["time"])) < 0.35 and block["text"] == existing["text"] for existing in merged):
            continue
        merged.append(block)
    return merged[:40]


def _keywords(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    important = {"login", "dashboard", "scan", "success", "error", "complete", "settings", "security", "runtime", "warning", "blocked"}
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, float]] = set()
    for block in blocks:
        lower = str(block.get("text", "")).lower()
        for word in important:
            if word in lower:
                key = (word, float(block["time"]))
                if key in seen:
                    continue
                seen.add(key)
                rows.append({"keyword": word, "time": block["time"], "confidence": block.get("confidence", 0.5)})
    return rows[:30]


def _confidence(value: Any) -> float:
    try:
        return max(0.0, min(float(value), 100.0))
    except (TypeError, ValueError):
        return 0.0


def _number(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0
