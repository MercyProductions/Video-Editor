from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

from content.generator import run_content_generator
from content.profiles import load_profile
from content.thumbnails import generate_thumbnail_set
from metrics.store import record_metric
from parser.project_parser import ProjectParser
from quality.checker import run_quality_check
from renderer.renderer import VideoRenderer
from review.preflight import run_final_preflight
from social.posting_package import create_posting_package
from social.reformat import reformat_project
from styles.presets import list_styles, normalize_style


CONTENT_TYPES = {"auto", "youtube_shorts", "tiktok", "product_showcase", "tutorial", "promo_ad"}
PLATFORM_ALIASES = {
    "shorts": "youtube_shorts",
    "youtube_shorts": "youtube_shorts",
    "youtube_short": "youtube_shorts",
    "tiktok": "tiktok",
    "reels": "instagram_reels",
    "instagram": "instagram_reels",
    "instagram_reels": "instagram_reels",
    "youtube": "youtube_landscape",
    "youtube_landscape": "youtube_landscape",
    "landscape": "youtube_landscape",
    "square": "square",
}


def run_autonomous_production_pipeline(
    *,
    idea: str,
    output_dir: Path,
    assets_folder: Path | None = None,
    music_path: Path | None = None,
    logo_path: Path | None = None,
    profile: str | Path | None = None,
    platform: str | None = None,
    content_type: str = "auto",
    vibe: str | None = None,
    duration: float | None = None,
    approved: bool = False,
    render_preview: bool = True,
    final_render: bool = False,
    package: bool = False,
    variants: int = 4,
    quality: str = "preview",
    cache: bool = True,
    gpu: bool = False,
) -> dict[str, Any]:
    """Run a creator-controlled autonomous production pass.

    The pipeline intentionally composes the existing local engines instead of
    inventing a second renderer. Generated JSON remains the source of truth.
    """

    started = time.perf_counter()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    profile_data = load_profile(profile)
    chosen_mode = _choose_content_type(idea, content_type)
    chosen_platform = _choose_platform(platform, chosen_mode)
    chosen_tone = _choose_tone(idea, vibe, profile_data)
    chosen_style = _choose_style(idea, vibe, profile_data, chosen_mode)
    target_duration = _choose_duration(idea, duration, chosen_mode)

    autonomous_plan = _build_autonomous_plan(
        idea=idea,
        mode=chosen_mode,
        platform=chosen_platform,
        tone=chosen_tone,
        style=chosen_style,
        duration=target_duration,
        vibe=vibe,
        profile=profile_data,
        assets_folder=assets_folder,
        music_path=music_path,
    )
    _write_json(output_dir / "autonomous_plan.json", autonomous_plan)
    _write_json(output_dir / "autonomous_style_direction.json", autonomous_plan["styleDirection"])

    generator_summary = run_content_generator(
        idea=_generator_prompt(idea, autonomous_plan),
        output_dir=output_dir,
        mode=chosen_mode,
        product_name=None,
        target_platform=chosen_platform,
        goal=autonomous_plan["planning"]["goal"],
        bullet_points=autonomous_plan["planning"]["featurePriorities"],
        assets_folder=assets_folder.resolve() if assets_folder else None,
        music_path=music_path.resolve() if music_path else None,
        logo_path=logo_path.resolve() if logo_path else None,
        duration=target_duration,
        tone=chosen_tone,
        style=chosen_style,
        approved=approved,
        render=render_preview,
        quality="preview",
        cache=cache,
        gpu=gpu,
    )

    project_path = Path(str(generator_summary["projectPath"])).resolve()
    project = json.loads(project_path.read_text(encoding="utf-8"))
    if approved:
        project = _mark_project_approved(project_path, project)
    asset_selection = _asset_selection_report(output_dir, assets_folder)
    _write_json(output_dir / "autonomous_asset_selection.json", asset_selection)

    preview_video = _capture_preview_video(generator_summary, output_dir) if render_preview else None
    final_video: Path | None = None
    final_render_blocked = False
    final_render_block_reason: str | None = None
    if final_render:
        if approved:
            pre_render_preflight = run_final_preflight(
                project_path,
                preview_video=preview_video if preview_video and preview_video.exists() else None,
                output_path=output_dir / "autonomous_pre_render_preflight.json",
            )
            if int(pre_render_preflight.get("blockingCount", 0) or 0) > 0:
                final_render_blocked = True
                final_render_block_reason = "preflight_blocking_issues"
            else:
                final_video = output_dir / "final_video.mp4"
                parsed = ProjectParser().load(project_path)
                VideoRenderer(parsed, output_path=final_video, quality=quality, use_cache=cache, resume=cache, gpu=gpu).render()
        else:
            final_render_blocked = True
            final_render_block_reason = "creator_approval_required"

    check_video = final_video or preview_video
    quality_review = _quality_review(project_path, check_video, output_dir, profile_data, autonomous_plan)
    _write_json(output_dir / "autonomous_quality_review.json", quality_review)

    variants_report = _variant_report(
        project_path=project_path,
        video_path=check_video,
        output_dir=output_dir,
        plan=autonomous_plan,
        project=project,
        variants=variants,
    )
    _write_json(output_dir / "autonomous_variants.json", variants_report)

    package_report = None
    if package and final_video and final_video.exists():
        package_report = create_posting_package(
            project_path,
            final_video,
            output_dir=output_dir / "upload_package",
            platforms=_package_platforms(chosen_platform),
            title=autonomous_plan["planning"]["title"],
            accent_color=autonomous_plan["styleDirection"]["accentColor"],
        )

    explainability = _explainability_report(autonomous_plan, asset_selection, quality_review, final_render_blocked)
    _write_json(output_dir / "autonomous_explainability.json", explainability)
    (output_dir / "autonomous_explainability.txt").write_text(_explainability_text(explainability), encoding="utf-8")

    summary = {
        "mode": "autonomous_production_pipeline",
        "idea": idea,
        "projectPath": str(project_path),
        "contentPlanPath": generator_summary.get("contentPlanPath"),
        "generationReviewPath": generator_summary.get("generationReviewPath"),
        "approvalStatePath": generator_summary.get("approvalStatePath"),
        "reviewSummaryPath": generator_summary.get("reviewSummaryPath"),
        "aiReasoningPath": generator_summary.get("aiReasoningPath"),
        "autonomousPlanPath": str((output_dir / "autonomous_plan.json").resolve()),
        "assetSelectionPath": str((output_dir / "autonomous_asset_selection.json").resolve()),
        "styleDirectionPath": str((output_dir / "autonomous_style_direction.json").resolve()),
        "qualityReviewPath": str((output_dir / "autonomous_quality_review.json").resolve()),
        "variantsPath": str((output_dir / "autonomous_variants.json").resolve()),
        "explainabilityPath": str((output_dir / "autonomous_explainability.json").resolve()),
        "explainabilityTextPath": str((output_dir / "autonomous_explainability.txt").resolve()),
        "previewVideo": str(preview_video) if preview_video else None,
        "finalVideo": str(final_video) if final_video else None,
        "postingPackagePath": package_report.get("rootPackage", {}).get("folder") if package_report else None,
        "finalRenderBlocked": final_render_blocked,
        "finalRenderBlockReason": final_render_block_reason,
        "humanApproval": {
            "requiredForFinalRender": True,
            "approved": approved,
            "approvalReady": generator_summary.get("approvalReady", False),
            "unresolvedReviewSections": generator_summary.get("unresolvedReviewSections", []),
            "creatorControls": ["approve", "lock", "regenerate", "override", "exclude", "choose export"],
        },
        "planning": autonomous_plan["planning"],
        "styleDirection": autonomous_plan["styleDirection"],
        "qualityReview": {
            "readinessScore": quality_review["readinessScore"],
            "blockingIssues": quality_review["blockingIssues"],
            "warnings": quality_review["warnings"][:10],
        },
        "variants": variants_report,
        "warnings": _combined_warnings(generator_summary, quality_review, final_render_blocked, final_render_block_reason),
        "elapsedSeconds": round(time.perf_counter() - started, 3),
        "localFirst": True,
    }
    _write_json(output_dir / "autonomous_pipeline_summary.json", summary)
    record_metric(
        "autonomous_pipeline",
        {
            "mode": chosen_mode,
            "platform": chosen_platform,
            "style": chosen_style,
            "duration": target_duration,
            "approved": approved,
            "previewRendered": bool(preview_video),
            "finalRendered": bool(final_video),
            "readinessScore": quality_review["readinessScore"],
            "elapsedSeconds": summary["elapsedSeconds"],
        },
    )
    return summary


