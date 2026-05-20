from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from metrics.store import default_metrics_path, summarize_metrics


def creator_analytics(*, output_path: Path | None = None) -> dict[str, Any]:
    metrics_path = default_metrics_path()
    rows = _read_rows(metrics_path)
    summary = summarize_metrics(metrics_path=metrics_path)
    events = Counter(str(row.get("event", "unknown")) for row in rows)
    render_rows = [row for row in rows if row.get("event") == "render"]
    successful_exports = sum(1 for row in render_rows if int(row.get("outputSize") or 0) > 0)
    pipelines = [row for row in rows if row.get("event") in {"pipeline", "batch"}]
    report = {
        "metricsPath": str(metrics_path),
        "eventCounts": dict(events),
        "renderFrequency": len(render_rows),
        "exportSuccessRate": round(successful_exports / max(len(render_rows), 1), 3),
        "averageRenderSeconds": summary["averageRenderSeconds"],
        "averageOutputSize": summary["averageOutputSize"],
        "mostUsedTemplatesOrStyles": summary["templatePopularity"],
        "mostUsedTransitions": summary["mostUsedTransitions"],
        "effectUsage": summary["effectUsage"],
        "workflowEfficiency": {
            "automatedPipelineRuns": len(pipelines),
            "estimatedEditingMinutesSaved": round(len(pipelines) * 18 + len(render_rows) * 2.5, 1),
            "cacheFriendlyRenderCount": sum(1 for row in render_rows if row.get("cache")),
        },
        "localOnly": True,
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows
