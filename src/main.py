from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Callable

from ai.director import run_ai_director
from ai.generator import generate_project_from_prompt
from advanced import apply_advanced_cinematic_engine
from analytics.creator import creator_analytics
from audio.intelligence import analyze_audio_intelligence
from automation.hooks import process_queue_folder, watch_project_folder
from assets.database import database_report, duplicate_assets, index_folder, search_assets, track_project_usage
from assets.intelligence import analyze_asset_library
from assets.resolver import AssetResolver
from beginner.auto_template import template_catalog as beginner_template_catalog
from beginner.auto_template import template_names as beginner_template_names
from beginner.auto_template import run_beginner_auto_template
from broll.resolver import resolve_broll_layers
from brand.kit import apply_brand_kit, create_brand_kit
from captions.engine import add_captions_from_transcript
from cinematic.enhancer import apply_cinematic_enhancement, list_cinematic_presets
from clips.selector import select_highlights
from color.pipeline import apply_color_pipeline, list_color_presets, list_luts
from collab.manifest import check_portability, generate_project_manifest
from collab.review import add_comment, add_marker, compare_projects, export_review_report, load_review, lock_asset, set_role, set_scene_status
from content.autonomous import run_autonomous_production_pipeline
from content.generator import run_content_generator
from content.pipeline import run_batch_generation, run_project_pipeline
from content.profiles import apply_profile_to_project, create_profile, list_profiles, load_profile
from content.review import (
    build_generation_review,
    compare_content_versions,
    comparison_markdown,
    load_plan,
    save_plan,
    set_review_status,
    write_review_outputs,
)
from content.scene_builder import build_scene_prompt
from content.suggestions import suggest_scene_improvements
from content.thumbnails import generate_thumbnail_set
from content.youtube_shorts import run_youtube_shorts_auto
from datasets.exporter import export_training_dataset
from docs.local_docs import list_docs, read_doc
from effects.graph import list_effect_graph_presets
from ecosystem.local_policy import init_local_policy, load_local_policy
from engines.registry import api_surface, engine_registry
from evolution.report import build_evolution_report
from feedback.cli import run_feedback_command
from finalization.audit import architecture_audit
from finalization.profiler import profile_workflow
from finalization.release import release_candidate_check
from foundation import run_foundation_pass
from history.version_history import list_versions, rollback_version
from intelligence.beat_sync import analyze_audio, apply_beat_sync
from intelligence.clip_understanding import understand_clip, understand_folder
from intelligence.project_analyzer import analyze_project
from intelligence.smart_builder import build_smart_project
from media.compat import analyze_media, export_format_from_path, import_media_files
from metrics.store import metrics_from_project, record_metric, summarize_metrics
from mvp.quick_create import create_quick_project
from parser.project_parser import ProjectParser
from presets.export_presets import get_export_preset, list_export_presets
from preview.interactive import generate_interactive_preview
from preview.realtime import generate_realtime_preview
from preview.reporter import generate_preview
from project_packaging.project_package import export_project_package, open_project_package
from local_ai.engine import local_ai_status, local_caption_from_transcript, local_prompt_to_json, local_repair, local_scene_suggestions, local_transcribe
from local_ai.model_manager import model_manager_status, save_model_selection
from plugins.registry import audit_plugins, init_plugin, list_plugins, set_plugin_enabled
from quality.checker import run_quality_check
from recovery.integrity import check_project_integrity, relink_missing_assets
from recovery.recovery import autosave_project, backup_project, cleanup_recovery_points, create_restore_point, list_recovery_points, recover_corrupted_project, restore_recovery_point
from renderer.reliability import reliable_render_project
from renderer.renderer import VideoRenderer
from refinement.polish import list_polish_presets, refine_project
from repair.repairer import repair_project_file
from review.preflight import repair_final_preflight, run_final_preflight
from schema.validator import ProjectValidationError, validate_project
from security.privacy import privacy_security_report
from showcase import build_showcase_project, list_showcase_styles
from social.post_export import (
    create_post_export_variants,
    create_quick_reexport_project,
    record_success_note,
    review_export,
    save_reusable_template,
)
from social.posting_package import create_posting_package
from social.repurpose import repurpose_project
from social.reformat import reformat_project
from stability.cache import cache_report, cleanup_caches
from stability.dependencies import offline_dependency_report
from stability.diagnostics import repair_project as diagnostics_repair_project
from stability.diagnostics import run_diagnostics
from stability.performance import performance_dashboard_report
from storyboard.generator import generate_storyboard
from styles.presets import apply_style, list_styles
from templates.catalog import create_project_from_template, list_templates, template_names
from templates.template_packs import export_template_pack, install_template_pack, template_pack_catalog
from packs.portable_pack import export_pack, import_pack, list_installed_packs
from installer.local_installer import create_first_run_setup, create_installer_manifest, create_portable_zip, prepare_local_folders
from workers.local_render import enqueue_render, run_worker, worker_status
from workflow.cli import run_workflow_command
from workspace.system import add_workspace_profile, close_project, create_workspace, describe_workspace, list_workspace_profiles, list_workspaces, open_project, save_layout
from cli_parser import COMMANDS, build_parser

_CommandHandler = Callable[[argparse.Namespace], int]


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="[%(levelname)s] %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if raw_argv and raw_argv[0] not in COMMANDS and not raw_argv[0].startswith("-"):
        raw_argv.insert(0, "render")

    args = build_parser().parse_args(raw_argv)
    configure_logging(args.log_level)

    handler = _COMMAND_HANDLERS.get(args.command)
    if handler:
        return handler(args)

    build_parser().print_help()
    return 2


def _cmd_render(args: argparse.Namespace) -> int:
    started = time.perf_counter()
    project_path = Path(args.project_json).resolve()
    if args.repair:
        repaired_path = _default_repaired_path(project_path)
        result = repair_project_file(project_path, repaired_path)
        _print_repair_result(result, repaired_path)
        if not result.valid:
            return 1
        project_path = repaired_path

    if args.preset:
        project_path = _write_preset_override(project_path, args.preset)

    parser = ProjectParser()
    project = parser.load(project_path)
    if args.preview:
        preview = generate_preview(project, generate_placeholders=args.generate_placeholders)
        logging.info("Preview summary: %s", preview.summary_path)
        logging.info("Render plan: %s", preview.plan_path)

    output_path = _render_output_path(args.output, args.format)
    renderer = VideoRenderer(
        project,
        output_path=output_path,
        keep_temp=args.keep_temp,
        generate_placeholders=args.generate_placeholders,
        quality=args.quality,
        use_cache=args.cache,
        resume=args.resume,
        gpu=args.gpu or args.backend in {"gpu", "hybrid"},
    )
    final_path = renderer.render()
    record_metric(
        "render",
        {
            **metrics_from_project(project.raw),
            "project": str(project.path),
            "output": str(final_path),
            "outputSize": final_path.stat().st_size if final_path.exists() else 0,
            "renderSeconds": round(time.perf_counter() - started, 3),
            "quality": args.quality,
            "preset": args.preset or project.export_preset,
            "backend": args.backend,
            "gpu": args.gpu or args.backend in {"gpu", "hybrid"},
            "cache": args.cache,
            "format": export_format_from_path(final_path),
        },
    )
    logging.info("Export complete: %s", final_path)
    return 0


def _render_output_path(raw_output: str | None, output_format: str | None) -> Path | None:
    if raw_output:
        output = Path(raw_output).resolve()
        if output_format and export_format_from_path(output) != output_format:
            return _with_export_format(output, output_format)
        return output
    if not output_format:
        return None
    output_dir = Path(__file__).resolve().parents[1] / "output"
    if output_format == "image_sequence":
        return output_dir / "frames" / "frame_%05d.png"
    return output_dir / f"final_video.{output_format}"


def _with_export_format(path: Path, output_format: str) -> Path:
    if output_format == "image_sequence":
        if "%" in path.name:
            return path
        return path.parent / f"{path.stem}_%05d.png"
    extension = ".jpg" if output_format == "image_sequence" else f".{output_format}"
    return path.with_suffix(extension)


def _cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.project_json).resolve()
    try:
        data = _read_json(path)
        validate_project(data)
    except ProjectValidationError as exc:
        print(exc)
        return 1
    print(f"Valid project JSON: {path}")
    return 0


def _cmd_preview(args: argparse.Namespace) -> int:
    project_path = Path(args.project_json).resolve()
    if args.repair:
        repaired_path = _default_repaired_path(project_path)
        result = repair_project_file(project_path, repaired_path)
        _print_repair_result(result, repaired_path)
        if not result.valid:
            return 1
        project_path = repaired_path
    project = ProjectParser().load(project_path)
    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    result = generate_preview(project, output_dir=output_dir, generate_placeholders=args.generate_placeholders)
    print(f"Timeline summary: {result.summary_path}")
    print(f"Render plan: {result.plan_path}")
    if result.summary["missingAssets"]:
        print(f"Missing assets: {len(result.summary['missingAssets'])}")
        return 1
    return 0


def _cmd_quick_create(args: argparse.Namespace) -> int:
    recording = Path(args.recording).resolve()
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{recording.stem}.mvp_0_1.json")
    create_quick_project(
        recording,
        music=Path(args.music).resolve() if args.music else None,
        logo=Path(args.logo).resolve() if args.logo else None,
        title=args.title,
        caption=args.caption,
        instructions=args.instructions,
        style=args.style,
        duration=args.duration,
        width=args.width,
        height=args.height,
        fps=args.fps,
        output_path=output,
    )
    print(f"MVP 0.1 project JSON: {output}")
    if args.render:
        project = ProjectParser().load(output)
        render_output = Path(args.render_output).resolve() if args.render_output else output.with_suffix(".mp4")
        renderer = VideoRenderer(
            project,
            output_path=render_output,
            quality=args.quality,
            use_cache=args.cache,
            resume=args.cache,
        )
        final_path = renderer.render()
        print(f"MVP 0.1 rendered MP4: {final_path}")
    return 0


