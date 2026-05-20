from __future__ import annotations

import difflib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REVIEW_STATUSES = {"needs_review", "approved", "locked", "rejected"}


def build_generation_review(plan: dict[str, Any], project: dict[str, Any]) -> dict[str, Any]:
    assets = project.get("assets", {}) if isinstance(project.get("assets"), dict) else {}
    scenes = plan.get("scenePlan", [])
    captions = plan.get("captions", [])
    style = plan.get("editingStyle", {})
    brief = plan.get("contentBrief", {})
    review = {
        "reviewVersion": 1,
        "generatedAt": _now(),
        "status": "needs_review",
        "summary": {
            "hook": plan.get("hook", ""),
            "stylePreset": style.get("stylePreset", ""),
            "tone": style.get("tone", ""),
            "estimatedDuration": plan.get("duration", 0),
            "mode": brief.get("mode", ""),
            "targetPlatform": brief.get("targetPlatform", ""),
            "assetsUsed": [{"key": key, "path": value} for key, value in sorted(assets.items())],
            "warnings": list(plan.get("warnings", [])),
        },
        "sections": {
            "hook": _section("hook", plan.get("hook", "")),
            "script": [
                _section(f"script:{index}", line, extra={"index": index})
                for index, line in enumerate(plan.get("script", {}).get("lines", []))
            ],
            "scenes": [
                _section(
                    f"scene:{scene.get('id', index)}",
                    scene.get("title", scene.get("id", f"Scene {index + 1}")),
                    extra={
                        "sceneId": scene.get("id"),
                        "caption": scene.get("caption", ""),
                        "start": scene.get("start"),
                        "duration": scene.get("duration"),
                        "role": scene.get("role", ""),
                    },
                )
                for index, scene in enumerate(scenes)
            ],
            "captions": [
                _section(
                    f"caption:{caption.get('sceneId', index)}",
                    caption.get("text", ""),
                    extra={
                        "sceneId": caption.get("sceneId"),
                        "start": caption.get("start"),
                        "duration": caption.get("duration"),
                    },
                )
                for index, caption in enumerate(captions)
            ],
            "timing": [
                _section(
                    f"timing:{scene.get('id', index)}",
                    f"{scene.get('start')}s + {scene.get('duration')}s",
                    extra={"sceneId": scene.get("id"), "start": scene.get("start"), "duration": scene.get("duration")},
                )
                for index, scene in enumerate(scenes)
            ],
            "style": _section("style", f"{style.get('stylePreset', '')} / {style.get('tone', '')}"),
            "music": _section("music", "Music sync enabled" if style.get("musicSync", {}).get("enabled") else "No music sync"),
            "titleCards": [
                _section(
                    f"title:{scene.get('id', index)}",
                    scene.get("title", ""),
                    extra={"sceneId": scene.get("id"), "mediaRole": scene.get("mediaRole", "")},
                )
                for index, scene in enumerate(scenes)
                if scene.get("mediaRole") == "title_card" or scene.get("title")
            ],
        },
        "readiness": {},
    }
    review["readiness"] = review_readiness(review)
    return review


def apply_review_locks(review: dict[str, Any], locks: list[str]) -> dict[str, Any]:
    normalized = {_normalize_section_key(item) for item in locks if item.strip()}
    for section in _iter_sections(review):
        if _normalize_section_key(section.get("key", "")) in normalized:
            section["status"] = "locked"
            section["locked"] = True
    review["readiness"] = review_readiness(review)
    review["status"] = "approved" if review["readiness"]["readyForFinalRender"] else "needs_review"
    return review


def set_review_status(review: dict[str, Any], section_key: str, status: str) -> dict[str, Any]:
    clean_status = status if status in REVIEW_STATUSES else "needs_review"
    normalized = _normalize_section_key(section_key)
    changed = False
    if normalized == "all":
        for section in _iter_sections(review):
            section["status"] = clean_status
            section["locked"] = clean_status == "locked"
        changed = True
    else:
        for section in _iter_sections(review):
            if _normalize_section_key(section.get("key", "")) == normalized:
                section["status"] = clean_status
                section["locked"] = clean_status == "locked"
                changed = True
    if not changed:
        review.setdefault("warnings", []).append(f"Review section not found: {section_key}")
    review["updatedAt"] = _now()
    review["readiness"] = review_readiness(review)
    review["status"] = "approved" if review["readiness"]["readyForFinalRender"] else "needs_review"
    return review