def _choose_content_type(idea: str, content_type: str) -> str:
    requested = (content_type or "auto").strip().lower()
    if requested in CONTENT_TYPES and requested != "auto":
        return requested
    lower = idea.lower()
    if "tutorial" in lower or "walkthrough" in lower or "step by step" in lower:
        return "tutorial"
    if "tiktok" in lower:
        return "tiktok"
    if "ad" in lower or "promo" in lower or "buy" in lower:
        return "promo_ad"
    if any(word in lower for word in ["showcase", "demo", "product", "software", "dashboard", "cyber", "security"]):
        return "product_showcase"
    return "youtube_shorts"


def _choose_platform(platform: str | None, mode: str) -> str:
    if platform:
        return PLATFORM_ALIASES.get(platform.strip().lower(), platform.strip().lower())
    if mode == "tiktok":
        return "tiktok"
    if mode in {"product_showcase", "tutorial", "promo_ad", "youtube_shorts"}:
        return "youtube_shorts"
    return "youtube_shorts"


def _choose_tone(idea: str, vibe: str | None, profile: dict[str, Any]) -> str:
    text = f"{idea} {vibe or ''}".lower()
    if any(word in text for word in ["aggressive", "fast", "hype", "bass", "gaming"]):
        return "aggressive"
    if any(word in text for word in ["minimal", "elegant", "quiet", "clean"]):
        return "minimal" if "minimal" in text else "clean"
    memory = str(profile.get("pacingStyle") or profile.get("preferredPacing") or "").lower()
    if "aggressive" in memory:
        return "aggressive"
    if "minimal" in memory:
        return "minimal"
    return "cinematic"


