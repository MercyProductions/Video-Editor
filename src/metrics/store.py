from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Any


def default_metrics_path() -> Path:
    return Path(__file__).resolve().parents[2] / "output" / "metrics" / "metrics.jsonl"


def record_metric(event: str, data: dict[str, Any], *, metrics_path: Path | None = None) -> dict[str, Any]:
    metrics_path = metrics_path or default_metrics_path()
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    row = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event, **data}
    with metrics_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def summarize_metrics(*, metrics_path: Path | None = None, output_path: Path | None = None) -> dict[str, Any]:
    metrics_path = metrics_path or default_metrics_path()
    rows = _read_rows(metrics_path)
    templates = Counter(str(row.get("template") or row.get("style") or "unknown") for row in rows if row.get("event") in {"pipeline", "batch"})
    transitions = Counter()
    effect_usage = Counter()
    render_times: list[float] = []
    export_sizes: list[int] = []
    for row in rows:
        if row.get("event") == "render":
            if row.get("renderSeconds") is not None:
                render_times.append(float(row["renderSeconds"]))
            if row.get("outputSize") is not None:
                export_sizes.append(int(row["outputSize"]))
        for transition in row.get("transitions", []) if isinstance(row.get("transitions"), list) else []:
            transitions[str(transition)] += 1
        for effect in row.get("effects", []) if isinstance(row.get("effects"), list) else []:
            effect_usage[str(effect)] += 1
    summary = {
        "metricsPath": str(metrics_path),
        "eventCount": len(rows),
        "renderCount": sum(1 for row in rows if row.get("event") == "render"),
        "averageRenderSeconds": round(sum(render_times) / len(render_times), 3) if render_times else 0,
        "averageOutputSize": round(sum(export_sizes) / len(export_sizes), 1) if export_sizes else 0,
        "templatePopularity": dict(templates.most_common(20)),
        "mostUsedTransitions": dict(transitions.most_common(20)),
        "effectUsage": dict(effect_usage.most_common(20)),
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def metrics_from_project(project: dict[str, Any]) -> dict[str, Any]:
    transitions: list[str] = []
    effects: list[str] = []
    for scene in project.get("timeline", []):
        transition = scene.get("transitionOut")
        if isinstance(transition, dict) and transition.get("type"):
            transitions.append(str(transition["type"]))
        for layer in scene.get("layers", []):
            raw = layer.get("effects", [])
            if isinstance(raw, str):
                effects.append(raw)
            elif isinstance(raw, list):
                effects.extend(str(item) for item in raw)
            animation = layer.get("animation")
            if isinstance(animation, dict):
                effects.extend(str(value) for key, value in animation.items() if key in {"in", "out"} and value)
            elif isinstance(animation, str):
                effects.append(animation)
    return {"transitions": transitions, "effects": effects}


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows
