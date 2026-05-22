from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Any, Callable

from workflow.creator import (
    asset_reuse_report,
    create_default_creator_profile,
    create_workflow_pipeline,
    creator_memory_report,
    list_local_tasks,
    list_workflow_pipelines,
    load_workflow_pipeline,
    production_dashboard,
    run_due_tasks,
    run_workflow_batch,
    schedule_local_task,
    update_creator_memory,
)

_WorkflowHandler = Callable[[argparse.Namespace], int]


def run_workflow_command(args: argparse.Namespace) -> int:
    handler = _WORKFLOW_HANDLERS.get(args.workflow_command)
    if not handler:
        raise ValueError(f"Unknown workflow command: {args.workflow_command}")
    return handler(args)


def _workflow_profile(args: argparse.Namespace) -> int:
    profile = create_default_creator_profile(args.name, output_path=_optional_path(args.output))
    print(f"Creator profile: {profile['path']}")
    print(f"Profile: {profile['name']} | pacing={profile.get('pacingStyle')} | cta={profile.get('preferredCTAStyle')}")
    return 0


def _workflow_pipeline_create(args: argparse.Namespace) -> int:
    workflow = create_workflow_pipeline(
        args.name,
        preset=args.preset,
        profile=args.profile,
        mode=args.mode,
        tone=args.tone,
        style=args.style,
        duration=args.duration,
        output_path=_optional_path(args.output),
    )
    print(f"Workflow pipeline: {workflow['path']}")
    print(f"{workflow['name']} | mode={workflow['generationRules']['mode']} | tone={workflow['generationRules']['tone']} | duration={workflow['generationRules']['duration']}s")
    return 0


def _workflow_pipeline_list(args: argparse.Namespace) -> int:
    rows = list_workflow_pipelines()
    if not rows:
        print("No saved workflow pipelines found.")
        return 0
    for row in rows:
        print(f"{row['id']} | {row['name']} | {row['generationRules']['mode']} | {row['path']}")
    return 0


def _workflow_pipeline_show(args: argparse.Namespace) -> int:
    print(json.dumps(load_workflow_pipeline(args.name_or_path), indent=2))
    return 0


def _workflow_batch(args: argparse.Namespace) -> int:
    output_dir = _optional_path(args.output_dir) or _default_generated_path(f"workflow_batch_{_slug(args.idea)[:32]}")
    report = run_workflow_batch(
        args.workflow,
        idea=args.idea,
        output_dir=output_dir,
        assets_folder=_optional_path(args.assets),
        music_path=_optional_path(args.music),
        logo_path=_optional_path(args.logo),
        versions=args.versions,
        render=args.render,
        quality=args.quality,
    )
    print(f"Workflow batch: {output_dir / 'workflow_batch_summary.json'}")
    print(f"Generated variants: {report['versionCount']}")
    for item in report["outputs"][:8]:
        variant = item.get("variant", {})
        print(f"- v{variant.get('index')}: {variant.get('hookStyle')} / {variant.get('tone')} -> {item['projectPath']}")
    return 0


def _workflow_task_create(args: argparse.Namespace) -> int:
    task_args = shlex.split(args.cmd) if args.cmd else list(args.task_args)
    if not task_args:
        raise ValueError("task-create requires --cmd or command arguments, for example: --cmd \"render examples/project.json -o output/night.mp4 --quality preview\"")
    task = schedule_local_task(args.name, task_type=args.type, command=task_args, run_at=args.run_at, priority=args.priority)
    print(f"Scheduled local task: {task['path']}")
    print(f"{task['name']} | runAt={task['runAt']} | command={' '.join(task['command'])}")
    return 0


def _workflow_task_list(args: argparse.Namespace) -> int:
    tasks = list_local_tasks()
    if not tasks:
        print("No local scheduled tasks found.")
        return 0
    for task in tasks:
        print(f"{task.get('id')} | {task.get('status')} | {task.get('runAt')} | {task.get('name')}")
    return 0


def _workflow_task_run(args: argparse.Namespace) -> int:
    report = run_due_tasks(now="force" if args.force else None, limit=args.limit)
    print(f"Ran local tasks: {report['ran']}")
    for task in report["tasks"]:
        print(f"- {task.get('name')}: {task.get('status')} code={task.get('lastResult', {}).get('returnCode')}")
    return 0 if all(task.get("status") == "completed" for task in report["tasks"]) else 1 if report["tasks"] else 0


def _workflow_memory_update(args: argparse.Namespace) -> int:
    memory = update_creator_memory(
        profile_name=args.profile,
        project_path=_optional_path(args.project),
        content_plan_path=_optional_path(args.plan),
        rating=args.rating,
        note=args.note,
        preference=_parse_preferences(args.prefer),
    )
    print(f"Creator memory: {memory['path']}")
    print(f"Events={len(memory.get('events', []))} learned={len(memory.get('learnedAt', []))}")
    return 0


def _workflow_memory_show(args: argparse.Namespace) -> int:
    print(json.dumps(creator_memory_report(args.profile), indent=2))
    return 0


def _workflow_asset_reuse(args: argparse.Namespace) -> int:
    output = _optional_path(args.output)
    report = asset_reuse_report(project_path=_optional_path(args.project), output_path=output)
    if output:
        print(f"Asset reuse report: {output}")
    print(f"Top clips={len(report['frequentlyUsedClips'])} hooks={len(report['bestKnownHooks'])} transitions={len(report['favoriteTransitions'])}")
    return 0


def _workflow_dashboard(args: argparse.Namespace) -> int:
    output = _optional_path(args.output) or _default_generated_path("production_dashboard.json")
    dashboard = production_dashboard(project_path=_optional_path(args.project), output_path=output)
    print(f"Production dashboard: {output}")
    print(f"Recent renders={len(dashboard['recentRenders'])} queued={dashboard['queuedRenders']} cacheBytes={dashboard['storage']['cacheBytes']} success={dashboard['renderSuccessRate']}")
    return 0


def _optional_path(value: str | None) -> Path | None:
    return Path(value).resolve() if value else None


def _parse_preferences(items: list[str]) -> dict[str, Any]:
    preferences: dict[str, Any] = {}
    for item in items or []:
        if "=" not in item:
            preferences[item] = True
            continue
        key, value = item.split("=", 1)
        preferences[key.strip()] = _parse_preference_value(value.strip())
    return preferences


def _parse_preference_value(value: str) -> Any:
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return float(value) if "." in value else int(value)
    except ValueError:
        return value


def _default_generated_path(filename: str) -> Path:
    return Path(__file__).resolve().parents[2] / "examples" / "generated" / filename


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_")


_WORKFLOW_HANDLERS: dict[str, _WorkflowHandler] = {
    "profile": _workflow_profile,
    "pipeline-create": _workflow_pipeline_create,
    "pipeline-list": _workflow_pipeline_list,
    "pipeline-show": _workflow_pipeline_show,
    "batch": _workflow_batch,
    "task-create": _workflow_task_create,
    "task-list": _workflow_task_list,
    "task-run": _workflow_task_run,
    "memory-update": _workflow_memory_update,
    "memory-show": _workflow_memory_show,
    "asset-reuse": _workflow_asset_reuse,
    "dashboard": _workflow_dashboard,
}