def review_readiness(review: dict[str, Any]) -> dict[str, Any]:
    sections = list(_iter_sections(review))
    unresolved = [
        section.get("key", "")
        for section in sections
        if section.get("status", "needs_review") not in {"approved", "locked"}
    ]
    rejected = [section.get("key", "") for section in sections if section.get("status") == "rejected"]
    return {
        "readyForPreview": True,
        "readyForFinalRender": not unresolved and not rejected,
        "totalSections": len(sections),
        "unresolvedCount": len(unresolved),
        "rejectedCount": len(rejected),
        "unresolvedSections": unresolved[:50],
        "rejectedSections": rejected[:50],
    }


def build_ai_reasoning(plan: dict[str, Any], project: dict[str, Any]) -> dict[str, Any]:
    brief = plan.get("contentBrief", {})
    style = plan.get("editingStyle", {})
    assets = project.get("assets", {}) if isinstance(project.get("assets"), dict) else {}
    scenes = plan.get("scenePlan", [])
    media_assets = [key for key in assets if key.startswith(("clip_", "image_"))]
    return {
        "reasoningVersion": 1,
        "hook": (
            f"The hook leads with the clearest pain point for {brief.get('productName', 'the product')} "
            f"so the first seconds explain why the viewer should keep watching."
        ),
        "sceneOrder": (
            f"The plan follows {brief.get('mode', 'content')} structure: "
            + ", ".join(scene.get("section", scene.get("id", "scene")) for scene in scenes[:8])
            + "."
        ),
        "style": (
            f"{style.get('stylePreset', 'clean_cinematic')} was chosen for the {style.get('tone', 'cinematic')} tone, "
            f"platform pacing, and visual keywords in the request."
        ),
        "footage": (
            f"{len(media_assets)} visual asset slot(s) are used in rotation."
            if media_assets
            else "No raw footage was supplied, so the plan uses generated title cards and motion graphics."
        ),
        "reviewNeeded": [
            "Confirm the hook matches the actual product promise.",
            "Check that captions are accurate and readable.",
            "Confirm scene timing feels right before final export.",
            "Verify any selected footage really shows the described feature.",
            "Approve the CTA before final render.",
        ],
    }


def compare_content_versions(
    previous_plan: dict[str, Any],
    next_plan: dict[str, Any],
    *,
    previous_project: dict[str, Any] | None = None,
    next_project: dict[str, Any] | None = None,
    previous_render: str | None = None,
    next_render: str | None = None,
) -> dict[str, Any]:
    old_script = previous_plan.get("script", {}).get("lines", [])
    new_script = next_plan.get("script", {}).get("lines", [])
    old_scenes = _scene_rows(previous_plan.get("scenePlan", []))
    new_scenes = _scene_rows(next_plan.get("scenePlan", []))
    old_json = json.dumps(previous_project or previous_plan, indent=2, sort_keys=True).splitlines()
    new_json = json.dumps(next_project or next_plan, indent=2, sort_keys=True).splitlines()
    return {
        "comparisonVersion": 1,
        "generatedAt": _now(),
        "oldHook": previous_plan.get("hook", ""),
        "newHook": next_plan.get("hook", ""),
        "scriptDiff": _unified(old_script, new_script, "old_script", "new_script"),
        "scenePlanDiff": _unified(old_scenes, new_scenes, "old_scene_plan", "new_scene_plan"),
        "jsonDiff": _unified(old_json, new_json, "old_json", "new_json", limit=240),
        "renderComparison": {
            "oldRender": previous_render,
            "newRender": next_render,
            "note": "Open the listed files side by side in the desktop app for visual render comparison."
            if previous_render or next_render
            else "No rendered files were supplied for comparison.",
        },
        "summary": {
            "scriptLinesChanged": old_script != new_script,
            "scenePlanChanged": old_scenes != new_scenes,
            "styleChanged": previous_plan.get("editingStyle", {}).get("stylePreset") != next_plan.get("editingStyle", {}).get("stylePreset"),
        },
    }


