from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def transcript_to_caption_items(
    transcript_path: Path,
    *,
    mode: str = "phrase",
    default_duration: float = 2.4,
) -> list[dict[str, Any]]:
    text = transcript_path.read_text(encoding="utf-8")
    if transcript_path.suffix.lower() in {".srt", ".vtt"}:
        items = _parse_timed_transcript(text)
    else:
        items = _plain_text_captions(text, default_duration)
    if mode == "smart":
        items = smart_caption_items(
            " ".join(str(item["text"]) for item in items),
            duration=sum(float(item.get("duration", 0)) for item in items) or None,
        )
    elif mode in {"word", "word_by_word", "karaoke"}:
        items = _word_items(items)
    return items


def smart_caption_items(
    text: str,
    *,
    duration: float | None = None,
    max_words: int = 6,
    speaker: str | None = None,
) -> list[dict[str, Any]]:
    """Create readable short-form captions with punctuation-aware timing and emphasis metadata."""
    chunks = _caption_chunks(text, max_words=max_words)
    if not chunks:
        return []
    total_words = sum(max(len(_words(chunk)), 1) for chunk in chunks)
    target_duration = duration or max(2.0, total_words * 0.42)
    cursor = 0.0
    items: list[dict[str, Any]] = []
    for chunk in chunks:
        words = _words(chunk)
        punctuation_pause = 0.3 if re.search(r"[.!?]$", chunk.strip()) else 0.14 if re.search(r"[,;:]$", chunk.strip()) else 0.0
        base_duration = max(1.0, len(words) * target_duration / max(total_words, 1) + punctuation_pause)
        emphasis = _emphasis_words(chunk)
        item: dict[str, Any] = {
            "text": chunk,
            "start": round(cursor, 3),
            "duration": round(base_duration, 3),
            "emphasisWords": emphasis,
            "animatedKeywords": emphasis[:3],
            "highlightColor": "#ef4444" if emphasis else "#facc15",
            "readability": {
                "words": len(words),
                "wordsPerSecond": round(len(words) / max(base_duration, 0.01), 2),
                "punctuationPause": punctuation_pause,
            },
        }
        if speaker:
            item["speaker"] = speaker
        items.append(item)
        cursor += base_duration
    return items


def add_captions_from_transcript(
    project: dict[str, Any],
    transcript_path: Path,
    *,
    mode: str = "phrase",
    style: str = "tiktok",
    output_path: Path | None = None,
) -> dict[str, Any]:
    items = transcript_to_caption_items(transcript_path, mode=mode)
    caption_layer = _caption_layer(items, style, mode)
    target_scene = _longest_scene(project)
    target_scene.setdefault("layers", []).append(caption_layer)
    project.setdefault("metadata", {})["captions"] = {
        "source": str(transcript_path.resolve()),
        "mode": mode,
        "style": style,
        "itemCount": len(items),
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(project, handle, indent=2)
            handle.write("\n")
    return project


def _parse_timed_transcript(text: str) -> list[dict[str, Any]]:
    blocks = re.split(r"\n\s*\n", text.strip(), flags=re.MULTILINE)
    items: list[dict[str, Any]] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip() and line.strip().upper() != "WEBVTT"]
        time_line = next((line for line in lines if "-->" in line), None)
        if not time_line:
            continue
        start_raw, end_raw = [part.strip().split(" ")[0] for part in time_line.split("-->", 1)]
        caption_text = " ".join(line for line in lines if line != time_line and not line.isdigit())
        start = _timestamp(start_raw)
        end = _timestamp(end_raw)
        if caption_text:
            items.append({"text": caption_text, "start": start, "duration": max(end - start, 0.1)})
    return items


def _plain_text_captions(text: str, default_duration: float) -> list[dict[str, Any]]:
    chunks = [chunk.strip() for chunk in re.split(r"(?<=[.!?])\s+|\n+", text) if chunk.strip()]
    if not chunks and text.strip():
        chunks = [text.strip()]
    items = []
    cursor = 0.0
    for chunk in chunks:
        duration = max(default_duration, min(4.0, len(chunk.split()) * 0.38))
        items.append({"text": chunk, "start": round(cursor, 3), "duration": round(duration, 3)})
        cursor += duration
    return items


def _caption_chunks(text: str, *, max_words: int) -> list[str]:
    sentences = [chunk.strip() for chunk in re.split(r"(?<=[.!?])\s+|\n+", text) if chunk.strip()]
    chunks: list[str] = []
    for sentence in sentences or ([text.strip()] if text.strip() else []):
        words = sentence.split()
        current: list[str] = []
        for word in words:
            current.append(word)
            if len(current) >= max_words or re.search(r"[,;:]$", word):
                chunks.append(" ".join(current))
                current = []
        if current:
            chunks.append(" ".join(current))
    return chunks


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text)


def _emphasis_words(text: str) -> list[str]:
    stop = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "your",
        "from",
        "into",
        "about",
        "when",
        "then",
        "they",
        "will",
        "have",
    }
    words = _words(text)
    candidates = [word.strip("'") for word in words if len(word) >= 5 and word.lower() not in stop]
    if not candidates:
        candidates = [word.strip("'") for word in words if len(word) >= 4 and word.lower() not in stop]
    return candidates[:3]


def _word_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []
    for item in items:
        tokens = [token for token in str(item["text"]).split() if token]
        if not tokens:
            continue
        start = float(item.get("start", 0))
        duration = float(item.get("duration", 1))
        step = duration / len(tokens)
        for index, token in enumerate(tokens):
            words.append({"text": token, "start": round(start + index * step, 3), "duration": round(step * 1.15, 3)})
    return words


def _caption_layer(items: list[dict[str, Any]], style: str, mode: str) -> dict[str, Any]:
    layer = {
        "type": "caption",
        "layout": "lower_third",
        "fontSize": 58 if style == "tiktok" else 42,
        "color": "#ffffff",
        "strokeColor": "#000000",
        "strokeWidth": 4 if style == "tiktok" else 2,
        "box": style in {"tiktok", "karaoke"},
        "boxColor": "#000000aa",
        "boxPadding": 16,
        "captionMode": mode,
        "safeZone": "title",
        "animation": {"in": "slideUp", "out": "fade", "duration": 0.22},
        "readability": {"maxWords": 6 if style == "tiktok" else 8, "minDurationPerWord": 0.24},
        "items": items,
    }
    if mode == "karaoke":
        layer["color"] = "#facc15"
        layer["strokeColor"] = "#000000"
    return layer


def _longest_scene(project: dict[str, Any]) -> dict[str, Any]:
    timeline = project.setdefault("timeline", [])
    if not timeline:
        timeline.append({"id": "captions", "start": 0, "duration": 8, "layers": []})
    return max(timeline, key=lambda scene: float(scene.get("duration", 0)))


def _timestamp(value: str) -> float:
    value = value.replace(",", ".")
    parts = value.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return float(parts[0])