def _choose_style(idea: str, vibe: str | None, profile: dict[str, Any], mode: str) -> str:
    text = f"{idea} {vibe or ''}".lower()
    if "red" in text or "cyber" in text or "security" in text or "aegis" in text:
        return "red_black_aegis"
    if "gaming" in text or mode == "tiktok":
        return "gaming_montage"
    if "luxury" in text or "premium" in text:
        return "luxury_promo"
    if "minimal" in text or mode == "tutorial":
        return "minimal_tech"
    preferred = profile.get("stylePreset") or profile.get("preferredStyle")
    if isinstance(preferred, str):
        normalized = normalize_style(preferred)
        if normalized in list_styles():
            return normalized
    return "clean_cinematic"


def _choose_duration(idea: str, duration: float | None, mode: str) -> float:
    if duration:
        return round(max(8.0, min(float(duration), 90.0)), 3)
    lower = idea.lower()
    if "under 45" in lower or "45 second" in lower or "45-second" in lower:
        return 44.0
    if "30 second" in lower or "30-second" in lower:
        return 30.0
    if mode == "tutorial":
        return 45.0
    if mode == "product_showcase":
        return 35.0
    return 32.0


def _build_autonomous_plan(
    *,
    idea: str,
    mode: str,
    platform: str,
    tone: str,
    style: str,
    duration: float,
    vibe: str | None,
    profile: dict[str, Any],
    assets_folder: Path | None,
    music_path: Path | None,
) -> dict[str, Any]:
    stages = _stages_for(mode, duration)
    product = _product_name(idea)
    feature_priorities = _feature_priorities(idea)
    pacing_curve = _pacing_curve(stages, tone)
    return {
        "version": 1,
        "localFirst": True,
        "idea": idea,
        "planning": {
            "title": _title_for(product, mode),
            "productName": product,
            "goal": _goal_for(product, mode, platform),
            "mode": mode,
            "platform": platform,
            "duration": duration,
            "sceneCount": len(stages),
            "hookStrategy": _hook_strategy(idea, mode, tone),
            "revealTiming": _reveal_timing(stages),
            "ctaPlacement": "final 10-12% of the timeline",
            "featurePriorities": feature_priorities,
            "stages": stages,
            "pacingCurve": pacing_curve,
        },
        "assetStrategy": {
            "assetsFolder": str(assets_folder.resolve()) if assets_folder else None,
            "music": str(music_path.resolve()) if music_path else None,
            "selectionRules": [
                "prefer high motion or loudness spikes",
                "trim around highlight windows",
                "avoid likely dead footage",
                "reuse visual motifs only when they strengthen continuity",
            ],
            "deadFootagePolicy": "skip or shorten low-energy stretches",
        },
        "styleDirection": {
            "stylePreset": style,
            "tone": tone,
            "requestedVibe": vibe,
            "captionStyle": _caption_style_for(mode, tone, profile),
            "transitionStyle": _transition_style_for(style, tone),
            "lighting": _lighting_for(style, tone),
            "motionIntensity": _motion_intensity_for(tone),
            "accentColor": _accent_color_for(style, profile),
            "musicSync": bool(music_path),
        },
        "humanApproval": {
            "finalRenderRequiresApproval": True,
            "lockableSections": ["hook", "script", "scene", "caption", "style", "music", "timing", "title"],
            "availableOverrides": ["regenerate", "approve", "reject", "exclude", "manual JSON edit"],
        },
        "explainability": {
            "sceneStructureReason": f"{mode.replace('_', ' ')} uses a hook, progressive proof, payoff, and CTA so the viewer always knows why the clip matters.",
            "styleReason": _style_reason(style, tone, idea),
            "assetReason": "The asset pass scores footage by motion, loudness, highlight potential, and dead-footage risk.",
            "approvalReason": "Final export is gated so autonomous edits stay reviewable and creator-controlled.",
        },
    }