def write_review_outputs(
    output_dir: Path,
    plan: dict[str, Any],
    project: dict[str, Any],
    *,
    comparison: dict[str, Any] | None = None,
) -> dict[str, Path]:
    review = plan.get("approval") or build_generation_review(plan, project)
    reasoning = plan.get("reasoning") or build_ai_reasoning(plan, project)
    paths = {
        "generation_review": output_dir / "generation_review.json",
        "approval_state": output_dir / "approval_state.json",
        "ai_reasoning": output_dir / "ai_reasoning_summary.txt",
    }
    _write_json(paths["generation_review"], review)
    _write_json(paths["approval_state"], {"approval": review, "readiness": review.get("readiness", {})})
    paths["ai_reasoning"].write_text(reasoning_text(reasoning), encoding="utf-8")
    if comparison:
        paths["version_comparison"] = output_dir / "version_comparison.json"
        paths["version_comparison_text"] = output_dir / "version_comparison.md"
        _write_json(paths["version_comparison"], comparison)
        paths["version_comparison_text"].write_text(comparison_markdown(comparison), encoding="utf-8")
    return paths


def reasoning_text(reasoning: dict[str, Any]) -> str:
    lines = [
        "AI Reasoning Summary",
        "====================",
        "",
        f"Hook: {reasoning.get('hook', '')}",
        "",
        f"Scene order: {reasoning.get('sceneOrder', '')}",
        "",
        f"Style: {reasoning.get('style', '')}",
        "",
        f"Footage: {reasoning.get('footage', '')}",
        "",
        "Needs Review:",
    ]
    lines.extend(f"- {item}" for item in reasoning.get("reviewNeeded", []))
    return "\n".join(lines) + "\n"


def comparison_markdown(comparison: dict[str, Any]) -> str:
    lines = [
        "# Content Version Comparison",
        "",
        f"- Old hook: {comparison.get('oldHook', '')}",
        f"- New hook: {comparison.get('newHook', '')}",
        f"- Script changed: {comparison.get('summary', {}).get('scriptLinesChanged')}",
        f"- Scene plan changed: {comparison.get('summary', {}).get('scenePlanChanged')}",
        f"- Style changed: {comparison.get('summary', {}).get('styleChanged')}",
        "",
        "## Script Diff",
        "```diff",
        *comparison.get("scriptDiff", []),
        "```",
        "",
        "## Scene Plan Diff",
        "```diff",
        *comparison.get("scenePlanDiff", []),
        "```",
        "",
        "## JSON Diff",
        "```diff",
        *comparison.get("jsonDiff", []),
        "```",
        "",
        "## Render Comparison",
        f"- Old render: {comparison.get('renderComparison', {}).get('oldRender')}",
        f"- New render: {comparison.get('renderComparison', {}).get('newRender')}",
    ]
    return "\n".join(lines) + "\n"


def load_plan(path: Path) -> dict[str, Any]:
    return json.loads(path.resolve().read_text(encoding="utf-8"))


def save_plan(path: Path, plan: dict[str, Any]) -> None:
    _write_json(path.resolve(), plan)


def _section(key: str, label: str, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "status": "needs_review",
        "locked": False,
        **(extra or {}),
    }


def _iter_sections(review: dict[str, Any]):
    sections = review.get("sections", {})
    for value in sections.values():
        if isinstance(value, list):
            yield from value
        elif isinstance(value, dict):
            yield value


def _normalize_section_key(value: str) -> str:
    clean = value.strip().lower().replace(" ", "_")
    aliases = {
        "scene_plan": "scenes",
        "sceneplan": "scenes",
        "captions_only": "captions",
        "title_cards": "titlecards",
    }
    return aliases.get(clean, clean)


def _scene_rows(scenes: list[dict[str, Any]]) -> list[str]:
    rows = []
    for scene in scenes:
        rows.append(
            f"{scene.get('id')} | {scene.get('start')} | {scene.get('duration')} | "
            f"{scene.get('title')} | {scene.get('caption')}"
        )
    return rows


def _unified(old: list[Any], new: list[Any], fromfile: str, tofile: str, *, limit: int = 120) -> list[str]:
    old_lines = [str(item) for item in old]
    new_lines = [str(item) for item in new]
    diff = list(difflib.unified_diff(old_lines, new_lines, fromfile=fromfile, tofile=tofile, lineterm=""))
    if len(diff) > limit:
        return diff[:limit] + [f"... diff truncated after {limit} lines ..."]
    return diff


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