def _cmd_foundation_pass(args: argparse.Namespace) -> int:
    project_path = Path(args.project_json).resolve()
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{project_path.stem}.foundation.json")
    report_output = Path(args.report).resolve() if args.report else output.with_suffix(".foundation_report.json")
    result = run_foundation_pass(
        project_path,
        output_path=output,
        report_path=report_output,
        metadata_dir=Path(args.metadata_dir).resolve() if args.metadata_dir else None,
        cache_dir=Path(args.cache_dir).resolve() if args.cache_dir else None,
        generate_proxies=args.generate_proxies,
        run_benchmark=args.benchmark,
    )
    print(f"Foundation project: {result['outputPath']}")
    print(f"Foundation report: {result['reportPath']}")
    systems = result["report"]["systems"]
    print(
        "Foundation systems: "
        f"{len(systems)} | "
        f"timelineFrames={systems['frameAccurateTimeline']['summary']['totalFrames']} | "
        f"safetyScore={systems['accessibilitySafety']['summary']['score']} | "
        f"proxies={systems['proxyMedia']['summary']['proxyCount']}"
    )
    return 0


def _cmd_repair(args: argparse.Namespace) -> int:
    path = Path(args.project_json).resolve()
    output_path = None
    if args.output:
        output_path = Path(args.output).resolve()
    elif not args.in_place:
        output_path = _default_repaired_path(path)
    result = repair_project_file(path, output_path, in_place=args.in_place)
    target = path if args.in_place else output_path
    _print_repair_result(result, target)
    return 0 if result.valid else 1


def _cmd_template(args: argparse.Namespace) -> int:
    if args.template_command == "list":
        for template in list_templates():
            assets = ", ".join(f"{key}:{kind}" for key, kind in template["requiredAssets"].items())
            print(f"{template['key']} - {template['name']} | preset={template['exportPreset']} | assets={assets}")
        return 0

    project = create_project_from_template(args.name, preset=args.preset)
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{args.name}.json")
    _write_json(output, project)
    print(f"Template project created: {output}")
    if args.generate_placeholders:
        _generate_placeholders_for_project(output)
    return 0


def _cmd_ai_generate(args: argparse.Namespace) -> int:
    project = generate_project_from_prompt(args.prompt, template=args.template, preset=args.preset)
    slug = _slug(args.prompt)[:48] or "ai_project"
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{slug}.json")
    _write_json(output, project)
    print(f"AI-generated project JSON: {output}")
    if args.generate_placeholders:
        _generate_placeholders_for_project(output)
    return 0


def _cmd_preset(args: argparse.Namespace) -> int:
    for preset in list_export_presets():
        print(f"{preset.key} - {preset.label} | {preset.container}/{preset.video_codec}+{preset.audio_codec} | crf={preset.crf} | {preset.description}")
    return 0


def _cmd_analyze_audio(args: argparse.Namespace) -> int:
    audio = Path(args.audio).resolve()
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{audio.stem}.beat_analysis.json")
    analysis = analyze_audio(audio, output_path=output)
    print(f"Audio analysis: {output}")
    print(f"BPM: {analysis.get('bpm')} | beats={len(analysis.get('beats', []))} | bassDrops={len(analysis.get('bassDrops', []))}")
    return 0


def _cmd_beat_sync(args: argparse.Namespace) -> int:
    path = Path(args.project_json).resolve()
    data = _read_json(path)
    audio_path = Path(args.audio).resolve() if args.audio else _resolve_audio_asset_path(path, data, args.asset)
    analysis = analyze_audio(audio_path)
    synced = apply_beat_sync(data, analysis)
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{path.stem}.beat_sync.json")
    _relocate_assets_for_output(synced, path, output)
    _write_json(output, synced)
    print(f"Beat-synced project: {output}")
    print(f"BPM: {analysis.get('bpm')} | beats={len(analysis.get('beats', []))} | bassDrops={len(analysis.get('bassDrops', []))}")
    return 0


def _cmd_auto_select(args: argparse.Namespace) -> int:
    folder = Path(args.clips_folder).resolve()
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{folder.name}.clip_selection.json")
    result = select_highlights(folder, scene_duration=args.scene_duration, max_clips=args.max_clips, output_path=output)
    print(f"Clip selection report: {output}")
    print(f"Scanned={result['scannedClipCount']} selected={result['selectedClipCount']}")
    return 0 if result["selectedClipCount"] else 1


def _cmd_smart_build(args: argparse.Namespace) -> int:
    project = build_smart_project(
        Path(args.clips_folder).resolve(),
        Path(args.music).resolve(),
        duration=args.duration,
        scene_duration=args.scene_duration,
        style=args.style,
        preset=args.preset,
    )
    output = Path(args.output).resolve() if args.output else _default_generated_path("smart_build.json")
    _write_json(output, project)
    print(f"Smart-built project: {output}")
    if args.generate_placeholders:
        _generate_placeholders_for_project(output)
    return 0