def _generator_prompt(idea: str, plan: dict[str, Any]) -> str:
    style = plan["styleDirection"]
    stages = ", ".join(stage["name"] for stage in plan["planning"]["stages"])
    features = ", ".join(plan["planning"]["featurePriorities"])
    return (
        f"{idea}\n"
        f"Autonomous plan: {plan['planning']['mode']} for {plan['planning']['platform']} under {plan['planning']['duration']} seconds. "
        f"Use stages: {stages}. Prioritize: {features}. "
        f"Style: {style['stylePreset']} / {style['tone']}; transitions: {style['transitionStyle']}; "
        f"captions: {style['captionStyle']['density']} and readable."
    )


def _asset_selection_report(output_dir: Path, assets_folder: Path | None) -> dict[str, Any]:
    clip_selection_path = output_dir / "clip_selection.json"
    if clip_selection_path.exists():
        report = json.loads(clip_selection_path.read_text(encoding="utf-8"))
    else:
        report = {"folder": str(assets_folder.resolve()) if assets_folder else None, "selected": [], "clips": [], "warnings": []}
    selected = report.get("selected", [])
    return {
        "folder": report.get("folder"),
        "scannedClipCount": report.get("scannedClipCount", 0),
        "selectedClipCount": report.get("selectedClipCount", len(selected)),
        "selected": [
            {
                "path": item.get("path"),
                "highlightStart": item.get("highlightStart"),
                "highlightDuration": item.get("highlightDuration"),
                "highlightScore": item.get("highlightScore"),
                "reason": item.get("highlightReason") or _selection_reason(item),
                "tags": item.get("tags", []),
            }
            for item in selected
        ],
        "warnings": report.get("warnings", []),
        "explainability": [
            "Selected clips are reused through the generated scene plan as immutable source references.",
            "Trimming remains non-destructive through JSON trimStart/trimEnd instructions.",
        ],
    }


def _capture_preview_video(generator_summary: dict[str, Any], output_dir: Path) -> Path | None:
    render_path = generator_summary.get("renderPath")
    if not render_path:
        return None
    source = Path(str(render_path)).resolve()
    if not source.exists():
        return None
    preview = output_dir / "preview_video.mp4"
    if source.resolve() != preview.resolve():
        shutil.copy2(source, preview)
    return preview.resolve()


def _mark_project_approved(project_path: Path, project: dict[str, Any]) -> dict[str, Any]:
    for scene in project.get("timeline", []):
        if not scene.get("excludeFromFinal"):
            scene["reviewStatus"] = "locked" if scene.get("reviewStatus") == "locked" else "approved"
    project.setdefault("metadata", {}).setdefault("autonomousPipeline", {})["creatorApproved"] = True
    project["metadata"]["autonomousPipeline"]["approvalNote"] = "Approved via autonomous pipeline --approved flag."
    project_path.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
    return project


