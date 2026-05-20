from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from assets.database import database_report, track_project_usage
from content.generator import run_content_generator
from content.profiles import create_profile, load_profile
from metrics.store import default_metrics_path, record_metric, summarize_metrics
from quality.checker import run_quality_check
from stability.cache import cache_report, cleanup_caches
from styles.presets import list_styles
from workers.local_render import worker_status


WORKFLOW_PRESETS: dict[str, dict[str, Any]] = {
    "youtube_short_product_showcase": {
        "name": "YouTube Short Product Showcase",
        "mode": "youtube_shorts",
        "tone": "cinematic",
        "style": "auto",
        "duration": 35,
        "structure": ["hook", "problem", "feature_showcase", "result", "cta"],
        "pacing": "fast_vertical",
        "effects": ["large_captions", "smooth_zoom", "title_cards"],
        "exportPackage": {"platforms": ["youtube_shorts"], "thumbnailVariants": 3},
    },
    "cybersecurity_tool_demo": {
        "name": "Cybersecurity Tool Demo",
        "mode": "youtube_shorts",
        "tone": "cinematic",
        "style": "red_black_aegis",
        "duration": 45,
        "structure": ["hook", "risk", "scan", "result", "cta"],
        "pacing": "medium_fast",
        "effects": ["red_black_lighting", "focus_zoom", "caption_emphasis"],
        "exportPackage": {"platforms": ["youtube_shorts", "tiktok", "x_twitter"], "thumbnailVariants": 3},
    },
    "gaming_montage": {
        "name": "Gaming Montage",
        "mode": "tiktok",
        "tone": "aggressive",
        "style": "gaming_montage",
        "duration": 24,
        "structure": ["hook", "setup", "fast_hits", "payoff", "cta"],
        "pacing": "fast_cuts",
        "effects": ["zoom_hits", "punchy_captions", "beat_sync"],
        "exportPackage": {"platforms": ["tiktok", "youtube_shorts", "instagram_reels"], "thumbnailVariants": 3},
    },
    "minimal_saas_promo": {
        "name": "Minimal SaaS Promo",
        "mode": "product_showcase",
        "tone": "minimal",
        "style": "minimal_tech",
        "duration": 30,
        "structure": ["intro", "feature_reveal", "result", "cta"],
        "pacing": "clean",
        "effects": ["soft_crossfade", "readable_captions", "subtle_zoom"],
        "exportPackage": {"platforms": ["youtube_shorts", "x_twitter"], "thumbnailVariants": 3},
    },
}

HOOK_VARIANTS = {
    "serious": "Lead with a direct business problem and practical payoff.",
    "curiosity": "Open with a surprising question or hidden issue.",
    "problem_solution": "Start with the pain, then quickly reveal the fix.",
    "aggressive": "Use a punchy, high-energy first line with faster pacing.",
    "clean": "Use a simple professional hook with minimal hype.",
}

CTA_VARIANTS = {
    "subscribe": "End by asking viewers to subscribe for more workflow demos.",
    "download": "End by asking viewers to download or try the product.",
    "comment": "End by asking viewers what feature they want next.",
    "follow": "End by asking viewers to follow for more short demos.",
}


def workflow_root() -> Path:
    return Path(__file__).resolve().parents[2] / "workflows"


def pipeline_dir() -> Path:
    return workflow_root() / "pipelines"


def tasks_dir() -> Path:
    return workflow_root() / "tasks"


def memory_dir() -> Path:
    return workflow_root() / "memory"


def create_workflow_pipeline(
    name: str,
    *,
    preset: str | None = None,
    profile: str | Path | None = None,
    mode: str | None = None,
    tone: str | None = None,
    style: str | None = None,
    duration: float | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    key = _slug(preset or name)
    base = json.loads(json.dumps(WORKFLOW_PRESETS.get(key, WORKFLOW_PRESETS["youtube_short_product_showcase"])))
    base["name"] = name or base["name"]
    if mode:
        base["mode"] = mode
    if tone:
        base["tone"] = tone
    if style:
        base["style"] = style
    if duration:
        base["duration"] = duration
    profile_data = load_profile(profile)
    workflow = {
        "workflowVersion": 1,
        "id": _slug(base["name"]),
        "name": base["name"],
        "createdAt": _now(),
        "localOnly": True,
        "profile": {
            "name": profile_data.get("name", "Default Creator"),
            "path": profile_data.get("path"),
            "captionStyle": profile_data.get("captionStyle"),
            "exportSettings": profile_data.get("exportSettings"),
            "preferredTransitions": profile_data.get("favoriteTransitions", []),
            "preferredCTAStyle": profile_data.get("ctaStyle"),
        },
        "generationRules": {
            "mode": base["mode"],
            "tone": base["tone"],
            "style": base["style"],
            "duration": base["duration"],
            "preferredHooks": profile_data.get("preferredHooks", []),
            "preferredTransitions": profile_data.get("favoriteTransitions", []),
            "preferredMusicBehavior": profile_data.get("preferredMusicBehavior", {}),
        },
        "pacing": base["pacing"],
        "structure": base["structure"],
        "effects": base["effects"],
        "exportPackage": base["exportPackage"],
    }
    path = output_path or pipeline_dir() / f"{workflow['id']}.workflow.json"
    _write_json(path, workflow)
    workflow["path"] = str(path.resolve())
    return workflow


def list_workflow_pipelines() -> list[dict[str, Any]]:
    root = pipeline_dir()
    if not root.exists():
        return []
    rows = []
    for path in sorted(root.glob("*.workflow.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["path"] = str(path.resolve())
            rows.append(data)
        except json.JSONDecodeError:
            continue
    return rows


def load_workflow_pipeline(path_or_name: str | Path) -> dict[str, Any]:
    raw = Path(path_or_name)
    path = raw if raw.exists() else pipeline_dir() / f"{_slug(str(path_or_name))}.workflow.json"
    if not path.exists():
        preset_key = _slug(str(path_or_name))
        if preset_key in WORKFLOW_PRESETS:
            return create_workflow_pipeline(WORKFLOW_PRESETS[preset_key]["name"], preset=preset_key)
        raise FileNotFoundError(f"Workflow pipeline not found: {path_or_name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["path"] = str(path.resolve())
    return data


def run_workflow_batch(
    workflow_path_or_name: str | Path,
    *,
    idea: str,
    output_dir: Path,
    assets_folder: Path | None = None,
    music_path: Path | None = None,
    logo_path: Path | None = None,
    versions: int = 3,
    render: bool = False,
    quality: str = "preview",
) -> dict[str, Any]:
    workflow = load_workflow_pipeline(workflow_path_or_name)
    identity = _creator_identity(str(workflow.get("profile", {}).get("name", "Default Creator")))
    rules = workflow["generationRules"]
    output_dir.mkdir(parents=True, exist_ok=True)
    hooks = list(HOOK_VARIANTS.items())
    ctas = list(CTA_VARIANTS.items())
    tones = _batch_tones(str(rules.get("tone", "cinematic")))
    outputs = []
    for index in range(1, max(1, versions) + 1):
        hook_key, hook_instruction = hooks[(index - 1) % len(hooks)]
        cta_key, cta_instruction = ctas[(index - 1) % len(ctas)]
        tone = tones[(index - 1) % len(tones)]
        prompt = f"{idea}. Hook style: {hook_instruction} CTA style: {cta_instruction} {_identity_prompt(identity)}".strip()
        run_dir = output_dir / f"v{index:02d}_{hook_key}_{tone}"
        summary = run_content_generator(
            idea=prompt,
            output_dir=run_dir,
            mode=str(rules.get("mode", "youtube_shorts")),
            product_name=None,
            target_platform=None,
            goal=f"Workflow batch variant {index} for {workflow['name']}",
            bullet_points=[],
            assets_folder=assets_folder,
            music_path=music_path,
            logo_path=logo_path,
            duration=float(rules.get("duration", 35)),
            tone=tone,
            style=_identity_style(identity, str(rules.get("style", "auto"))),
            locks=[],
            approved=False,
            render=render,
            quality=quality,
            cache=True,
        )
        summary["variant"] = {"index": index, "hookStyle": hook_key, "ctaStyle": cta_key, "tone": tone}
        if identity:
            summary["creatorIdentityApplied"] = {
                "profile": identity.get("profile"),
                "updatedAt": identity.get("updatedAt"),
                "guidance": identity.get("generationGuidance", [])[:4],
            }
        outputs.append(summary)
    report = {
        "workflow": workflow,
        "idea": idea,
        "versionCount": len(outputs),
        "outputs": outputs,
        "exportPackage": workflow.get("exportPackage", {}),
    }
    _write_json(output_dir / "workflow_batch_summary.json", report)
    record_metric("workflow_batch", {"workflow": workflow["id"], "count": len(outputs), "render": render})
    return report


def schedule_local_task(
    name: str,
    *,
    task_type: str,
    command: list[str],
    run_at: str = "overnight",
    priority: int = 0,
    enabled: bool = True,
    output_path: Path | None = None,
) -> dict[str, Any]:
    task = {
        "taskVersion": 1,
        "id": _slug(name) + "_" + uuid.uuid4().hex[:8],
        "name": name,
        "type": task_type,
        "runAt": run_at,
        "priority": priority,
        "enabled": enabled,
        "localOnly": True,
        "command": command,
        "status": "scheduled",
        "createdAt": _now(),
        "lastRunAt": None,
        "lastResult": None,
    }
    path = output_path or tasks_dir() / f"{task['id']}.task.json"
    _write_json(path, task)
    task["path"] = str(path.resolve())
    return task


def list_local_tasks() -> list[dict[str, Any]]:
    root = tasks_dir()
    if not root.exists():
        return []
    tasks = []
    for path in sorted(root.glob("*.task.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            item["path"] = str(path.resolve())
            tasks.append(item)
        except json.JSONDecodeError:
            tasks.append({"path": str(path.resolve()), "status": "corrupt"})
    return sorted(tasks, key=lambda item: (int(item.get("priority", 0)) * -1, str(item.get("name", ""))))


def run_due_tasks(*, now: str | None = None, limit: int = 5) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    ran = []
    for task in list_local_tasks():
        if len(ran) >= limit:
            break
        if not task.get("enabled", True) or not _task_due(task, now=now):
            continue
        path = Path(task["path"])
        command = [sys.executable, str(root / "render.py"), *[str(part) for part in task.get("command", [])]]
        started = time.perf_counter()
        result = subprocess.run(command, cwd=str(root), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=3600)
        task["lastRunAt"] = _now()
        task["lastResult"] = {
            "returnCode": result.returncode,
            "seconds": round(time.perf_counter() - started, 3),
            "output": (result.stdout or "")[-6000:],
        }
        task["status"] = "completed" if result.returncode == 0 else "failed"
        _write_json(path, task)
        ran.append(task)
    report = {"ran": len(ran), "tasks": ran}
    _write_json(tasks_dir() / "task_run_report.json", report)
    return report


def update_creator_memory(
    *,
    profile_name: str,
    project_path: Path | None = None,
    content_plan_path: Path | None = None,
    rating: str | None = None,
    note: str | None = None,
    preference: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path = memory_dir() / f"{_slug(profile_name)}.memory.json"
    memory = _read_json(path, default={"memoryVersion": 1, "profile": profile_name, "events": [], "preferences": {}, "learnedAt": []})
    event: dict[str, Any] = {"timestamp": _now(), "rating": rating, "note": note}
    if project_path and project_path.exists():
        project = json.loads(project_path.read_text(encoding="utf-8"))
        event["project"] = str(project_path.resolve())
        event["style"] = project.get("stylePreset") or project.get("metadata", {}).get("stylePreset")
        event["transitions"] = _transitions(project)
        event["captionDensity"] = _caption_density(project)
    if content_plan_path and content_plan_path.exists():
        plan = json.loads(content_plan_path.read_text(encoding="utf-8"))
        event["contentPlan"] = str(content_plan_path.resolve())
        event["hook"] = plan.get("hook")
        event["mode"] = plan.get("contentBrief", {}).get("mode")
        event["tone"] = plan.get("editingStyle", {}).get("tone")
    if preference:
        memory.setdefault("preferences", {}).update(preference)
    memory.setdefault("events", []).append(event)
    memory["learnedAt"] = _derive_preferences(memory["events"], memory.get("preferences", {}))
    _write_json(path, memory)
    memory["path"] = str(path.resolve())
    record_metric("creator_memory", {"profile": profile_name, "rating": rating or "none"})
    return memory


def creator_memory_report(profile_name: str | None = None) -> dict[str, Any]:
    root = memory_dir()
    memories = []
    paths = [root / f"{_slug(profile_name)}.memory.json"] if profile_name else sorted(root.glob("*.memory.json")) if root.exists() else []
    for path in paths:
        if path.exists():
            item = json.loads(path.read_text(encoding="utf-8"))
            item["path"] = str(path.resolve())
            item["eventCount"] = len(item.get("events", []))
            memories.append(item)
    return {"memoryDir": str(root.resolve()), "count": len(memories), "memories": memories}


def asset_reuse_report(*, project_path: Path | None = None, output_path: Path | None = None) -> dict[str, Any]:
    usage = track_project_usage(project_path) if project_path and project_path.exists() else None
    db = database_report()
    metrics = summarize_metrics()
    memory = creator_memory_report()
    hooks = Counter()
    styles = Counter()
    transitions = Counter(metrics.get("mostUsedTransitions", {}))
    for item in memory.get("memories", []):
        for event in item.get("events", []):
            if event.get("hook"):
                hooks[str(event["hook"])] += 1
            if event.get("style"):
                styles[str(event["style"])] += 1
            for transition in event.get("transitions", []) if isinstance(event.get("transitions"), list) else []:
                transitions[str(transition)] += 1
    report = {
        "assetDatabase": db,
        "projectUsage": usage,
        "frequentlyUsedClips": [row for row in db.get("topUsage", []) if str(row.get("asset_path", "")).lower().endswith((".mp4", ".mov", ".mkv", ".webm"))][:10],
        "bestKnownHooks": dict(hooks.most_common(10)),
        "favoriteTransitions": dict(transitions.most_common(10)),
        "preferredStyles": dict((styles or Counter(metrics.get("templatePopularity", {}))).most_common(10)),
        "creatorPreferences": memory,
    }
    if output_path:
        _write_json(output_path, report)
    return report


def production_dashboard(*, project_path: Path | None = None, output_path: Path | None = None) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    metrics = summarize_metrics()
    caches = cache_report(root / "output")
    workers = worker_status()
    asset_db = database_report()
    project_health = run_quality_check(project_path) if project_path and project_path.exists() else None
    recent_renders = _recent_files([root / "output", root / "examples" / "generated", root / "exports"], "*.mp4", 12)
    render_jobs = workers.get("jobs", [])
    completed = sum(1 for job in render_jobs if job.get("status") == "completed")
    failed = sum(1 for job in render_jobs if job.get("status") == "failed")
    dashboard = {
        "dashboardVersion": 1,
        "generatedAt": _now(),
        "recentRenders": recent_renders,
        "queuedRenders": workers.get("queued", 0),
        "runningRenders": workers.get("running", 0),
        "storage": {
            "outputBytes": _dir_size(root / "output"),
            "exportsBytes": _dir_size(root / "exports"),
            "cacheBytes": caches.get("totalBytes", 0),
        },
        "cache": caches,
        "assetDatabase": {"assetCount": asset_db.get("assetCount", 0), "duplicateGroupCount": asset_db.get("duplicateGroupCount", 0)},
        "projectHealth": project_health,
        "renderSuccessRate": round(completed / max(completed + failed, 1), 3),
        "metrics": metrics,
        "workflowHealth": _workflow_health(metrics, caches, project_health),
    }
    if output_path:
        _write_json(output_path, dashboard)
    return dashboard


def create_default_creator_profile(name: str, *, output_path: Path | None = None) -> dict[str, Any]:
    return create_profile(
        name,
        output_path=output_path,
        overrides={
            "preferredHooks": ["problem_solution", "curiosity"],
            "preferredTransitions": ["crossfade", "zoom"],
            "favoriteTransitions": ["crossfade", "zoom"],
            "preferredCTAStyle": "save_and_try",
            "ctaStyle": "save_and_try",
            "pacingStyle": "medium_fast",
            "introStyle": "short_title_card",
            "outroStyle": "cta_card",
        },
    )


def _batch_tones(primary: str) -> list[str]:
    tones = [primary]
    for tone in ["cinematic", "clean", "aggressive", "minimal"]:
        if tone not in tones:
            tones.append(tone)
    return tones


def _task_due(task: dict[str, Any], *, now: str | None) -> bool:
    run_at = str(task.get("runAt", "overnight")).lower()
    if now == "force" or run_at in {"now", "once"}:
        return True
    if run_at == "overnight":
        hour = int(time.strftime("%H", time.localtime()))
        return hour >= 22 or hour <= 6
    if run_at.startswith("hourly"):
        return True
    return False


def _derive_preferences(events: list[dict[str, Any]], manual: dict[str, Any]) -> list[dict[str, Any]]:
    positive = [event for event in events if str(event.get("rating", "")).lower() in {"good", "great", "reuse", "approved", "5", "4"}]
    styles = Counter(str(event.get("style")) for event in positive if event.get("style"))
    hooks = Counter(str(event.get("hook")) for event in positive if event.get("hook"))
    transitions = Counter()
    for event in positive:
        for transition in event.get("transitions", []) if isinstance(event.get("transitions"), list) else []:
            transitions[str(transition)] += 1
    learned = []
    if styles:
        learned.append({"key": "preferredStyle", "value": styles.most_common(1)[0][0], "confidence": min(0.95, 0.45 + styles.most_common(1)[0][1] * 0.1)})
    if hooks:
        learned.append({"key": "preferredHook", "value": hooks.most_common(1)[0][0], "confidence": min(0.9, 0.4 + hooks.most_common(1)[0][1] * 0.08)})
    if transitions:
        learned.append({"key": "preferredTransition", "value": transitions.most_common(1)[0][0], "confidence": min(0.9, 0.4 + transitions.most_common(1)[0][1] * 0.08)})
    for key, value in manual.items():
        learned.append({"key": key, "value": value, "confidence": 1.0, "source": "manual"})
    return learned


def _workflow_health(metrics: dict[str, Any], caches: dict[str, Any], project_health: dict[str, Any] | None) -> list[str]:
    warnings = []
    if caches.get("totalBytes", 0) > 10 * 1024**3:
        warnings.append("Cache storage is high; schedule cache cleanup.")
    if metrics.get("renderCount", 0) == 0:
        warnings.append("No render metrics recorded yet.")
    if project_health and not project_health.get("passed"):
        warnings.append("Current project has quality issues.")
    return warnings


def _creator_identity(profile_name: str) -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "feedback" / "identity" / f"{_slug(profile_name)}.creator-identity.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _identity_prompt(identity: dict[str, Any]) -> str:
    guidance = identity.get("generationGuidance", []) if isinstance(identity.get("generationGuidance"), list) else []
    if not guidance:
        return ""
    return "Creator preference memory: " + " ".join(str(item) for item in guidance[:3])


def _identity_style(identity: dict[str, Any], fallback: str) -> str:
    if fallback and fallback != "auto":
        return fallback
    model = identity.get("preferenceModel", {}) if isinstance(identity.get("preferenceModel"), dict) else {}
    style = str(model.get("colorGradingPreference") or "auto")
    return style if style in list_styles() else fallback


def _recent_files(roots: list[Path], pattern: str, limit: int) -> list[dict[str, Any]]:
    files = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob(pattern):
            if path.is_file():
                stat = path.stat()
                files.append({"path": str(path.resolve()), "bytes": stat.st_size, "modifiedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stat.st_mtime))})
    return sorted(files, key=lambda item: item["modifiedAt"], reverse=True)[:limit]


def _transitions(project: dict[str, Any]) -> list[str]:
    values = []
    for scene in project.get("timeline", []):
        transition = scene.get("transitionOut")
        if isinstance(transition, dict) and transition.get("type"):
            values.append(str(transition["type"]))
    return values


def _caption_density(project: dict[str, Any]) -> float:
    words = 0
    duration = float(project.get("project", {}).get("duration", 1) or 1)
    for scene in project.get("timeline", []):
        for layer in scene.get("layers", []):
            if layer.get("type") in {"text", "caption", "captions"}:
                words += len(str(layer.get("text", "")).split())
                for item in layer.get("items", []) if isinstance(layer.get("items"), list) else []:
                    words += len(str(item.get("text", "")).split())
    return round(words / max(duration, 0.1), 3)


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _read_json(path: Path, *, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return json.loads(json.dumps(default))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup = path.with_suffix(path.suffix + ".corrupt")
        shutil.copy2(path, backup)
        return json.loads(json.dumps(default))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "workflow"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