def _cmd_pipeline(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_generated_path(f"pipeline_{_slug(args.prompt)[:34]}")
    result = run_project_pipeline(
        prompt=args.prompt,
        clips_folder=Path(args.clips_folder).resolve(),
        music_path=Path(args.music).resolve() if args.music else None,
        style=args.style,
        preset=args.preset,
        duration=args.duration,
        output_dir=output_dir,
        profile=args.profile,
        render=args.render,
        quality=args.quality,
    )
    print(f"Pipeline project: {result['projectPath']}")
    print(f"Storyboard: {result['storyboardPath']}")
    if result.get("renderPath"):
        print(f"Rendered video: {result['renderPath']}")
    print(f"Suggestions: {len(result.get('suggestions', []))} | elapsed={result['elapsedSeconds']}s")
    return 0


def _cmd_autonomous(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_generated_path(f"autonomous_{_slug(args.idea)[:34]}")
    result = run_autonomous_production_pipeline(
        idea=args.idea,
        output_dir=output_dir,
        assets_folder=Path(args.assets_folder).resolve() if args.assets_folder else None,
        music_path=Path(args.music).resolve() if args.music else None,
        logo_path=Path(args.logo).resolve() if args.logo else None,
        profile=args.profile,
        platform=args.platform,
        content_type=args.content_type,
        vibe=args.vibe,
        duration=args.duration,
        approved=args.approved,
        render_preview=args.render_preview,
        final_render=args.final_render,
        package=args.package,
        variants=args.variants,
        quality=args.quality,
        cache=args.cache,
        gpu=args.gpu,
    )
    print(f"Autonomous project: {result['projectPath']}")
    print(f"Review summary: {result['reviewSummaryPath']}")
    print(f"Autonomous plan: {result['autonomousPlanPath']}")
    print(f"Explainability: {result['explainabilityTextPath']}")
    print(f"Readiness score: {result['qualityReview']['readinessScore']}/100")
    if result.get("previewVideo"):
        print(f"Preview video: {result['previewVideo']}")
    if result.get("finalVideo"):
        print(f"Final video: {result['finalVideo']}")
    if result.get("postingPackagePath"):
        print(f"Posting package: {result['postingPackagePath']}")
    if result.get("finalRenderBlocked"):
        print("Final render blocked: rerun with --approved after review.")
    if result.get("warnings"):
        print("Warnings:")
        for warning in result["warnings"]:
            print(f"- {warning}")
    print(f"Elapsed: {result['elapsedSeconds']}s")
    return 0


def _cmd_youtube_short(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_generated_path(f"youtube_short_{_slug(args.prompt)[:34]}")
    result = run_youtube_shorts_auto(
        prompt=args.prompt,
        output_dir=output_dir,
        assets_folder=Path(args.assets_folder).resolve() if args.assets_folder else None,
        music_path=Path(args.music).resolve() if args.music else None,
        logo_path=Path(args.logo).resolve() if args.logo else None,
        style=args.style,
        duration=args.duration,
        render=args.render,
        quality=args.quality,
        cache=args.cache,
        gpu=args.gpu,
    )
    print(f"YouTube Short project: {result['projectPath']}")
    print(f"Plan: {result['planPath']}")
    print(f"Review summary: {result['reviewSummaryPath']}")
    print(f"Hook: {result['hook']}")
    print(f"Style: {result['style']} | duration={result['duration']}s")
    if result.get("renderPath"):
        print(f"Rendered video: {result['renderPath']}")
    if result.get("warnings"):
        print("Warnings:")
        for warning in result["warnings"]:
            print(f"- {warning}")
    return 0


def _cmd_content_generate(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_generated_path(f"content_{args.mode}_{_slug(args.idea)[:28]}")
    try:
        result = run_content_generator(
            idea=args.idea,
            output_dir=output_dir,
            mode=args.mode,
            product_name=args.product_name,
            target_platform=args.platform,
            goal=args.goal,
            bullet_points=list(args.bullet or []),
            assets_folder=Path(args.assets_folder).resolve() if args.assets_folder else None,
            music_path=Path(args.music).resolve() if args.music else None,
            logo_path=Path(args.logo).resolve() if args.logo else None,
            duration=args.duration,
            tone=args.tone,
            style=args.style,
            existing_plan_path=Path(args.existing_plan).resolve() if args.existing_plan else None,
            regenerate=args.regenerate,
            locks=list(args.lock or []),
            approved=args.approved,
            render=args.render,
            quality=args.quality,
            cache=args.cache,
            gpu=args.gpu,
        )
    except RuntimeError as exc:
        print(f"Content generation blocked: {exc}", file=sys.stderr)
        return 2
    print(f"Content project: {result['projectPath']}")
    print(f"Review summary: {result['reviewSummaryPath']}")
    print(f"Generation review: {result['generationReviewPath']}")
    print(f"AI reasoning: {result['aiReasoningPath']}")
    print(f"Scene plan: {result['scenePlanPath']}")
    print(f"Hook: {result['hook']}")
    print(f"Mode: {result['mode']} | style={result['style']} | duration={result['duration']}s")
    print(f"Approved for final render: {result['approvalReady']}")
    if result.get("versionComparisonPath"):
        print(f"Version comparison: {result['versionComparisonPath']}")
    if result.get("renderPath"):
        print(f"Rendered video: {result['renderPath']}")
    if result.get("warnings"):
        print("Warnings:")
        for warning in result["warnings"]:
            print(f"- {warning}")
    return 0


def _cmd_auto_template(args: argparse.Namespace) -> int:
    if args.auto_template_command == "list":
        catalog = beginner_template_catalog()
        if args.json:
            print(json.dumps({"templates": catalog}, indent=2))
            return 0
        for item in catalog:
            print(f"{item['key']}: {item['name']} ({item['aspect_ratio']}, {item['export_settings']['preset']})")
        return 0

    output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_generated_path(f"beginner_{args.template}_{_slug(args.product_name)[:24]}")
    try:
        result = run_beginner_auto_template(
            output_dir=output_dir,
            template=args.template,
            media_file=Path(args.media).resolve() if args.media else None,
            image_folder=Path(args.images).resolve() if args.images else None,
            asset_folder=Path(args.assets).resolve() if args.assets else None,
            music_path=Path(args.music).resolve() if args.music else None,
            logo_path=Path(args.logo).resolve() if args.logo else None,
            target_platform=args.platform,
            product_name=args.product_name,
            video_goal=args.goal,
            key_features=list(args.feature or []),
            desired_vibe=args.vibe,
            duration=args.duration,
            render=args.render,
            quality=args.quality,
            cache=args.cache,
            gpu=args.gpu,
        )
    except (RuntimeError, KeyError, ProjectValidationError) as exc:
        print(f"Beginner auto-template failed: {exc}", file=sys.stderr)
        return 2
    beginner = result.get("beginnerSummary", {})
    template = beginner.get("template", {})
    outputs = beginner.get("outputs", {})
    print(f"Beginner auto video: {template.get('name', args.template)}")
    print(f"Project JSON: {outputs.get('projectJson') or result.get('projectPath')}")
    print(f"Review summary: {outputs.get('reviewSummary') or result.get('reviewSummaryPath')}")
    print(f"Script: {outputs.get('script') or result.get('scriptPath')}")
    print(f"Scene plan: {outputs.get('scenePlan') or result.get('scenePlanPath')}")
    print(f"Beginner summary: {result.get('beginnerSummaryPath')}")
    print(f"Hook: {result.get('hook')}")
    print(f"Style: {result.get('style')} | duration={result.get('duration')}s")
    if outputs.get("renderedVideo") or result.get("renderPath"):
        print(f"Rendered video: {outputs.get('renderedVideo') or result.get('renderPath')}")
    warnings = beginner.get("warnings") or result.get("warnings") or []
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
    return 0


def _cmd_media(args: argparse.Namespace) -> int:
    if args.media_command == "formats":
        from dataclasses import asdict
        from media.compat import AUDIO_EXTENSIONS, EXPORT_FORMATS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS

        payload = {
            "videoImport": sorted(VIDEO_EXTENSIONS),
            "imageImport": sorted(IMAGE_EXTENSIONS),
            "audioImport": sorted(AUDIO_EXTENSIONS),
            "exportFormats": EXPORT_FORMATS,
            "exportPresets": [asdict(preset) for preset in list_export_presets()],
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print("Video import: " + ", ".join(payload["videoImport"]))
            print("Image import: " + ", ".join(payload["imageImport"]))
            print("Audio import: " + ", ".join(payload["audioImport"]))
            print("Export formats: " + ", ".join(sorted(payload["exportFormats"])))
            print("Export presets: " + ", ".join(preset["key"] for preset in payload["exportPresets"]))
        return 0

    if args.media_command == "inspect":
        path = Path(args.file).resolve()
        result = analyze_media(path)
        if args.output:
            output = Path(args.output).resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(f"Media metadata: {output}")
        else:
            print(json.dumps(result, indent=2))
        return 1 if result.get("broken") else 0

    project_dir = Path(args.project_dir).resolve() if args.project_dir else Path.cwd().resolve()
    output = Path(args.output).resolve() if args.output else None
    result = import_media_files(
        [Path(file).resolve() for file in args.files],
        project_dir=project_dir,
        normalize=args.normalize,
        generate_proxy=not args.no_proxy,
        generate_thumbnail=not args.no_thumbnails,
        generate_waveform=not args.no_waveforms,
        target_fps=args.fps,
        sample_rate=args.sample_rate,
        output_path=output,
    )
    print(f"Imported media: {len(result['imported'])}")
    print(f"Report: {result['reportPath']}")
    for item in result["imported"]:
        marker = "normalized" if item.get("normalized") else "copied"
        print(f"- {item['assetKey']} [{item['type']}, {marker}] -> {item.get('projectPath')}")
    if result.get("warnings"):
        print("Warnings:")
        for warning in result["warnings"]:
            print(f"- {warning}")
    return 0


def _cmd_content_review(args: argparse.Namespace) -> int:
    if args.content_review_command == "show":
        plan_path = Path(args.plan).resolve()
        plan = load_plan(plan_path)
        project = _content_review_project(plan_path)
        review = plan.get("approval") or build_generation_review(plan, project)
        output_dir = Path(args.output_dir).resolve() if args.output_dir else plan_path.parent
        paths = write_review_outputs(output_dir, {**plan, "approval": review}, project)
        summary = review.get("summary", {})
        readiness = review.get("readiness", {})
        print(f"Generation review: {paths['generation_review']}")
        print(f"Approval state: {paths['approval_state']}")
        print(f"Hook: {summary.get('hook', '')}")
        print(f"Style: {summary.get('stylePreset', '')} | duration={summary.get('estimatedDuration', 0)}s")
        print(f"Ready for final render: {readiness.get('readyForFinalRender', False)}")
        if readiness.get("unresolvedSections"):
            print("Unresolved sections:")
            for section in readiness["unresolvedSections"][:12]:
                print(f"- {section}")
        return 0

    if args.content_review_command == "approve":
        plan_path = Path(args.plan).resolve()
        output_path = Path(args.output).resolve() if args.output else plan_path
        plan = load_plan(plan_path)
        project = _content_review_project(plan_path)
        review = plan.get("approval") or build_generation_review(plan, project)
        review = set_review_status(review, args.section, args.status)
        plan["approval"] = review
        save_plan(output_path, plan)
        paths = write_review_outputs(output_path.parent, plan, project)
        print(f"Updated plan: {output_path}")
        print(f"Approval state: {paths['approval_state']}")
        print(f"Section: {args.section} -> {args.status}")
        print(f"Ready for final render: {review.get('readiness', {}).get('readyForFinalRender', False)}")
        return 0

    if args.content_review_command == "compare":
        old_plan_path = Path(args.old_plan).resolve()
        new_plan_path = Path(args.new_plan).resolve()
        old_project = _read_json(Path(args.old_project).resolve()) if args.old_project else None
        new_project = _read_json(Path(args.new_project).resolve()) if args.new_project else None
        comparison = compare_content_versions(
            load_plan(old_plan_path),
            load_plan(new_plan_path),
            previous_project=old_project,
            next_project=new_project,
            previous_render=args.old_render,
            next_render=args.new_render,
        )
        output_dir = Path(args.output_dir).resolve() if args.output_dir else new_plan_path.parent / "comparison"
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "version_comparison.json"
        text_path = output_dir / "version_comparison.md"
        _write_json(json_path, comparison)
        text_path.write_text(comparison_markdown(comparison), encoding="utf-8")
        print(f"Version comparison: {json_path}")
        print(f"Readable comparison: {text_path}")
        print(f"Script changed: {comparison['summary']['scriptLinesChanged']}")
        print(f"Scene plan changed: {comparison['summary']['scenePlanChanged']}")
        print(f"Style changed: {comparison['summary']['styleChanged']}")
        return 0

    raise ValueError(f"Unknown content review command: {args.content_review_command}")


def _cmd_post_package(args: argparse.Namespace) -> int:
    project_path = Path(args.project_json).resolve()
    video_path = Path(args.video).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else Path(__file__).resolve().parents[1] / "exports" / _slug(project_path.stem)
    summary = create_posting_package(
        project_path,
        video_path,
        output_dir=output_dir,
        platforms=list(args.platforms or ["all"]),
        title=args.title,
        accent_color=args.accent,
        render_report_path=Path(args.render_report).resolve() if args.render_report else None,
        render_logs_path=Path(args.render_logs).resolve() if args.render_logs else None,
    )
    print(f"Posting package: {summary['outputDir']}")
    print(f"Video: {summary['video']}")
    for package in summary["platforms"]:
        status = "ready" if package["ready"] else "review"
        print(f"- {package['platform']}: {status} | {package['folder']}")
    root_validation = summary.get("rootPackage", {}).get("validation", {})
    root_status = "ready" if root_validation.get("ready") else "review"
    print(f"Upload package: {root_status} | {summary['rootPackage']['folder']}")
    print(f"Archive: {summary['archive']['folder']}")
    return 0


def _cmd_post_export(args: argparse.Namespace) -> int:
    if args.post_export_command == "review":
        output = Path(args.output).resolve() if args.output else _default_generated_path(f"{Path(args.project_json).stem}.post_export_review.json")
        report = review_export(
            Path(args.project_json).resolve(),
            Path(args.video).resolve(),
            package_dir=Path(args.package_dir).resolve() if args.package_dir else None,
            output_path=output,
        )
        print(f"Post-export review: {output}")
        print(f"Playable={report['playbackReview']['playable']} issues={report['issueCount']} readyForReuse={report['readyForReuse']}")
        return 0 if not any(issue["severity"] == "error" for issue in report["issues"]) else 1
    if args.post_export_command == "reexport":
        output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_generated_path(f"{Path(args.project_json).stem}_quick_reexport")
        report = create_quick_reexport_project(
            Path(args.project_json).resolve(),
            output_dir=output_dir,
            preset=args.preset,
            format_name=args.format,
            mode=args.mode,
            captions=args.captions,
            thumbnail=args.thumbnail,
        )
        print(f"Quick re-export project: {report['outputProject']}")
        print(f"Preset={report['preset']} format={report['format']} captions={report['captions']}")
        return 0
    if args.post_export_command == "template":
        output = Path(args.output).resolve() if args.output else Path(__file__).resolve().parents[1] / "templates" / "reusable" / f"{_slug(args.name)}.reuse-template.json"
        template = save_reusable_template(
            Path(args.project_json).resolve(),
            output_path=output,
            name=args.name,
            video_path=Path(args.video).resolve() if args.video else None,
            note=args.note,
        )
        print(f"Reusable template: {template['path']}")
        print(f"Name={template['name']} scenes={template['pacing']['sceneCount']}")
        return 0
    if args.post_export_command == "variants":
        output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_generated_path(f"{Path(args.project_json).stem}_post_export_variants")
        summary = create_post_export_variants(
            Path(args.project_json).resolve(),
            output_dir=output_dir,
            variants=args.variant or None,
            hook=args.hook,
            cta=args.cta,
        )
        print(f"Post-export variants: {summary['outputDir']}")
        print(f"Variants={len(summary['outputs'])}")
        return 0
    if args.post_export_command == "note":
        note = record_success_note(
            Path(args.project_json).resolve(),
            video_path=Path(args.video).resolve() if args.video else None,
            profile=args.profile,
            tags=args.tag,
            note=args.note,
            output_path=Path(args.output).resolve() if args.output else None,
        )
        print(f"Success note: {note['path']}")
        print(f"Profile={note['profile']} tags={', '.join(note['tags']) or 'none'}")
        return 0
    raise ValueError(f"Unknown post-export command: {args.post_export_command}")


def _cmd_repurpose(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_generated_path(f"{Path(args.project_json).stem}_repurposed")
    summary = repurpose_project(
        Path(args.project_json).resolve(),
        output_dir=output_dir,
        platforms=list(args.platforms or ["all"]),
        hook_variants=list(args.hook or []),
        cta_variants=list(args.cta or []),
        reuse_style=not args.no_reuse_style,
        render=args.render,
        quality=args.quality,
        package=args.package,
        generate_placeholders=args.generate_placeholders,
        max_variants=args.max_variants,
    )
    print(f"Repurpose summary: {output_dir / 'repurpose_summary.json'}")
    print(f"Variants={summary['count']} platforms={', '.join(summary['platforms'])} rendered={summary['rendered']} packaged={summary['packaged']}")
    return 0


def _cmd_batch(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_generated_path(f"batch_{_slug(args.prompt)[:34]}")
    result = run_batch_generation(
        prompt=args.prompt,
        clips_folder=Path(args.clips_folder).resolve(),
        music_path=Path(args.music).resolve() if args.music else None,
        styles=list(args.styles),
        presets=list(args.presets),
        versions=args.versions,
        output_dir=output_dir,
        render=args.render,
        quality=args.quality,
    )
    print(f"Batch summary: {output_dir / 'batch_summary.json'}")
    print(f"Generated edits: {result['count']}")
    return 0


def _cmd_highlight_detect(args: argparse.Namespace) -> int:
    folder = Path(args.clips_folder).resolve()
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{folder.name}.highlight_detection.json")
    result = select_highlights(folder, scene_duration=args.scene_duration, max_clips=args.max_clips, output_path=output)
    print(f"Highlight detection report: {output}")
    print(f"Scanned={result['scannedClipCount']} selected={result['selectedClipCount']}")
    for clip in result["selected"][:5]:
        print(f"- {Path(clip['path']).name}: score={clip.get('highlightScore')} tags={','.join(clip.get('tags', []))}")
    return 0 if result["scannedClipCount"] else 1


def _cmd_thumbnail(args: argparse.Namespace) -> int:
    video = Path(args.video).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_generated_path(f"{video.stem}.thumbnails")
    result = generate_thumbnail_set(video, title=args.title, output_dir=output_dir, accent_color=args.accent)
    print(f"Thumbnail report: {result['reportPath']}")
    print(f"Generated thumbnails: {len(result['thumbnails'])}")
    return 0


def _cmd_suggest(args: argparse.Namespace) -> int:
    path = Path(args.project_json).resolve()
    project = _read_json(path)
    result = suggest_scene_improvements(project)
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{path.stem}.suggestions.json")
    _write_json(output, result)
    print(f"Suggestions report: {output}")
    for item in result["suggestions"][:8]:
        print(f"- [{item['severity']}] {item['target']}: {item['message']}")
    return 0


def _cmd_captions(args: argparse.Namespace) -> int:
    path = Path(args.project_json).resolve()
    data = _read_json(path)
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{path.stem}.captions.json")
    add_captions_from_transcript(data, Path(args.transcript).resolve(), mode=args.mode, style=args.style)
    _relocate_assets_for_output(data, path, output)
    _write_json(output, data)
    print(f"Captioned project: {output}")
    return 0


def _cmd_style(args: argparse.Namespace) -> int:
    if args.style_command == "list":
        for name in list_styles():
            print(name)
        return 0
    path = Path(args.project_json).resolve()
    styled = apply_style(_read_json(path), args.style)
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{path.stem}.{args.style}.json")
    _relocate_assets_for_output(styled, path, output)
    _write_json(output, styled)
    print(f"Styled project: {output}")
    return 0


def _cmd_director(args: argparse.Namespace) -> int:
    path = Path(args.project_json).resolve()
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{path.stem}.director.json")
    result = run_ai_director(
        path,
        args.goal,
        output_path=output,
        preserve_scene_ids=list(args.preserve or []),
        save_history=not args.no_history,
    )
    print(f"AI Director project: {output}")
    print(f"Director report: {output.with_suffix('.director_report.json')}")
    if result.history:
        print(f"History version: {result.history['id']}")
    print(result.report["summary"])
    return 0


def _cmd_storyboard(args: argparse.Namespace) -> int:
    project = ProjectParser().load(Path(args.project_json).resolve())
    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    result = generate_storyboard(project, output_dir=output_dir)
    print(f"Storyboard JSON: {result['storyboardPath']}")
    print(f"Storyboard text: {result['textPath']}")
    print(f"Scenes: {len(result['scenes'])}")
    return 0


def _cmd_asset_analyze(args: argparse.Namespace) -> int:
    path = Path(args.path).resolve()
    data = _read_json(path) if path.is_file() and path.suffix.lower() == ".json" else None
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{path.stem}.asset_report.json")
    result = analyze_asset_library(path, project_data=data, output_path=output)
    print(f"Asset intelligence report: {output}")
    print(f"Assets: {result['assetCount']} | issues: {len(result['issues'])}")
    return 0 if not any(issue.get("severity") == "error" for issue in result["issues"]) else 1


def _cmd_resolve_broll(args: argparse.Namespace) -> int:
    path = Path(args.project_json).resolve()
    data = resolve_broll_layers(_read_json(path), path.parent)
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{path.stem}.broll.json")
    _relocate_assets_for_output(data, path, output)
    _write_json(output, data)
    print(f"B-roll resolved project: {output}")
    return 0


def _cmd_history(args: argparse.Namespace) -> int:
    path = Path(args.project_json).resolve()
    if args.history_command == "list":
        versions = list_versions(path)
        if not versions:
            print("No AI edit history found.")
            return 0
        for version in versions:
            print(f"{version['id']} | {version.get('timestamp')} | {version.get('summary')}")
        return 0
    output = Path(args.output).resolve() if args.output else None
    target = rollback_version(path, args.version_id, output_path=output)
    print(f"Rolled back project written to: {target}")
    return 0


def _cmd_package(args: argparse.Namespace) -> int:
    if args.package_command == "export":
        path = Path(args.project_json).resolve()
        output = Path(args.output).resolve() if args.output else _default_generated_path(f"{path.stem}.project.zip")
        manifest = export_project_package(path, output)
        print(f"Project package: {output}")
        print(f"Assets included: {len(manifest['assets'])}")
        return 0
    package_path = Path(args.package_zip).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_generated_path(package_path.stem)
    manifest = open_project_package(package_path, output_dir)
    print(f"Package opened to: {manifest['openedTo']}")
    print(f"Project JSON: {manifest['projectPath']}")
    return 0


def _cmd_plugin(args: argparse.Namespace) -> int:
    if args.plugin_command == "list":
        plugins = list_plugins()
        if not plugins:
            print("No plugins installed.")
            return 0
        for plugin in plugins:
            print(f"{plugin.get('id')} | {plugin.get('type')} | {plugin.get('name')} | {plugin.get('path')}")
        return 0
    if args.plugin_command == "audit":
        report = audit_plugins()
        print(json.dumps(report, indent=2))
        return 0 if not any(item.get("severity") == "error" for item in report["warnings"]) else 1
    if args.plugin_command in {"disable", "enable"}:
        enabled = args.plugin_command == "enable"
        plugin = set_plugin_enabled(args.plugin_id, enabled)
        print(f"Plugin {plugin['id']} {'enabled' if enabled else 'disabled'}: {plugin['path']}")
        return 0
    plugin = init_plugin(args.name, args.type)
    print(f"Plugin created: {plugin['path']}")
    return 0


def _cmd_realtime_preview(args: argparse.Namespace) -> int:
    project = ProjectParser().load(Path(args.project_json).resolve())
    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    result = generate_realtime_preview(project, timestamp=args.time, scene_id=args.scene, output_dir=output_dir, quality_mode=args.mode, layer_mode=args.layers)
    print(f"Realtime preview frame: {result['frame']}")
    print(f"Preview report: {result['reportPath']}")
    return 0


def _cmd_interactive_preview(args: argparse.Namespace) -> int:
    project = ProjectParser().load(Path(args.project_json).resolve())
    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    result = generate_interactive_preview(
        project,
        output_dir=output_dir,
        quality_mode=args.quality_mode,
        scope=args.scope,
        scene_id=args.scene_id,
        generate_placeholders=args.generate_placeholders,
    )
    print(f"Interactive preview video: {result['previewVideo']}")
    print(f"Timeline summary: {result['timelineSummaryPath']}")
    if result.get("waveformPath"):
        print(f"Waveform preview: {result['waveformPath']}")
    print(f"Preview report: {result['reportPath']}")
    return 0


def _cmd_template_pack(args: argparse.Namespace) -> int:
    if args.template_pack_command == "list":
        for item in template_pack_catalog():
            print(f"{item['key']} | {item['name']} | author={item['author']} | tags={','.join(item['tags'])}")
        return 0
    if args.template_pack_command == "export":
        output = Path(args.output).resolve() if args.output else _default_generated_path(f"{args.template}.template-pack.zip")
        result = export_template_pack(args.template, output)
        print(f"Template pack exported: {result['path']}")
        return 0
    install_dir = Path(args.output_dir).resolve() if args.output_dir else None
    result = install_template_pack(Path(args.package_zip).resolve(), install_dir)
    print(f"Template pack installed: {result['installedTo']}")
    return 0


def _cmd_brand(args: argparse.Namespace) -> int:
    if args.brand_command == "init":
        output = Path(args.output).resolve() if args.output else _default_generated_path("brand_kit.json")
        create_brand_kit(output)
        print(f"Brand kit created: {output}")
        return 0
    project_path = Path(args.project_json).resolve()
    brand_kit = _read_json(Path(args.brand_kit).resolve())
    branded = apply_brand_kit(_read_json(project_path), brand_kit)
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{project_path.stem}.branded.json")
    _relocate_assets_for_output(branded, project_path, output)
    _write_json(output, branded)
    print(f"Branded project: {output}")
    return 0


def _cmd_manifest(args: argparse.Namespace) -> int:
    project_path = Path(args.project_json).resolve()
    if args.check_only:
        result = check_portability(project_path)
        print(json.dumps(result, indent=2))
        return 0 if result["portable"] and result["versionCompatible"] else 1
    output = Path(args.output).resolve() if args.output else None
    result = generate_project_manifest(project_path, output_path=output)
    print(f"Project manifest: {result['manifestPath']}")
    print(f"Portable: {result['checks']['portable']} | assets={result['assetCount']}")
    return 0 if result["checks"]["versionCompatible"] else 1


def _cmd_quality_check(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{Path(args.project_json).stem}.quality_report.json")
    result = run_quality_check(Path(args.project_json).resolve(), output_path=output)
    print(f"Quality report: {output}")
    print(f"Passed: {result['passed']} | issues={result['issueCount']}")
    return 0 if result["passed"] else 1


def _cmd_final_preflight(args: argparse.Namespace) -> int:
    project_path = Path(args.project_json).resolve()
    preview_video = Path(args.preview_video).resolve() if args.preview_video else None
    if args.preflight_command == "check":
        output = Path(args.output).resolve() if args.output else _default_generated_path(f"{project_path.stem}.final_preflight.json")
        result = run_final_preflight(project_path, preview_video=preview_video, output_path=output, export_format=args.format)
        print(f"Final preflight report: {output}")
        print(f"Ready: {result['ready']} | score={result['exportReadinessScore']} | issues={result['issueCount']} | blocking={result['blockingCount']}")
        return 0 if result["ready"] else 1

    output = Path(args.output).resolve()
    result = repair_final_preflight(
        project_path,
        output_path=output,
        issue_id=args.issue_id,
        mode=args.mode,
        preview_video=preview_video,
        export_format=args.format,
    )
    after = result["reportAfter"]
    print(f"Preflight repair output: {result['output']}")
    print(f"Applied fixes: {len(result['applied'])} | ready={after['ready']} | score={after['exportReadinessScore']}")
    return 0 if after["ready"] else 1


def _cmd_reformat(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_generated_path("social_reformats")
    result = reformat_project(Path(args.project_json).resolve(), list(args.targets), output_dir)
    print(f"Social reformat output dir: {output_dir}")
    for item in result["outputs"]:
        print(f"- {item['target']}: {item['path']}")
    return 0


def _cmd_recovery(args: argparse.Namespace) -> int:
    if args.recovery_command == "autosave":
        path = Path(args.project_json).resolve()
        result = autosave_project(path, path.read_text(encoding="utf-8"))
        print(f"Autosave: {result['path']}")
        return 0
    if args.recovery_command == "backup":
        result = backup_project(Path(args.project_json).resolve())
        print(f"Backup: {result['path']}")
        return 0
    if args.recovery_command == "restore-point":
        result = create_restore_point(Path(args.project_json).resolve(), label=args.label)
        print(f"Restore point: {result['path']} | label={result['label']}")
        return 0
    if args.recovery_command == "cleanup":
        result = cleanup_recovery_points(Path(args.project_json).resolve(), keep=args.keep)
        print(f"Recovery cleanup deleted {result['deletedCount']} files.")
        return 0
    if args.recovery_command == "recover-corrupt":
        output = Path(args.output).resolve() if args.output else None
        result = recover_corrupted_project(Path(args.project_json).resolve(), output_path=output)
        print(f"Recovery strategy: {result['strategy']} | output={result['output']} | valid={result['valid']}")
        return 0 if result["valid"] else 1
    if args.recovery_command == "integrity":
        output = Path(args.output).resolve() if args.output else _default_generated_path(f"{Path(args.project_json).stem}.integrity_report.json")
        result = check_project_integrity(Path(args.project_json).resolve(), output_path=output)
        print(f"Integrity report: {output} | valid={result['valid']} issues={result['issueCount']} missingAssets={result['missingAssetCount']}")
        return 0 if result["valid"] else 1
    if args.recovery_command == "relink":
        output = Path(args.output).resolve() if args.output else None
        result = relink_missing_assets(Path(args.project_json).resolve(), Path(args.search_folder).resolve(), output_path=output)
        print(f"Relinked project: {result['output']} | relinked={result['relinkedCount']}")
        return 0
    if args.recovery_command == "list":
        for point in list_recovery_points(Path(args.project_json).resolve()):
            print(f"{point['type']} | {point['timestamp']} | {point['path']}")
        return 0
    result = restore_recovery_point(Path(args.source).resolve(), Path(args.target).resolve())
    print(f"Restored: {result['target']}")
    return 0


def _cmd_profile(args: argparse.Namespace) -> int:
    if args.profile_command == "list":
        profiles = list_profiles()
        if not profiles:
            print("No creator profiles saved.")
            return 0
        for profile in profiles:
            print(f"{profile.get('name')} | {profile.get('path')}")
        return 0
    if args.profile_command == "create":
        output = Path(args.output).resolve() if args.output else None
        profile = create_profile(args.name, output_path=output)
        print(f"Creator profile: {profile['path']}")
        return 0
    if args.profile_command == "apply":
        path = Path(args.project_json).resolve()
        profile = load_profile(args.name_or_path)
        updated = apply_profile_to_project(_read_json(path), profile)
        output = Path(args.output).resolve() if args.output else _default_generated_path(f"{path.stem}.{_slug(profile.get('name', 'profile'))}.json")
        _relocate_assets_for_output(updated, path, output)
        validate_project(updated)
        _write_json(output, updated)
        print(f"Profile-applied project: {output}")
        return 0
    profile = load_profile(args.name_or_path)
    print(json.dumps(profile, indent=2))
    return 0


def _cmd_automation(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_generated_path(f"automation_{args.automation_command}")
    if args.automation_command == "queue":
        report = process_queue_folder(Path(args.queue_dir).resolve(), output_dir=output_dir, quality=args.quality)
        print(f"Queue report: {output_dir / 'queue_report.json'}")
        print(f"Jobs: {report['jobCount']}")
        return 0 if all(job.get("ok") for job in report["jobs"]) else 1
    report = watch_project_folder(
        Path(args.watch_dir).resolve(),
        output_dir=output_dir,
        quality=args.quality,
        once=not args.loop,
        poll_seconds=args.poll,
    )
    print(f"Watch report: {output_dir / 'watch_report.json'}")
    print(f"Runs: {report['runCount']}")
    return 0 if all(run.get("ok") for run in report["runs"]) else 1


def _cmd_metrics(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve() if args.output else _default_generated_path("metrics_summary.json")
    summary = summarize_metrics(output_path=output)
    print(f"Metrics summary: {output}")
    print(f"Events: {summary['eventCount']} | renders={summary['renderCount']} | avgRender={summary['averageRenderSeconds']}s")
    return 0


def _cmd_cinematic_enhance(args: argparse.Namespace) -> int:
    path = Path(args.project_json).resolve()
    enhanced = apply_cinematic_enhancement(_read_json(path), args.preset)
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{path.stem}.{args.preset}.json")
    _relocate_assets_for_output(enhanced, path, output)
    validate_project(enhanced)
    _write_json(output, enhanced)
    print(f"Cinematic project: {output}")
    return 0


def _cmd_effect_graph(args: argparse.Namespace) -> int:
    for preset in list_effect_graph_presets():
        print(preset)
    return 0


def _cmd_understand_clip(args: argparse.Namespace) -> int:
    path = Path(args.path).resolve()
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{path.stem}.clip_understanding.json")
    result = understand_folder(path, output_path=output) if path.is_dir() else understand_clip(path, output_path=output)
    print(f"Clip understanding report: {output}")
    if path.is_dir():
        print(f"Clips: {result['clipCount']} | top highlights: {len(result['topHighlights'])}")
    else:
        scores = result.get("scores", {})
        print(f"Highlight={scores.get('highlightPotential')} action={scores.get('actionIntensity')} use={result.get('suggestedUse')}")
    return 0


def _cmd_audio_intel(args: argparse.Namespace) -> int:
    audio = Path(args.audio).resolve()
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{audio.stem}.audio_intelligence.json")
    result = analyze_audio_intelligence(audio, output_path=output)
    profile = result.get("mixProfile", {})
    print(f"Audio intelligence report: {output}")
    print(f"BPM={result.get('bpm')} beats={profile.get('beatCount')} drops={profile.get('bassDropCount')} recommendations={len(result.get('editRecommendations', []))}")
    return 0


def _cmd_scene_build(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{_slug(args.prompt)[:42] or 'scene_build'}.json")
    project = build_scene_prompt(
        args.prompt,
        duration=args.duration,
        preset=args.preset,
        style=args.style,
        output_path=output,
    )
    validate_project(project)
    print(f"Scene-built project: {output}")
    if args.render:
        parsed = ProjectParser().load(output)
        render_path = output.with_suffix(".mp4")
        VideoRenderer(parsed, output_path=render_path, quality=args.quality, use_cache=True, resume=True).render()
        print(f"Rendered video: {render_path}")
    return 0


def _cmd_project_analyze(args: argparse.Namespace) -> int:
    path = Path(args.project_json).resolve()
    rendered_video = Path(args.rendered_video).resolve() if args.rendered_video else None
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{path.stem}.project_analysis.json")
    report = analyze_project(path, rendered_video=rendered_video, output_path=output)
    print(f"Project analysis: {output}")
    print(f"Pacing={report['pacing']['score']} captionDensity={report['captions']['density']} transitionSpam={report['transitions']['spamRisk']} warnings={len(report['warnings'])}")
    return 0


def _cmd_workspace(args: argparse.Namespace) -> int:
    if args.workspace_command == "init":
        workspace = create_workspace(args.name, workspace_path=Path(args.output).resolve() if args.output else None)
        print(f"Workspace: {workspace['path']}")
        return 0
    if args.workspace_command == "list":
        rows = list_workspaces()
        if not rows:
            print("No workspaces saved.")
            return 0
        for row in rows:
            print(f"{row['name']} | projects={row['projectCount']} | {row['path']}")
        return 0
    if args.workspace_command == "show":
        print(json.dumps(describe_workspace(Path(args.workspace).resolve()), indent=2))
        return 0
    if args.workspace_command == "open":
        workspace = open_project(Path(args.workspace).resolve(), Path(args.project_json).resolve())
        print(f"Opened project. Workspace projects: {len(workspace.get('projects', []))}")
        return 0
    if args.workspace_command == "close":
        workspace = close_project(Path(args.workspace).resolve(), Path(args.project_json).resolve())
        print(f"Closed project. Workspace projects: {len(workspace.get('projects', []))}")
        return 0
    if args.workspace_command == "profile":
        workspace_path = Path(args.workspace).resolve()
        if args.add:
            settings = json.loads(Path(args.settings_json).resolve().read_text(encoding="utf-8")) if args.settings_json else None
            workspace = add_workspace_profile(workspace_path, args.add, settings=settings)
            print(f"Workspace profile saved: {args.add} | profiles={len(workspace.get('profiles', []))}")
            return 0
        profiles = list_workspace_profiles(workspace_path)
        if not profiles:
            print("No workspace profiles saved.")
            return 0
        for profile in profiles:
            print(f"{profile.get('name')} | {profile.get('settings', {}).get('preferredMode', 'unknown')}")
        return 0
    layout: dict[str, Any] | str = args.preset
    if args.layout_json:
        layout = json.loads(Path(args.layout_json).resolve().read_text(encoding="utf-8"))
    workspace = save_layout(Path(args.workspace).resolve(), layout)
    print(f"Saved layout '{workspace.get('layout', {}).get('name', 'custom')}' to {workspace['path']}")
    return 0


def _cmd_review(args: argparse.Namespace) -> int:
    if args.review_command == "compare":
        output = Path(args.output).resolve() if args.output else _default_generated_path("project_compare_report.json")
        report = compare_projects(Path(args.left_project_json).resolve(), Path(args.right_project_json).resolve(), output_path=output)
        print(f"Comparison report: {output} | changedScenes={report['summary']['changedSceneCount']} diffLines={report['summary']['lineDiffCount']}")
        return 0
    project = Path(args.project_json).resolve()
    if args.review_command == "show":
        print(json.dumps(load_review(project), indent=2))
        return 0
    if args.review_command == "comment":
        review = add_comment(project, scene_id=args.scene_id, body=args.body, author=args.author, timestamp=args.time)
        print(f"Review saved: {review['path']} | comments={len(review.get('comments', []))}")
        return 0
    if args.review_command == "marker":
        review = add_marker(project, scene_id=args.scene_id, marker_type=args.type, timestamp=args.time, note=args.note, author=args.author)
        print(f"Review saved: {review['path']} | markers={len(review.get('markers', []))}")
        return 0
    if args.review_command == "approve":
        review = set_scene_status(project, scene_id=args.scene_id, status=args.status)
        print(f"Scene {args.scene_id}: {review['sceneApprovals'][args.scene_id]['status']}")
        return 0
    if args.review_command == "lock-asset":
        review = lock_asset(project, asset=args.asset, owner=args.owner, reason=args.reason)
        print(f"Asset locked: {args.asset} | locks={len(review.get('assetLocks', {}))}")
        return 0
    if args.review_command == "role":
        review = set_role(project, user=args.user, role=args.role)
        print(f"Role set: {args.user}={review['roles'][args.user]['role']}")
        return 0
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{project.stem}.review_report.json")
    report = export_review_report(project, output_path=output)
    print(f"Review report: {output} | comments={report['commentCount']} markers={report['markerCount']}")
    return 0


def _cmd_asset_db(args: argparse.Namespace) -> int:
    if args.asset_db_command == "index":
        report = index_folder(Path(args.folder).resolve(), previews=not args.no_previews)
        print(f"Asset database: {report['database']}")
        print(f"Scanned={report['scanned']} indexed={report['indexed']} errors={len(report['errors'])}")
        return 0 if not report["errors"] else 1
    if args.asset_db_command == "search":
        rows = search_assets(args.query, asset_type=args.type, category=args.category, limit=args.limit)
        for row in rows:
            print(f"{row['type']} | {row.get('category')} | {Path(row['path']).name} | {row['path']}")
        print(f"Results: {len(rows)}")
        return 0
    if args.asset_db_command == "duplicates":
        groups = duplicate_assets()
        for group in groups[:20]:
            print(f"{group['hash'][:12]} | count={group['count']} | bytes={group['bytes']}")
            for item in group["assets"][:5]:
                print(f"  - {item['path']}")
        print(f"Duplicate groups: {len(groups)}")
        return 0
    if args.asset_db_command == "usage":
        report = track_project_usage(Path(args.project_json).resolve())
        print(f"Tracked usage for {report['assetCount']} assets.")
        return 0
    output = Path(args.output).resolve() if args.output else _default_generated_path("asset_database_report.json")
    report = database_report(output_path=output)
    print(f"Asset database report: {output} | assets={report['assetCount']} duplicates={report['duplicateGroupCount']}")
    return 0


def _cmd_pack(args: argparse.Namespace) -> int:
    if args.pack_command == "export":
        output = Path(args.output).resolve() if args.output else None
        manifest = export_pack(Path(args.source).resolve(), pack_type=args.type, output_path=output, name=args.name, author=args.author)
        print(f"Pack exported: {manifest['path']} | entries={len(manifest['entries'])}")
        return 0
    if args.pack_command == "import":
        install_dir = Path(args.output_dir).resolve() if args.output_dir else None
        manifest = import_pack(Path(args.package).resolve(), install_dir=install_dir)
        print(f"Pack installed: {manifest['installedTo']}")
        return 0
    rows = list_installed_packs()
    if not rows:
        print("No installed packs found.")
        return 0
    for row in rows:
        print(f"{row.get('type')} | {row.get('name')} | {row.get('path')}")
    return 0


def _cmd_dataset_export(args: argparse.Namespace) -> int:
    projects = [Path(path).resolve() for path in args.projects]
    output = Path(args.output).resolve() if args.output else _default_generated_path("local_training_dataset.json")
    dataset = export_training_dataset(projects, output, include_text=args.include_text)
    print(f"Dataset exported: {output} | projects={dataset['projectCount']} anonymized={dataset['privacy']['anonymized']}")
    return 0


def _cmd_analytics(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve() if args.output else _default_generated_path("creator_analytics.json")
    report = creator_analytics(output_path=output)
    print(f"Creator analytics: {output}")
    print(f"Renders={report['renderFrequency']} success={report['exportSuccessRate']} savedMinutes={report['workflowEfficiency']['estimatedEditingMinutesSaved']}")
    return 0


def _cmd_api(args: argparse.Namespace) -> int:
    data = api_surface() if args.api_command == "describe" else engine_registry()
    print(json.dumps(data, indent=2))
    return 0


def _cmd_local_policy(args: argparse.Namespace) -> int:
    if args.local_policy_command == "init":
        config = init_local_policy(Path(args.output).resolve() if args.output else None)
        print(f"Local-first policy: {config['path']} | telemetryEnabled={config['telemetryEnabled']}")
        return 0
    config = load_local_policy(Path(args.path).resolve() if args.path else None)
    print(json.dumps(config, indent=2))
    return 0


def _cmd_diagnostics(args: argparse.Namespace) -> int:
    if args.diagnostics_command == "repair":
        report = diagnostics_repair_project(Path(args.project_json).resolve(), Path(args.output).resolve())
        print(f"Repair output: {report['output']} | valid={report['valid']} fixes={len(report['fixes'])}")
        return 0 if report["valid"] else 1
    project = Path(args.project_json).resolve() if args.project_json else None
    output = Path(args.output).resolve() if args.output else _default_generated_path("diagnostics_report.json")
    report = run_diagnostics(project, output_path=output)
    print(f"Diagnostics report: {output}")
    print(f"FFmpeg={report['ffmpeg']['ok']} pluginsInvalid={report['plugins']['invalidCount']} cacheBytes={report['cache']['totalBytes']}")
    return 0 if report["ffmpeg"]["ok"] and not report["plugins"]["invalidCount"] else 1


def _cmd_worker(args: argparse.Namespace) -> int:
    queue_dir = Path(args.queue_dir).resolve() if getattr(args, "queue_dir", None) else None
    if args.worker_command == "enqueue":
        job = enqueue_render(
            Path(args.project_json).resolve(),
            output_path=Path(args.output).resolve() if args.output else None,
            queue_dir=queue_dir,
            quality=args.quality,
        )
        print(f"Queued local render job: {job['id']} -> {job['output']}")
        return 0
    if args.worker_command == "run":
        report = run_worker(queue_dir=queue_dir, once=not args.loop, timeout_seconds=args.timeout)
        print(f"Worker report: {Path(report['heartbeat']).parent / 'worker_report.json'} | processed={report['processed']}")
        return 0 if all(job.get("status") == "completed" for job in report["jobs"]) else 1
    status = worker_status(queue_dir=queue_dir)
    print(json.dumps(status, indent=2))
    return 0


def _cmd_workflow(args: argparse.Namespace) -> int:
    return run_workflow_command(args)


def _cmd_feedback(args: argparse.Namespace) -> int:
    return run_feedback_command(args)


def _cmd_evolution_report(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve() if args.output else _default_generated_path("long_term_evolution_report.json")
    report = build_evolution_report(
        project_path=Path(args.project).resolve() if args.project else None,
        profile_name=args.profile,
        output_path=output,
        include_release_check=args.include_release_check,
    )
    print(f"Long-term evolution report: {output}")
    print(f"Readiness={report['readinessScore']} localFirst={report['localFirst']} nextActions={len(report['nextActions'])}")
    return 0 if report["readinessScore"] >= 60 else 1


def _cmd_local_ai(args: argparse.Namespace) -> int:
    if args.local_ai_command == "status":
        print(json.dumps(local_ai_status(), indent=2))
        return 0
    if args.local_ai_command == "prompt-json":
        output = Path(args.output).resolve() if args.output else _default_generated_path(f"{_slug(args.prompt)[:42] or 'local_ai_project'}.json")
        result = local_prompt_to_json(args.prompt, output_path=output, template=args.template, preset=args.preset)
        source = result.get("source", "heuristic-local-engine")
        model = f" | model={result['model']}" if result.get("model") else ""
        print(f"Local prompt JSON: {result['output']} | source={source}{model}")
        return 0
    if args.local_ai_command == "repair":
        result = local_repair(Path(args.project_json).resolve(), output_path=Path(args.output).resolve())
        print(f"Local repair: {result['output']} | valid={result['valid']} fixes={len(result['fixes'])}")
        return 0 if result["valid"] else 1
    if args.local_ai_command == "suggest":
        output = Path(args.output).resolve() if args.output else _default_generated_path(f"{Path(args.project_json).stem}.local_ai_suggestions.json")
        result = local_scene_suggestions(Path(args.project_json).resolve(), output_path=output)
        print(f"Local suggestions: {output} | suggestions={result['suggestionCount']}")
        return 0
    if args.local_ai_command == "captions":
        result = local_caption_from_transcript(Path(args.project_json).resolve(), Path(args.transcript).resolve(), output_path=Path(args.output).resolve(), mode=args.mode, style=args.style)
        print(f"Local captioned project: {result['output']} | captions={result['captionCount']}")
        return 0
    result = local_transcribe(Path(args.audio).resolve(), output_path=Path(args.output).resolve())
    print(json.dumps(result, indent=2))
    return 0 if result.get("available") and result.get("returnCode") == 0 else 1


def _cmd_model_manager(args: argparse.Namespace) -> int:
    if args.model_command == "select":
        registry = save_model_selection(args.task, args.model)
        print(f"Selected model for {args.task}: {registry['selections'][args.task]['model']}")
        return 0
    output = Path(args.output).resolve() if args.output else _default_generated_path("local_model_status.json")
    report = model_manager_status(output_path=output)
    print(f"Local model status: {output}")
    print(f"Ollama={report['ollama']['health']} models={report['ollama']['modelCount']} whisper={report['whisper']['available']} warnings={len(report['warnings'])}")
    return 0


def _cmd_dependency_check(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve() if args.output else _default_generated_path("dependency_report.json")
    report = offline_dependency_report(output_path=output)
    print(f"Dependency report: {output}")
    print(f"FFmpeg={report['ffmpeg']['installed']} gpuEncoding={report['ffmpeg'].get('supportsGpuEncoding')} fonts={report['fonts']['fontCount']} freeGb={report['storage']['freeGb']}")
    for warning in report["readiness"]["warnings"]:
        print(f"- {warning}")
    return 0 if report["readiness"]["ready"] else 1


def _cmd_installer(args: argparse.Namespace) -> int:
    if args.installer_command == "prepare":
        base_dir = Path(args.base_dir).resolve() if args.base_dir else None
        output = Path(args.output).resolve() if args.output else None
        setup = create_first_run_setup(base_dir, output_path=output)
        print(f"First-run setup: {setup['path']}")
        return 0
    if args.installer_command == "manifest":
        manifest = create_installer_manifest(
            bundled_ffmpeg=Path(args.bundled_ffmpeg).resolve() if args.bundled_ffmpeg else None,
            output_path=Path(args.output).resolve() if args.output else None,
        )
        print(f"Installer manifest: {manifest['path']}")
        return 0
    result = create_portable_zip(output_path=Path(args.output).resolve() if args.output else None)
    print(f"Portable ZIP: {result['path']} | entries={result['entryCount']} | bytes={result['bytes']}")
    return 0


def _cmd_privacy_report(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve() if args.output else _default_generated_path("privacy_security_report.json")
    report = privacy_security_report(output_path=output)
    print(f"Privacy/security report: {output}")
    print(f"localFirst={report['privacy']['localFirst']} telemetry={report['privacy']['telemetry']} pluginWarnings={len(report['plugins']['warnings'])}")
    return 0 if not any(item.get("severity") == "error" for item in report["plugins"]["warnings"]) else 1


def _cmd_reliable_render(args: argparse.Namespace) -> int:
    report = reliable_render_project(
        Path(args.project_json).resolve(),
        output_path=Path(args.output).resolve() if args.output else None,
        attempts=args.attempts,
        quality=args.quality,
        use_cache=args.cache,
        resume=args.resume,
        gpu=args.gpu,
    )
    print(f"Reliable render report: {report['reportPath']}")
    print(f"success={report['success']} attempts={report['attemptCount']} output={report['output']}")
    return 0 if report["success"] else 1


def _cmd_performance_report(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve() if args.output else _default_generated_path("performance_dashboard.json")
    report = performance_dashboard_report(output_path=output)
    print(f"Performance report: {output}")
    print(f"renders={report['render']['renderCount']} avgRender={report['render']['averageRenderSeconds']}s cache={report['cache']['totalBytes']} bytes")
    for warning in report["bottlenecks"]:
        print(f"- {warning}")
    return 0


def _cmd_docs(args: argparse.Namespace) -> int:
    if args.docs_command == "list":
        for doc in list_docs():
            print(f"{doc['key']} | {doc['title']} | {doc['path']}")
        return 0
    print(read_doc(args.key))
    return 0


def _cmd_refine(args: argparse.Namespace) -> int:
    path = Path(args.project_json).resolve()
    refined = refine_project(_read_json(path), args.preset)
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{path.stem}.phase11.{args.preset}.json")
    _relocate_assets_for_output(refined, path, output)
    validate_project(refined)
    _write_json(output, refined)
    print(f"Refined project: {output}")
    print(f"Preset={args.preset} suggestions={refined.get('metadata', {}).get('phase11', {}).get('suggestionCount', 0)}")
    if args.render:
        parsed = ProjectParser().load(output)
        render_path = output.with_suffix(".mp4")
        VideoRenderer(parsed, output_path=render_path, quality=args.quality, use_cache=True, resume=True).render()
        print(f"Rendered refined preview: {render_path}")
    return 0


def _cmd_color(args: argparse.Namespace) -> int:
    if args.color_command == "list":
        for preset in list_color_presets():
            print(f"{preset['key']} | {preset['label']} | nodes={len(preset['nodes'])}")
        return 0
    if args.color_command == "luts":
        rows = list_luts()
        if not rows:
            print("No local LUT files found in luts/.")
            return 0
        for row in rows:
            print(f"{row['name']} | {row['path']}")
        return 0
    path = Path(args.project_json).resolve()
    lut = Path(args.lut).resolve() if args.lut else None
    colored = apply_color_pipeline(_read_json(path), args.preset, lut_path=lut)
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{path.stem}.{args.preset}.color.json")
    _relocate_assets_for_output(colored, path, output)
    validate_project(colored)
    _write_json(output, colored)
    print(f"Color-pipeline project: {output}")
    return 0


def _cmd_advanced(args: argparse.Namespace) -> int:
    project_path = Path(args.project_json).resolve()
    data = _read_json(project_path)
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{project_path.stem}.advanced.json")
    report_output = Path(args.report).resolve() if args.report else output.with_suffix(".advanced_report.json")
    result = apply_advanced_cinematic_engine(data, output_path=report_output)
    _relocate_assets_for_output(result["project"], project_path, output)
    validate_project(result["project"])
    _write_json(output, result["project"])
    print(f"Advanced cinematic project: {output}")
    print(f"Advanced systems report: {report_output}")
    print(
        "Systems: "
        f"{len(result['report']['systems'])} | "
        f"decisions={len(result['report'].get('decisions', []))} | "
        f"warnings={len(result['report'].get('warnings', []))}"
    )
    return 0


def _cmd_cache(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve() if getattr(args, "root", None) else None
    if args.cache_command == "report":
        output = Path(args.output).resolve() if args.output else _default_generated_path("cache_report.json")
        report = cache_report(root, output_path=output)
        print(f"Cache report: {output} | buckets={report['bucketCount']} bytes={report['totalBytes']}")
        return 0
    result = cleanup_caches(root, max_bytes=int(args.max_gb * 1024**3), dry_run=args.dry_run)
    print(f"Cache cleanup: deleted={result['deletedCount']} bytes={result['deletedBytes']} dryRun={result['dryRun']}")
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    demo_dir = Path(__file__).resolve().parents[1] / "examples" / "demos"
    rows = sorted(demo_dir.glob("*.json")) if demo_dir.exists() else []
    if not rows:
        print("No built-in demos found.")
        return 0
    for path in rows:
        try:
            data = _read_json(path)
            print(f"{path.stem} | {data.get('metadata', {}).get('demoName', path.stem)} | {path}")
        except Exception:
            print(f"{path.stem} | unreadable | {path}")
    return 0


def _cmd_architecture_audit(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve() if args.output else _default_generated_path("architecture_audit.json")
    report = architecture_audit(output_path=output)
    print(f"Architecture audit: {output}")
    print(f"pythonFiles={report['summary']['pythonFileCount']} docs={report['summary']['docCount']} warnings={report['summary']['warningCount']}")
    for warning in report["warnings"]:
        print(f"- {warning}")
    return 0


def _cmd_profile_run(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{Path(args.project_json).stem}.profile.json")
    report = profile_workflow(Path(args.project_json).resolve(), output_path=output, include_render=args.include_render)
    print(f"Performance profile: {output}")
    for item in report["slowest"]:
        print(f"- {item['name']}: {item['seconds']}s ok={item['ok']}")
    return 0 if all(item["ok"] for item in report["timings"]) else 1


def _cmd_release_check(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve() if args.output else _default_generated_path("release_candidate_check.json")
    report = release_candidate_check(output_path=output, include_render_profile=args.include_render_profile)
    print(f"Release candidate check: {output}")
    print(f"ready={report['ready']} checks={report['checkCount']} failed={report['failedCount']}")
    for item in report["checks"]:
        if not item["ok"]:
            print(f"- failed {item['name']}: {item.get('error') or item.get('details')}")
    return 0 if report["ready"] else 1


def _cmd_showcase(args: argparse.Namespace) -> int:
    if args.list_styles:
        for style in list_showcase_styles():
            print(style)
        return 0
    if not args.recording:
        print("A recording path is required unless --list-styles is used.")
        return 2

    recording = Path(args.recording).resolve()
    output = Path(args.output).resolve() if args.output else _default_generated_path(f"{recording.stem}.showcase_project.json")
    analysis_output = Path(args.analysis_output).resolve() if args.analysis_output else output.with_suffix(".analysis.json")
    spec_output = Path(args.spec_output).resolve() if args.spec_output else output.with_suffix(".spec.json")
    score_output = Path(args.score_output).resolve() if args.score_output else output.with_suffix(".score.json")
    advanced_output = Path(args.advanced_output).resolve() if args.advanced_output else output.with_suffix(".advanced.json")
    result = build_showcase_project(
        recording,
        music_path=Path(args.music).resolve() if args.music else None,
        logo_path=Path(args.logo).resolve() if args.logo else None,
        style=args.style,
        style_profile=args.style_profile,
        instructions=args.instructions,
        product_name=args.product_name,
        duration=args.duration,
        manual_overrides=args.overrides,
        output_path=output,
        analysis_output_path=analysis_output,
        spec_output_path=spec_output,
        score_output_path=score_output,
        advanced_output_path=advanced_output,
    )
    validate_project(result["project"])
    print(f"Cinematic showcase project: {output}")
    print(f"Desktop analysis: {analysis_output}")
    print(f"Structured spec: {spec_output}")
    print(f"Showcase score: {score_output} | overall={result['score']['overall']}")
    print(f"Advanced cinematic report: {advanced_output} | decisions={len(result['advancedReport'].get('decisions', []))}")
    print(f"Style: {result['styleProfile'].get('name', result['styleProfile'].get('key'))}")
    print(f"Scenes: {len(result['project']['timeline'])} | duration={result['project']['project']['duration']}s")

    if args.render:
        project = ProjectParser().load(output)
        render_output = Path(args.render_output).resolve() if args.render_output else output.parent / f"{output.stem}.mp4"
        renderer = VideoRenderer(
            project,
            output_path=render_output,
            quality=args.quality,
            use_cache=args.cache,
            resume=args.cache,
            gpu=args.gpu,
        )
        final_path = renderer.render()
        print(f"Showcase render: {final_path}")
    return 0


_COMMAND_HANDLERS: dict[str, _CommandHandler] = {
    "render": _cmd_render,
    "validate": _cmd_validate,
    "preview": _cmd_preview,
    "quick-create": _cmd_quick_create,
    "foundation-pass": _cmd_foundation_pass,
    "repair": _cmd_repair,
    "template": _cmd_template,
    "ai-generate": _cmd_ai_generate,
    "preset": _cmd_preset,
    "analyze-audio": _cmd_analyze_audio,
    "beat-sync": _cmd_beat_sync,
    "auto-select": _cmd_auto_select,
    "smart-build": _cmd_smart_build,
    "pipeline": _cmd_pipeline,
    "autonomous": _cmd_autonomous,
    "youtube-short": _cmd_youtube_short,
    "content-generate": _cmd_content_generate,
    "auto-template": _cmd_auto_template,
    "media": _cmd_media,
    "content-review": _cmd_content_review,
    "post-package": _cmd_post_package,
    "post-export": _cmd_post_export,
    "repurpose": _cmd_repurpose,
    "batch": _cmd_batch,
    "highlight-detect": _cmd_highlight_detect,
    "thumbnail": _cmd_thumbnail,
    "suggest": _cmd_suggest,
    "captions": _cmd_captions,
    "style": _cmd_style,
    "director": _cmd_director,
    "storyboard": _cmd_storyboard,
    "asset-analyze": _cmd_asset_analyze,
    "resolve-broll": _cmd_resolve_broll,
    "history": _cmd_history,
    "package": _cmd_package,
    "plugin": _cmd_plugin,
    "realtime-preview": _cmd_realtime_preview,
    "interactive-preview": _cmd_interactive_preview,
    "template-pack": _cmd_template_pack,
    "brand": _cmd_brand,
    "manifest": _cmd_manifest,
    "quality-check": _cmd_quality_check,
    "final-preflight": _cmd_final_preflight,
    "reformat": _cmd_reformat,
    "recovery": _cmd_recovery,
    "profile": _cmd_profile,
    "automation": _cmd_automation,
    "metrics": _cmd_metrics,
    "cinematic-enhance": _cmd_cinematic_enhance,
    "effect-graph": _cmd_effect_graph,
    "understand-clip": _cmd_understand_clip,
    "audio-intel": _cmd_audio_intel,
    "scene-build": _cmd_scene_build,
    "project-analyze": _cmd_project_analyze,
    "workspace": _cmd_workspace,
    "review": _cmd_review,
    "asset-db": _cmd_asset_db,
    "pack": _cmd_pack,
    "dataset-export": _cmd_dataset_export,
    "analytics": _cmd_analytics,
    "api": _cmd_api,
    "local-policy": _cmd_local_policy,
    "diagnostics": _cmd_diagnostics,
    "worker": _cmd_worker,
    "workflow": _cmd_workflow,
    "feedback": _cmd_feedback,
    "evolution-report": _cmd_evolution_report,
    "local-ai": _cmd_local_ai,
    "model-manager": _cmd_model_manager,
    "dependency-check": _cmd_dependency_check,
    "installer": _cmd_installer,
    "privacy-report": _cmd_privacy_report,
    "reliable-render": _cmd_reliable_render,
    "performance-report": _cmd_performance_report,
    "docs": _cmd_docs,
    "refine": _cmd_refine,
    "color": _cmd_color,
    "advanced": _cmd_advanced,
    "cache": _cmd_cache,
    "demo": _cmd_demo,
    "architecture-audit": _cmd_architecture_audit,
    "profile-run": _cmd_profile_run,
    "release-check": _cmd_release_check,
    "showcase": _cmd_showcase,
}


def _generate_placeholders_for_project(project_path: Path) -> None:
    project = ProjectParser().load(project_path)
    AssetResolver(project, generate_missing=True).verify_referenced_assets()
    print(f"Placeholder assets ready for: {project_path}")


def _print_repair_result(result: Any, target: Path | None) -> None:
    if result.errors_before:
        print("Detected validation issues:")
        for line in result.errors_before:
            print(f"- {line}")
    if result.fixes:
        print("Applied fixes:")
        for fix in result.fixes:
            print(f"- {fix}")
    if result.valid:
        print("Repaired JSON is valid.")
        if target:
            print(f"Written to: {target}")
    else:
        print("Repair could not make the JSON valid.")
        for line in result.errors_after:
            print(f"- {line}")


def _write_preset_override(project_path: Path, preset: str) -> Path:
    data = _read_json(project_path)
    normalized = get_export_preset(preset).key
    data["exportPreset"] = normalized
    output = _default_generated_path(f"{project_path.stem}.{normalized}.json")
    _relocate_assets_for_output(data, project_path, output)
    _write_json(output, data)
    return output


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _content_review_project(plan_path: Path) -> dict[str, Any]:
    project_path = plan_path.parent / "project.json"
    if project_path.exists():
        return _read_json(project_path)
    return {"assets": {}}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def _default_repaired_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}.repaired.json")


def _default_generated_path(filename: str) -> Path:
    return Path(__file__).resolve().parents[1] / "examples" / "generated" / filename


def _resolve_audio_asset_path(project_path: Path, data: dict[str, Any], asset_key: str) -> Path:
    assets = data.get("assets", {})
    if asset_key not in assets:
        raise KeyError(f"Audio asset '{asset_key}' is not defined in {project_path}")
    raw = Path(assets[asset_key])
    return raw if raw.is_absolute() else (project_path.parent / raw).resolve()


def _relocate_assets_for_output(data: dict[str, Any], source_project_path: Path, output_path: Path) -> None:
    if source_project_path.parent.resolve() == output_path.parent.resolve():
        return
    assets = data.get("assets", {})
    if not isinstance(assets, dict):
        return
    for key, value in list(assets.items()):
        raw = Path(str(value))
        if not raw.is_absolute():
            assets[key] = str((source_project_path.parent / raw).resolve())


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_")