def _quality_review(
    project_path: Path,
    video_path: Path | None,
    output_dir: Path,
    profile: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    quality = run_quality_check(project_path, output_path=output_dir / "autonomous_quality_check.json")
    preflight = run_final_preflight(
        project_path,
        preview_video=video_path if video_path and video_path.exists() else None,
        output_path=output_dir / "autonomous_preflight.json",
    )
    issue_count = int(quality.get("issueCount", 0) or 0) + int(preflight.get("issueCount", 0) or 0)
    blocking = int(preflight.get("blockingCount", 0) or 0)
    readability = float(preflight.get("scores", {}).get("readability", 100) or 100)
    pacing = _pacing_score(plan, preflight)
    creator_consistency = _creator_consistency_score(profile, plan)
    readiness = max(0, min(100, round((float(preflight.get("exportReadinessScore", 80) or 80) + readability + pacing + creator_consistency) / 4 - blocking * 8 - issue_count * 0.7)))
    warnings = [str(issue.get("message")) for issue in preflight.get("issues", []) if issue.get("severity") in {"warning", "error"}]
    return {
        "qualityCheckPath": str((output_dir / "autonomous_quality_check.json").resolve()),
        "preflightPath": str((output_dir / "autonomous_preflight.json").resolve()),
        "readinessScore": readiness,
        "scores": {
            "pacing": pacing,
            "readability": round(readability),
            "visualClarity": float(preflight.get("scores", {}).get("technical", 86) or 86),
            "audioBalance": float(preflight.get("scores", {}).get("audio", 82) or 82),
            "creatorConsistency": creator_consistency,
        },
        "blockingIssues": blocking,
        "issueCount": issue_count,
        "warnings": warnings,
        "qualityCheck": quality,
        "preflight": preflight,
    }


def _variant_report(
    *,
    project_path: Path,
    video_path: Path | None,
    output_dir: Path,
    plan: dict[str, Any],
    project: dict[str, Any],
    variants: int,
) -> dict[str, Any]:
    count = max(1, min(int(variants or 1), 8))
    export_versions = reformat_project(
        project_path,
        ["youtube_shorts", "tiktok", "instagram_reels", "youtube_landscape", "discord"],
        output_dir / "export_versions",
    )
    thumbnail_report = None
    if video_path and video_path.exists():
        try:
            thumbnail_report = generate_thumbnail_set(
                video_path,
                title=plan["planning"]["title"],
                output_dir=output_dir / "autonomous_thumbnails",
                accent_color=plan["styleDirection"]["accentColor"],
            )
        except Exception as exc:
            thumbnail_report = {"error": f"Thumbnail generation skipped: {exc}"}
    return {
        "hookVariants": _hook_variants(plan, count),
        "pacingVariants": _pacing_variants(plan, count),
        "ctaVariants": _cta_variants(plan, project, count),
        "thumbnailVariants": thumbnail_report,
        "exportVersions": export_versions,
        "notes": "Variants are planning/export artifacts until the creator chooses which versions to render.",
    }


def _explainability_report(
    plan: dict[str, Any],
    asset_selection: dict[str, Any],
    quality_review: dict[str, Any],
    final_render_blocked: bool,
) -> dict[str, Any]:
    selected = asset_selection.get("selected", [])
    return {
        "whyStructure": plan["explainability"]["sceneStructureReason"],
        "whyStyle": plan["explainability"]["styleReason"],
        "whyClips": [
            f"{Path(str(item.get('path', 'clip'))).name}: {item.get('reason')} (score {item.get('highlightScore')})"
            for item in selected[:8]
        ]
        or ["No source clips were selected; the generated edit relies on title cards, images, and text overlays."],
        "whyPacing": f"Pacing follows {plan['planning']['pacingCurve']['shape']} with reveal at {plan['planning']['revealTiming']['primaryRevealAt']}s.",
        "whyEffects": f"Effects follow {plan['styleDirection']['stylePreset']} with {plan['styleDirection']['motionIntensity']} motion intensity and {plan['styleDirection']['lighting']['intensity']} lighting.",
        "qualityDecision": f"Autonomous readiness score is {quality_review['readinessScore']}/100 with {quality_review['blockingIssues']} blocking issues.",
        "approvalDecision": (
            "Final render was blocked by approval or preflight gate; review warnings before export."
            if final_render_blocked
            else "Creator approval state was respected."
        ),
        "safeBoundaries": [
            "The pipeline only writes generated project files and outputs.",
            "Source media is referenced non-destructively.",
            "Final rendering and posting packages require explicit creator approval.",
        ],
    }


def _explainability_text(report: dict[str, Any]) -> str:
    lines = [
        "Autonomous Production Explainability",
        "=" * 38,
        f"Structure: {report['whyStructure']}",
        f"Style: {report['whyStyle']}",
        f"Pacing: {report['whyPacing']}",
        f"Effects: {report['whyEffects']}",
        f"Quality: {report['qualityDecision']}",
        f"Approval: {report['approvalDecision']}",
        "",
        "Clip Choices:",
    ]
    lines.extend(f"- {item}" for item in report["whyClips"])
    lines.append("")
    lines.append("Safety Boundaries:")
    lines.extend(f"- {item}" for item in report["safeBoundaries"])
    return "\n".join(lines) + "\n"


def _stages_for(mode: str, duration: float) -> list[dict[str, Any]]:
    if mode == "tutorial":
        ratios = [("hook", 0.12), ("setup", 0.14), ("steps", 0.52), ("result", 0.14), ("cta", 0.08)]
    elif mode == "promo_ad":
        ratios = [("hook", 0.15), ("problem", 0.2), ("solution", 0.4), ("proof", 0.15), ("cta", 0.1)]
    elif mode == "product_showcase":
        ratios = [("intro", 0.14), ("feature_reveal", 0.26), ("interaction_highlight", 0.32), ("payoff", 0.18), ("cta", 0.1)]
    else:
        ratios = [("hook", 0.1), ("problem", 0.18), ("feature_showcase", 0.42), ("result", 0.2), ("cta", 0.1)]
    cursor = 0.0
    stages = []
    for index, (name, ratio) in enumerate(ratios):
        stage_duration = round(duration * ratio, 3)
        if index == len(ratios) - 1:
            stage_duration = round(max(duration - cursor, 0.5), 3)
        stages.append({"name": name, "start": round(cursor, 3), "duration": stage_duration, "end": round(cursor + stage_duration, 3)})
        cursor += stage_duration
    return stages


def _pacing_curve(stages: list[dict[str, Any]], tone: str) -> dict[str, Any]:
    shape = "fast crescendo" if tone == "aggressive" else "smooth cinematic reveal"
    if tone in {"minimal", "clean"}:
        shape = "clean proof-first ramp"
    return {
        "shape": shape,
        "beats": [
            {"time": stage["start"], "intent": "reset attention" if index == 0 else "advance proof"}
            for index, stage in enumerate(stages)
        ],
    }


def _reveal_timing(stages: list[dict[str, Any]]) -> dict[str, Any]:
    reveal = next((stage for stage in stages if stage["name"] in {"feature_reveal", "feature_showcase", "solution", "steps"}), stages[min(1, len(stages) - 1)])
    payoff = next((stage for stage in stages if stage["name"] in {"payoff", "result", "proof"}), stages[-2])
    return {"primaryRevealAt": reveal["start"], "payoffAt": payoff["start"], "ctaAt": stages[-1]["start"]}


def _feature_priorities(idea: str) -> list[str]:
    lowered = idea.replace(" and ", ", ").replace(";", ",")
    parts = []
    for raw in lowered.split(","):
        item = raw.strip(" .")
        if len(item) < 4:
            continue
        if any(skip in item.lower() for skip in ["create ", "make ", "youtube", "tiktok", "seconds", "cinematic"]):
            continue
        parts.append(_sentence(item))
    return parts[:6] or ["Clear problem detection", "Fast visual proof", "Clean result moment"]


def _product_name(idea: str) -> str:
    lower = idea.lower()
    if "for my " in lower:
        start = lower.index("for my ") + len("for my ")
        chunk = idea[start:].split(".")[0].split(",")[0]
        return _title_case(" ".join(chunk.split()[:5]))
    if "automatic troubleshooter" in lower:
        return "Automatic Troubleshooter"
    words = [word.strip(".,:;!?") for word in idea.split() if word.strip(".,:;!?")]
    return _title_case(" ".join(words[:4])) if words else "Creator Project"


def _title_for(product: str, mode: str) -> str:
    if mode == "tutorial":
        return f"{product} Workflow"
    if mode == "promo_ad":
        return f"{product} Fixes the Blocker"
    return f"{product} Showcase"


def _goal_for(product: str, mode: str, platform: str) -> str:
    platform_label = platform.replace("_", " ")
    if mode == "tutorial":
        return f"Teach viewers the clearest way to use {product} on {platform_label}."
    if mode == "promo_ad":
        return f"Turn {product} into a problem/solution ad for {platform_label}."
    return f"Create a near-finished cinematic {product} video for {platform_label}."


def _hook_strategy(idea: str, mode: str, tone: str) -> str:
    lower = idea.lower()
    if "problem" in lower or "troubleshooter" in lower:
        return "problem-first hook with immediate pain point"
    if mode == "tutorial":
        return "clarity hook with visible outcome"
    if tone == "aggressive":
        return "fast disruption hook with high caption density"
    return "premium reveal hook with concise benefit"


def _caption_style_for(mode: str, tone: str, profile: dict[str, Any]) -> dict[str, Any]:
    profile_style = profile.get("captionStyle", {})
    density = "high" if mode in {"youtube_shorts", "tiktok"} else "medium"
    if tone in {"minimal", "clean"}:
        density = "medium"
    return {
        "density": density,
        "fontSize": int(profile_style.get("fontSize", 58) or 58),
        "safeZone": "lower_third",
        "readability": "large stroke, short phrases, no more than two caption beats per second",
    }


def _transition_style_for(style: str, tone: str) -> str:
    if tone == "aggressive" or style == "gaming_montage":
        return "fast zoom hits"
    if style == "red_black_aegis":
        return "fade-to-black with red accent pulses"
    if style == "minimal_tech":
        return "clean crossfades"
    return "smooth cinematic crossfades"


def _lighting_for(style: str, tone: str) -> dict[str, Any]:
    if style == "red_black_aegis":
        return {"theme": "red_black", "intensity": 0.48, "behavior": "subtle glow with darker edges"}
    if style == "luxury_promo":
        return {"theme": "warm_luxury", "intensity": 0.35, "behavior": "soft highlights and vignette"}
    if tone == "minimal":
        return {"theme": "neutral_clean", "intensity": 0.18, "behavior": "low contrast preservation"}
    return {"theme": "cool_cinematic", "intensity": 0.3, "behavior": "contrast lift with gentle vignette"}


def _motion_intensity_for(tone: str) -> str:
    if tone == "aggressive":
        return "high"
    if tone in {"minimal", "clean"}:
        return "low_medium"
    return "medium"


def _accent_color_for(style: str, profile: dict[str, Any]) -> str:
    branding = profile.get("branding", {}) if isinstance(profile.get("branding"), dict) else {}
    if isinstance(branding.get("primaryColor"), str) and branding.get("primaryColor"):
        return str(branding["primaryColor"])
    return {
        "red_black_aegis": "#ef4444",
        "gaming_montage": "#f97316",
        "minimal_tech": "#2563eb",
        "luxury_promo": "#f5d46b",
    }.get(style, "#6db5a5")


def _style_reason(style: str, tone: str, idea: str) -> str:
    if style == "red_black_aegis":
        return "Red/black cinematic styling fits security, diagnostics, and premium technical demos."
    if style == "gaming_montage":
        return "High-energy zooms and faster transitions fit aggressive short-form pacing."
    if style == "minimal_tech":
        return "Minimal tech styling protects readability and keeps instructional scenes clear."
    if style == "luxury_promo":
        return "Luxury promo styling supports premium reveals and slower payoff timing."
    return f"Clean cinematic styling is a balanced fit for a {tone} edit from this prompt."


def _selection_reason(item: dict[str, Any]) -> str:
    tags = item.get("tags") or []
    if "motion_spike" in tags:
        return "strong motion spike"
    if "loud_reaction" in tags:
        return "loudness peak"
    if "possible_kill_or_payoff" in tags:
        return "likely payoff moment"
    return "best available highlight score"


def _pacing_score(plan: dict[str, Any], preflight: dict[str, Any]) -> int:
    stage_count = len(plan["planning"]["stages"])
    warnings = int(preflight.get("warningsRemaining", 0) or 0)
    base = 90 if 4 <= stage_count <= 7 else 76
    return max(0, min(100, base - warnings * 2))


def _creator_consistency_score(profile: dict[str, Any], plan: dict[str, Any]) -> int:
    score = 82
    preferred = normalize_style(str(profile.get("stylePreset") or profile.get("preferredStyle") or ""))
    if preferred and preferred == plan["styleDirection"]["stylePreset"]:
        score += 10
    preferred_preset = profile.get("exportSettings", {}).get("preset") if isinstance(profile.get("exportSettings"), dict) else None
    if preferred_preset and str(preferred_preset) in {plan["planning"]["platform"], "shorts"}:
        score += 4
    return max(0, min(100, score))


def _hook_variants(plan: dict[str, Any], count: int) -> list[dict[str, str]]:
    product = plan["planning"]["productName"]
    features = plan["planning"]["featurePriorities"]
    options = [
        ("serious", f"Stop guessing. {product} shows the blocker."),
        ("curiosity", f"What if {product} could reveal the issue in seconds?"),
        ("problem_solution", f"Apps fail for hidden reasons. {product} makes them visible."),
        ("fast_aggressive", f"Find the launch blocker before it wastes another minute."),
        ("clean_professional", f"A cleaner way to diagnose launch problems with {product}."),
    ]
    if features:
        options.append(("feature_first", f"{features[0]} finally gets a clear visual workflow."))
    return [{"style": key, "hook": value} for key, value in options[:count]]


def _pacing_variants(plan: dict[str, Any], count: int) -> list[dict[str, Any]]:
    duration = float(plan["planning"]["duration"])
    variants = [
        {"name": "balanced", "duration": duration, "transitionFrequency": "scene", "motion": plan["styleDirection"]["motionIntensity"]},
        {"name": "faster_cut", "duration": round(duration * 0.86, 2), "transitionFrequency": "high", "motion": "medium_high"},
        {"name": "premium_slow_reveal", "duration": round(duration * 1.08, 2), "transitionFrequency": "medium_low", "motion": "medium"},
        {"name": "caption_heavy", "duration": duration, "transitionFrequency": "medium", "motion": "medium_low"},
    ]
    return variants[:count]


def _cta_variants(plan: dict[str, Any], project: dict[str, Any], count: int) -> list[dict[str, str]]:
    product = plan["planning"]["productName"]
    mode = plan["planning"]["mode"]
    options = [
        {"style": "direct", "cta": f"Try {product} before the next blocker costs time."},
        {"style": "follow", "cta": f"Follow for more clean {product} workflows."},
        {"style": "download", "cta": f"Download {product} and scan before you guess."},
        {"style": "comment", "cta": "Comment the blocker you want diagnosed next."},
        {"style": "save", "cta": "Save this workflow for your next troubleshooting session."},
    ]
    if mode == "tutorial":
        options.insert(0, {"style": "tutorial_save", "cta": "Save this for the next setup issue."})
    return options[:count]


def _package_platforms(platform: str) -> list[str]:
    if platform in {"youtube_shorts", "shorts"}:
        return ["youtube_shorts", "tiktok", "instagram_reels"]
    if platform == "tiktok":
        return ["tiktok", "youtube_shorts", "instagram_reels"]
    if platform == "youtube_landscape":
        return ["youtube_landscape", "x_twitter", "discord"]
    return [platform]


def _combined_warnings(
    generator_summary: dict[str, Any],
    quality_review: dict[str, Any],
    final_render_blocked: bool,
    final_render_block_reason: str | None,
) -> list[str]:
    warnings = [str(item) for item in generator_summary.get("warnings", [])]
    warnings.extend(quality_review.get("warnings", [])[:8])
    if final_render_blocked:
        if final_render_block_reason == "preflight_blocking_issues":
            warnings.append("Final render/package skipped because pre-render preflight found blocking issues.")
        else:
            warnings.append("Final render/package skipped until creator approval is provided.")
    return warnings


def _sentence(text: str) -> str:
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return cleaned
    return cleaned[0].upper() + cleaned[1:]


def _title_case(text: str) -> str:
    words = [word for word in text.replace("_", " ").split() if word]
    return " ".join(word[:1].upper() + word[1:].lower() for word in words) or "Creator Project"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
