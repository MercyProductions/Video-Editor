from __future__ import annotations

import argparse
import json
import logging
import shlex
import sys
import time
from pathlib import Path
from typing import Any

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
from feedback.loops import (
    creator_identity_report,
    export_local_training_dataset,
    hook_effectiveness_report,
    learn_preferences,
    record_ai_feedback_event,
    record_render_review,
    render_self_analysis,
    style_consistency_report,
)
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
from workspace.system import add_workspace_profile, close_project, create_workspace, describe_workspace, list_workspace_profiles, list_workspaces, open_project, save_layout


COMMANDS = {
    "render",
    "validate",
    "preview",
    "template",
    "ai-generate",
    "repair",
    "preset",
    "analyze-audio",
    "beat-sync",
    "auto-select",
    "smart-build",
    "captions",
    "style",
    "director",
    "storyboard",
    "asset-analyze",
    "resolve-broll",
    "history",
    "package",
    "plugin",
    "realtime-preview",
    "interactive-preview",
    "template-pack",
    "brand",
    "manifest",
    "quality-check",
    "final-preflight",
    "reformat",
    "recovery",
    "pipeline",
    "autonomous",
    "youtube-short",
    "content-generate",
    "content-review",
    "post-package",
    "post-export",
    "repurpose",
    "batch",
    "highlight-detect",
    "thumbnail",
    "suggest",
    "profile",
    "automation",
    "metrics",
    "cinematic-enhance",
    "effect-graph",
    "understand-clip",
    "audio-intel",
    "scene-build",
    "project-analyze",
    "workspace",
    "review",
    "asset-db",
    "pack",
    "dataset-export",
    "analytics",
    "api",
    "local-policy",
    "diagnostics",
    "worker",
    "workflow",
    "feedback",
    "evolution-report",
    "local-ai",
    "model-manager",
    "dependency-check",
    "installer",
    "privacy-report",
    "reliable-render",
    "performance-report",
    "docs",
    "refine",
    "color",
    "cache",
    "demo",
    "architecture-audit",
    "profile-run",
    "release-check",
    "showcase",
    "advanced",
    "quick-create",
    "foundation-pass",
    "auto-template",
    "media",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="render.py",
        description="AI-assisted automatic video editor CLI.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )
    subparsers = parser.add_subparsers(dest="command")

    render_parser = subparsers.add_parser("render", help="Render a project JSON to MP4.")
    render_parser.add_argument("project_json")
    render_parser.add_argument("-o", "--output", default=None)
    render_parser.add_argument("--preset", default=None, help="Override export preset for this render.")
    render_parser.add_argument("--format", choices=["mp4", "mov", "mkv", "webm", "gif", "image_sequence"], default=None, help="Override output container. Defaults to the output file extension or MP4.")
    render_parser.add_argument("--repair", action="store_true", help="Repair invalid JSON before rendering.")
    render_parser.add_argument("--preview", action="store_true", help="Write preview reports before rendering.")
    render_parser.add_argument("--keep-temp", action="store_true")
    render_parser.add_argument("--generate-placeholders", action="store_true")
    render_parser.add_argument("--quality", choices=["preview", "final"], default="final")
    render_parser.add_argument("--cache", action="store_true", help="Cache rendered scene files.")
    render_parser.add_argument("--resume", action="store_true", help="Reuse cached scene files when present.")
    render_parser.add_argument("--gpu", action="store_true", help="Try GPU H.264 encoding when available.")
    render_parser.add_argument("--backend", choices=["cpu", "gpu", "hybrid"], default="cpu", help="Render backend preference. Hybrid tries GPU encoding with CPU fallback.")
    render_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    validate_parser = subparsers.add_parser("validate", help="Validate a project JSON file.")
    validate_parser.add_argument("project_json")
    validate_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    preview_parser = subparsers.add_parser("preview", help="Generate timeline and asset reports.")
    preview_parser.add_argument("project_json")
    preview_parser.add_argument("-o", "--output-dir", default=None)
    preview_parser.add_argument("--repair", action="store_true")
    preview_parser.add_argument("--generate-placeholders", action="store_true")
    preview_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    quick_parser = subparsers.add_parser("quick-create", help="MVP 0.1: create project JSON from one MP4 and optionally render it.")
    quick_parser.add_argument("recording", help="One local .mp4 desktop recording.")
    quick_parser.add_argument("--music", default=None, help="Optional local music file.")
    quick_parser.add_argument("--logo", default=None, help="Optional local logo/image overlay.")
    quick_parser.add_argument("--title", default="Automatic Edit")
    quick_parser.add_argument("--caption", default="Generated from local media.")
    quick_parser.add_argument("--instructions", default="", help="Stored in metadata for later iterations.")
    quick_parser.add_argument("--style", choices=["clean", "cinematic", "red_black"], default="clean")
    quick_parser.add_argument("--duration", type=float, default=None)
    quick_parser.add_argument("--width", type=int, default=1280)
    quick_parser.add_argument("--height", type=int, default=720)
    quick_parser.add_argument("--fps", type=int, default=30)
    quick_parser.add_argument("-o", "--output", default=None, help="Generated project JSON path.")
    quick_parser.add_argument("--render", action="store_true", help="Render the generated project immediately.")
    quick_parser.add_argument("--render-output", default=None, help="Rendered MP4 path.")
    quick_parser.add_argument("--quality", choices=["preview", "final"], default="preview")
    quick_parser.add_argument("--cache", action="store_true")
    quick_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    foundation_parser = subparsers.add_parser("foundation-pass", help="Apply foundational stability systems to a project JSON.")
    foundation_parser.add_argument("project_json")
    foundation_parser.add_argument("-o", "--output", default=None, help="Foundation-normalized project JSON path.")
    foundation_parser.add_argument("--report", default=None, help="Foundation report JSON path.")
    foundation_parser.add_argument("--metadata-dir", default=None, help="Structured metadata/history directory.")
    foundation_parser.add_argument("--cache-dir", default=None, help="Multi-layer cache root.")
    foundation_parser.add_argument("--generate-proxies", action="store_true", help="Generate low-resolution proxy media for video assets.")
    foundation_parser.add_argument("--benchmark", action="store_true", help="Include benchmark/stress diagnostics.")
    foundation_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    repair_parser = subparsers.add_parser("repair", help="Repair an invalid project JSON file.")
    repair_parser.add_argument("project_json")
    repair_parser.add_argument("-o", "--output", default=None)
    repair_parser.add_argument("--in-place", action="store_true")
    repair_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    template_parser = subparsers.add_parser("template", help="Work with reusable project templates.")
    template_subparsers = template_parser.add_subparsers(dest="template_command", required=True)
    template_subparsers.add_parser("list", help="List available templates.")
    template_create = template_subparsers.add_parser("create", help="Create a project JSON from a template.")
    template_create.add_argument("name", choices=template_names())
    template_create.add_argument("-o", "--output", default=None)
    template_create.add_argument("--preset", default=None)
    template_create.add_argument("--generate-placeholders", action="store_true")
    template_create.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    ai_parser = subparsers.add_parser("ai-generate", help="Generate project JSON from a plain English prompt.")
    ai_parser.add_argument("prompt")
    ai_parser.add_argument("-o", "--output", default=None)
    ai_parser.add_argument("--template", choices=template_names(), default=None)
    ai_parser.add_argument("--preset", default=None)
    ai_parser.add_argument("--generate-placeholders", action="store_true")
    ai_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    preset_parser = subparsers.add_parser("preset", help="List export presets.")
    preset_subparsers = preset_parser.add_subparsers(dest="preset_command", required=True)
    preset_subparsers.add_parser("list", help="List export presets.")

    analyze_parser = subparsers.add_parser("analyze-audio", help="Analyze beats, BPM, bass drops, peaks, and quiet sections.")
    analyze_parser.add_argument("audio")
    analyze_parser.add_argument("-o", "--output", default=None)
    analyze_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    beat_parser = subparsers.add_parser("beat-sync", help="Apply music beat timing to an existing project JSON.")
    beat_parser.add_argument("project_json")
    beat_parser.add_argument("--audio", default=None, help="Direct audio file path.")
    beat_parser.add_argument("--asset", default="music", help="Project asset key to analyze when --audio is omitted.")
    beat_parser.add_argument("-o", "--output", default=None)
    beat_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    select_parser = subparsers.add_parser("auto-select", help="Scan a folder of clips and choose highlight segments.")
    select_parser.add_argument("clips_folder")
    select_parser.add_argument("--scene-duration", type=float, default=3)
    select_parser.add_argument("--max-clips", type=int, default=8)
    select_parser.add_argument("-o", "--output", default=None)
    select_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    smart_parser = subparsers.add_parser("smart-build", help="Build an edited project from a clips folder and music.")
    smart_parser.add_argument("clips_folder")
    smart_parser.add_argument("--music", required=True)
    smart_parser.add_argument("--duration", type=float, default=20)
    smart_parser.add_argument("--scene-duration", type=float, default=2.5)
    smart_parser.add_argument("--style", default="gaming_montage", choices=list_styles())
    smart_parser.add_argument("--preset", default="youtube_1080p")
    smart_parser.add_argument("-o", "--output", default=None)
    smart_parser.add_argument("--generate-placeholders", action="store_true")
    smart_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    pipeline_parser = subparsers.add_parser("pipeline", help="Run idea-to-assets-to-edit-to-export generation.")
    pipeline_parser.add_argument("prompt")
    pipeline_parser.add_argument("clips_folder")
    pipeline_parser.add_argument("--music", default=None)
    pipeline_parser.add_argument("--style", default=None, choices=list_styles())
    pipeline_parser.add_argument("--preset", default=None, choices=["youtube_1080p", "tiktok_reels", "shorts", "square", "discord_720p", "cinematic_4k"])
    pipeline_parser.add_argument("--duration", type=float, default=None)
    pipeline_parser.add_argument("--profile", default=None)
    pipeline_parser.add_argument("-o", "--output-dir", default=None)
    pipeline_parser.add_argument("--render", action="store_true")
    pipeline_parser.add_argument("--quality", choices=["preview", "final"], default="preview")
    pipeline_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    autonomous_parser = subparsers.add_parser("autonomous", help="Run autonomous idea-to-review-to-package production.")
    autonomous_parser.add_argument("idea", help="Creator idea, product brief, or raw notes.")
    autonomous_parser.add_argument("--assets", dest="assets_folder", default=None, help="Optional folder of clips/images to use.")
    autonomous_parser.add_argument("--music", default=None, help="Optional local music track.")
    autonomous_parser.add_argument("--logo", default=None, help="Optional local logo/branding image.")
    autonomous_parser.add_argument("--profile", default=None, help="Creator profile name or .creator-profile.json path.")
    autonomous_parser.add_argument(
        "--platform",
        default=None,
        choices=["shorts", "youtube_shorts", "youtube_short", "tiktok", "reels", "instagram_reels", "youtube", "youtube_landscape", "landscape", "square"],
        help="Target platform. Defaults are inferred from the idea/content type.",
    )
    autonomous_parser.add_argument(
        "--content-type",
        default="auto",
        choices=["auto", "youtube_shorts", "tiktok", "product_showcase", "tutorial", "promo_ad"],
        help="Autonomous structure to use, or auto-infer from the idea.",
    )
    autonomous_parser.add_argument("--vibe", default=None, help="Desired creative direction, e.g. premium red black cinematic.")
    autonomous_parser.add_argument("--duration", type=float, default=None, help="Target duration in seconds.")
    autonomous_parser.add_argument("--variants", type=int, default=4, help="Number of hook/pacing/CTA variants to prepare.")
    autonomous_parser.add_argument("--approved", action="store_true", help="Mark generated sections approved and allow final render/package.")
    autonomous_parser.add_argument("--render-preview", action="store_true", help="Render a preview MP4 for review.")
    autonomous_parser.add_argument("--final-render", action="store_true", help="Render final_video.mp4 when --approved is also set.")
    autonomous_parser.add_argument("--package", action="store_true", help="Create upload-ready posting package after approved final render.")
    autonomous_parser.add_argument("--quality", choices=["preview", "final"], default="preview")
    autonomous_parser.add_argument("--cache", action="store_true")
    autonomous_parser.add_argument("--gpu", action="store_true")
    autonomous_parser.add_argument("-o", "--output-dir", default=None)
    autonomous_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    youtube_short_parser = subparsers.add_parser("youtube-short", help="Create a structured YouTube Short from a prompt, optional assets, and optional music.")
    youtube_short_parser.add_argument("prompt")
    youtube_short_parser.add_argument("--assets", dest="assets_folder", default=None, help="Optional folder of source clips.")
    youtube_short_parser.add_argument("--music", default=None, help="Optional music track for beat-aware pacing metadata.")
    youtube_short_parser.add_argument("--logo", default=None, help="Optional logo image for intro/outro title cards.")
    youtube_short_parser.add_argument("--style", default="auto", choices=["auto", *list_styles()], help="Use a style preset or let the local generator choose.")
    youtube_short_parser.add_argument("--duration", type=float, default=None, help="Target duration in seconds, clamped to 8-45.")
    youtube_short_parser.add_argument("-o", "--output-dir", default=None)
    youtube_short_parser.add_argument("--render", action="store_true", help="Render final_video.mp4 after generating project JSON.")
    youtube_short_parser.add_argument("--quality", choices=["preview", "final"], default="preview")
    youtube_short_parser.add_argument("--cache", action="store_true", help="Use scene render cache when rendering.")
    youtube_short_parser.add_argument("--gpu", action="store_true", help="Try GPU H.264 encoding when rendering.")
    youtube_short_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    content_parser = subparsers.add_parser("content-generate", help="Generate complete short-form content from an idea, notes, and optional assets.")
    content_parser.add_argument("idea")
    content_parser.add_argument("--mode", default="youtube_shorts", choices=["youtube_shorts", "tiktok", "product_showcase", "tutorial", "promo_ad"])
    content_parser.add_argument("--product-name", default=None)
    content_parser.add_argument("--platform", default=None, help="Target platform such as shorts, tiktok, youtube, square.")
    content_parser.add_argument("--goal", default=None)
    content_parser.add_argument("--bullet", action="append", default=[], help="Product feature or note. May be used multiple times.")
    content_parser.add_argument("--assets", dest="assets_folder", default=None, help="Optional folder of raw footage/images.")
    content_parser.add_argument("--music", default=None)
    content_parser.add_argument("--logo", default=None)
    content_parser.add_argument("--duration", type=float, default=None)
    content_parser.add_argument("--tone", default="cinematic", choices=["minimal", "cinematic", "aggressive", "clean"])
    content_parser.add_argument("--style", default="auto", choices=["auto", *list_styles()])
    content_parser.add_argument("--existing-plan", default=None, help="Existing content_plan.json for locked/regenerated workflows.")
    content_parser.add_argument("--regenerate", default="full", choices=["full", "none", "hook", "script", "captions", "scenes", "scene_plan", "style"])
    content_parser.add_argument(
        "--lock",
        action="append",
        default=[],
        help="Lock script, hook, style, music, scene:<id>, caption:<id>, timing:<id>, title:<id>, or script:<index>. May be repeated.",
    )
    content_parser.add_argument("--approved", action="store_true", help="Mark all generated sections approved. Required for final-quality render.")
    content_parser.add_argument("-o", "--output-dir", default=None)
    content_parser.add_argument("--render", action="store_true")
    content_parser.add_argument("--quality", choices=["preview", "final"], default="preview")
    content_parser.add_argument("--cache", action="store_true")
    content_parser.add_argument("--gpu", action="store_true")
    content_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    auto_template_parser = subparsers.add_parser("auto-template", help="Beginner mode: generate a polished video from media and a premium template without hand-writing JSON.")
    auto_template_subparsers = auto_template_parser.add_subparsers(dest="auto_template_command", required=True)
    auto_template_list = auto_template_subparsers.add_parser("list", help="List beginner auto-template presets.")
    auto_template_list.add_argument("--json", action="store_true", help="Print template metadata as JSON.")
    auto_template_list.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    auto_template_create = auto_template_subparsers.add_parser("create", help="Create project.json and optionally render from a beginner template.")
    auto_template_create.add_argument("--template", default="premium_product_showcase", choices=beginner_template_names())
    auto_template_create.add_argument("--media", default=None, help="Optional source video file such as a desktop MP4 recording.")
    auto_template_create.add_argument("--images", default=None, help="Optional folder of images.")
    auto_template_create.add_argument("--assets", default=None, help="Optional product asset folder with images/videos.")
    auto_template_create.add_argument("--music", default=None, help="Optional music file.")
    auto_template_create.add_argument("--logo", default=None, help="Optional logo image.")
    auto_template_create.add_argument("--platform", default=None, help="Optional platform override such as shorts, tiktok, youtube, square.")
    auto_template_create.add_argument("--product-name", required=True)
    auto_template_create.add_argument("--goal", required=True, help="Plain-language video goal.")
    auto_template_create.add_argument("--feature", action="append", default=[], help="Key feature or talking point. May be used multiple times.")
    auto_template_create.add_argument("--vibe", default="", help="Desired vibe, e.g. premium red black cinematic.")
    auto_template_create.add_argument("--duration", type=float, default=None)
    auto_template_create.add_argument("-o", "--output-dir", default=None)
    auto_template_create.add_argument("--render", action="store_true", help="Render a preview/final MP4 after generating project.json.")
    auto_template_create.add_argument("--quality", choices=["preview", "final"], default="preview")
    auto_template_create.add_argument("--cache", action="store_true")
    auto_template_create.add_argument("--gpu", action="store_true")
    auto_template_create.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    media_parser = subparsers.add_parser("media", help="Inspect, normalize, and import creator media files.")
    media_subparsers = media_parser.add_subparsers(dest="media_command", required=True)
    media_formats = media_subparsers.add_parser("formats", help="List supported import/export formats.")
    media_formats.add_argument("--json", action="store_true")
    media_inspect = media_subparsers.add_parser("inspect", help="Probe one media file and print detailed metadata.")
    media_inspect.add_argument("file")
    media_inspect.add_argument("-o", "--output", default=None)
    media_import = media_subparsers.add_parser("import", help="Copy media into a project, normalize if needed, and generate metadata/previews.")
    media_import.add_argument("files", nargs="+")
    media_import.add_argument("--project-dir", default=None, help="Project folder that should receive assets/. Defaults to current directory.")
    media_import.add_argument("--normalize", choices=["auto", "always", "never"], default="auto")
    media_import.add_argument("--no-proxy", action="store_true")
    media_import.add_argument("--no-thumbnails", action="store_true")
    media_import.add_argument("--no-waveforms", action="store_true")
    media_import.add_argument("--fps", type=int, default=30)
    media_import.add_argument("--sample-rate", type=int, default=48000)
    media_import.add_argument("-o", "--output", default=None)
    media_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    content_review_parser = subparsers.add_parser("content-review", help="Review, approve, lock, and compare generated content plans.")
    content_review_subparsers = content_review_parser.add_subparsers(dest="content_review_command", required=True)
    content_review_show = content_review_subparsers.add_parser("show", help="Print the generation review packet for a content_plan.json.")
    content_review_show.add_argument("plan")
    content_review_show.add_argument("-o", "--output-dir", default=None)
    content_review_approve = content_review_subparsers.add_parser("approve", help="Set approval status for one generated section.")
    content_review_approve.add_argument("plan")
    content_review_approve.add_argument("--section", default="all", help="Section key such as all, hook, script:0, scene:<id>, caption:<id>, timing:<id>, style, music.")
    content_review_approve.add_argument("--status", default="approved", choices=["needs_review", "approved", "locked", "rejected"])
    content_review_approve.add_argument("-o", "--output", default=None, help="Optional output content_plan.json. Defaults to in-place update.")
    content_review_compare = content_review_subparsers.add_parser("compare", help="Compare old and new generated content plans.")
    content_review_compare.add_argument("old_plan")
    content_review_compare.add_argument("new_plan")
    content_review_compare.add_argument("--old-project", default=None)
    content_review_compare.add_argument("--new-project", default=None)
    content_review_compare.add_argument("--old-render", default=None)
    content_review_compare.add_argument("--new-render", default=None)
    content_review_compare.add_argument("-o", "--output-dir", default=None)

    post_package_parser = subparsers.add_parser("post-package", help="Create upload-ready local posting packages from a rendered video.")
    post_package_parser.add_argument("project_json")
    post_package_parser.add_argument("video")
    post_package_parser.add_argument(
        "--platforms",
        nargs="+",
        default=["all"],
        choices=[
            "all",
            "youtube_shorts",
            "shorts",
            "youtube",
            "youtube_landscape",
            "youtube_1080p",
            "tiktok",
            "instagram_reels",
            "instagram",
            "reels",
            "discord",
            "discord_720p",
            "high_quality_archive",
            "archive",
            "x_twitter",
            "twitter",
            "x",
        ],
    )
    post_package_parser.add_argument("--title", default=None)
    post_package_parser.add_argument("--accent", default=None)
    post_package_parser.add_argument("--render-report", default=None)
    post_package_parser.add_argument("--render-logs", default=None)
    post_package_parser.add_argument("-o", "--output-dir", default=None)
    post_package_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    post_export_parser = subparsers.add_parser("post-export", help="Review finished exports, create re-export JSON, save reusable templates, and record success notes.")
    post_export_subparsers = post_export_parser.add_subparsers(dest="post_export_command", required=True)
    post_export_review = post_export_subparsers.add_parser("review", help="Inspect a finished export and write post-export diagnostics.")
    post_export_review.add_argument("project_json")
    post_export_review.add_argument("video")
    post_export_review.add_argument("--package-dir", default=None)
    post_export_review.add_argument("-o", "--output", default=None)
    post_export_reexport = post_export_subparsers.add_parser("reexport", help="Create a quick re-export project JSON with safer settings.")
    post_export_reexport.add_argument("project_json")
    post_export_reexport.add_argument("--preset", default=None)
    post_export_reexport.add_argument("--format", default="mp4", choices=["mp4", "mov", "mkv", "webm", "gif"])
    post_export_reexport.add_argument("--mode", default="custom", choices=["custom", "lower_size", "higher_quality", "platform", "captions_off"])
    post_export_reexport.add_argument("--captions", default="keep", choices=["keep", "on", "off"])
    post_export_reexport.add_argument("--thumbnail", default=None)
    post_export_reexport.add_argument("-o", "--output-dir", default=None)
    post_export_template = post_export_subparsers.add_parser("template", help="Save style, pacing, captions, export settings, intro/outro, and lighting as a reusable local template.")
    post_export_template.add_argument("project_json")
    post_export_template.add_argument("--video", default=None)
    post_export_template.add_argument("--name", required=True)
    post_export_template.add_argument("--note", default=None)
    post_export_template.add_argument("-o", "--output", default=None)
    post_export_variants = post_export_subparsers.add_parser("variants", help="Generate editable project variants from a successful export.")
    post_export_variants.add_argument("project_json")
    post_export_variants.add_argument("--variant", action="append", default=[], choices=["shorter", "longer", "hook", "cta", "thumbnail", "caption_style"])
    post_export_variants.add_argument("--hook", default=None)
    post_export_variants.add_argument("--cta", default=None)
    post_export_variants.add_argument("-o", "--output-dir", default=None)
    post_export_note = post_export_subparsers.add_parser("note", help="Save a local success/reuse note for future creator preference learning.")
    post_export_note.add_argument("project_json")
    post_export_note.add_argument("--video", default=None)
    post_export_note.add_argument("--profile", default="Default Creator")
    post_export_note.add_argument("--tag", action="append", default=[], choices=["good_pacing", "good_style", "reuse_this", "too_much_motion", "captions_too_fast"])
    post_export_note.add_argument("--note", default=None)
    post_export_note.add_argument("-o", "--output", default=None)

    repurpose_parser = subparsers.add_parser("repurpose", help="Turn one strong edit into multi-platform, hook, and CTA variants.")
    repurpose_parser.add_argument("project_json")
    repurpose_parser.add_argument("--platforms", nargs="+", default=["all"], choices=["all", "youtube_shorts", "shorts", "tiktok", "instagram_reels", "instagram", "reels", "youtube", "youtube_landscape", "youtube_1080p", "discord", "x_twitter", "twitter", "x"])
    repurpose_parser.add_argument("--hook", action="append", default=[], choices=["all", "serious", "curiosity", "problem_solution", "fast_aggressive", "clean_professional"])
    repurpose_parser.add_argument("--cta", action="append", default=[], choices=["all", "subscribe", "visit_website", "download", "comment", "follow"])
    repurpose_parser.add_argument("--no-reuse-style", action="store_true")
    repurpose_parser.add_argument("--max-variants", type=int, default=None)
    repurpose_parser.add_argument("--render", action="store_true")
    repurpose_parser.add_argument("--package", action="store_true")
    repurpose_parser.add_argument("--quality", choices=["preview", "final"], default="preview")
    repurpose_parser.add_argument("--generate-placeholders", action="store_true")
    repurpose_parser.add_argument("-o", "--output-dir", default=None)
    repurpose_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    batch_parser = subparsers.add_parser("batch", help="Generate multiple A/B edits from the same assets.")
    batch_parser.add_argument("prompt")
    batch_parser.add_argument("clips_folder")
    batch_parser.add_argument("--music", default=None)
    batch_parser.add_argument("--styles", nargs="+", default=["clean_cinematic", "red_black_aegis"], choices=list_styles())
    batch_parser.add_argument("--presets", nargs="+", default=["shorts"], choices=["youtube_1080p", "tiktok_reels", "shorts", "square", "discord_720p", "cinematic_4k"])
    batch_parser.add_argument("--versions", type=int, default=2)
    batch_parser.add_argument("-o", "--output-dir", default=None)
    batch_parser.add_argument("--render", action="store_true")
    batch_parser.add_argument("--quality", choices=["preview", "final"], default="preview")
    batch_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    highlight_parser = subparsers.add_parser("highlight-detect", help="Detect highlight candidates, dead moments, motion spikes, and loud reactions.")
    highlight_parser.add_argument("clips_folder")
    highlight_parser.add_argument("--scene-duration", type=float, default=3)
    highlight_parser.add_argument("--max-clips", type=int, default=12)
    highlight_parser.add_argument("-o", "--output", default=None)
    highlight_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    thumbnail_parser = subparsers.add_parser("thumbnail", help="Generate vertical and landscape thumbnail variations.")
    thumbnail_parser.add_argument("video")
    thumbnail_parser.add_argument("--title", required=True)
    thumbnail_parser.add_argument("--accent", default="#ef4444")
    thumbnail_parser.add_argument("-o", "--output-dir", default=None)
    thumbnail_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    suggest_parser = subparsers.add_parser("suggest", help="Suggest overlays, transitions, zooms, SFX, and pacing improvements.")
    suggest_parser.add_argument("project_json")
    suggest_parser.add_argument("-o", "--output", default=None)
    suggest_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    captions_parser = subparsers.add_parser("captions", help="Add transcript captions to a project JSON.")
    captions_parser.add_argument("project_json")
    captions_parser.add_argument("transcript")
    captions_parser.add_argument("--mode", choices=["phrase", "word", "word_by_word", "karaoke", "smart"], default="phrase")
    captions_parser.add_argument("--style", choices=["default", "tiktok", "karaoke"], default="tiktok")
    captions_parser.add_argument("-o", "--output", default=None)
    captions_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    style_parser = subparsers.add_parser("style", help="List or apply named style presets.")
    style_subparsers = style_parser.add_subparsers(dest="style_command", required=True)
    style_subparsers.add_parser("list", help="List style presets.")
    style_apply = style_subparsers.add_parser("apply", help="Apply a style to a project JSON.")
    style_apply.add_argument("project_json")
    style_apply.add_argument("style", choices=list_styles())
    style_apply.add_argument("-o", "--output", default=None)
    style_apply.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    director_parser = subparsers.add_parser("director", help="Run AI Director mode over an existing project.")
    director_parser.add_argument("project_json")
    director_parser.add_argument("goal")
    director_parser.add_argument("-o", "--output", default=None)
    director_parser.add_argument("--preserve", nargs="*", default=[], help="Scene IDs to preserve while rewriting.")
    director_parser.add_argument("--no-history", action="store_true", help="Do not write .ave_history entry.")
    director_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    storyboard_parser = subparsers.add_parser("storyboard", help="Generate a scene-by-scene storyboard with thumbnails.")
    storyboard_parser.add_argument("project_json")
    storyboard_parser.add_argument("-o", "--output-dir", default=None)
    storyboard_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    asset_analyze_parser = subparsers.add_parser("asset-analyze", help="Analyze project assets or a media folder.")
    asset_analyze_parser.add_argument("path")
    asset_analyze_parser.add_argument("-o", "--output", default=None)
    asset_analyze_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    broll_parser = subparsers.add_parser("resolve-broll", help="Resolve b-roll placeholder layers to real assets.")
    broll_parser.add_argument("project_json")
    broll_parser.add_argument("-o", "--output", default=None)
    broll_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    history_parser = subparsers.add_parser("history", help="Inspect or roll back AI edit history.")
    history_subparsers = history_parser.add_subparsers(dest="history_command", required=True)
    history_list = history_subparsers.add_parser("list", help="List saved AI edit versions.")
    history_list.add_argument("project_json")
    history_rollback = history_subparsers.add_parser("rollback", help="Roll back to the old JSON from a version.")
    history_rollback.add_argument("project_json")
    history_rollback.add_argument("version_id")
    history_rollback.add_argument("-o", "--output", default=None)
    history_rollback.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    package_parser = subparsers.add_parser("package", help="Export or open portable project packages.")
    package_subparsers = package_parser.add_subparsers(dest="package_command", required=True)
    package_export = package_subparsers.add_parser("export", help="Export project JSON, assets, reports, and template metadata to a zip.")
    package_export.add_argument("project_json")
    package_export.add_argument("-o", "--output", default=None)
    package_open = package_subparsers.add_parser("open", help="Extract a packaged project zip.")
    package_open.add_argument("package_zip")
    package_open.add_argument("-o", "--output-dir", default=None)
    package_open.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    plugin_parser = subparsers.add_parser("plugin", help="List or create local editor plugins.")
    plugin_subparsers = plugin_parser.add_subparsers(dest="plugin_command", required=True)
    plugin_subparsers.add_parser("list", help="List installed plugins.")
    plugin_init = plugin_subparsers.add_parser("init", help="Create a plugin scaffold.")
    plugin_init.add_argument("name")
    plugin_init.add_argument("type", choices=["transition", "effect", "template", "export_preset", "automation"])
    plugin_subparsers.add_parser("audit", help="Audit local plugin permissions and isolation warnings.")
    plugin_disable = plugin_subparsers.add_parser("disable", help="Disable a local plugin without deleting it.")
    plugin_disable.add_argument("plugin_id")
    plugin_enable = plugin_subparsers.add_parser("enable", help="Enable a previously disabled local plugin.")
    plugin_enable.add_argument("plugin_id")
    plugin_init.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    realtime_parser = subparsers.add_parser("realtime-preview", help="Generate cached frame previews without full render.")
    realtime_parser.add_argument("project_json")
    realtime_parser.add_argument("--time", type=float, default=None)
    realtime_parser.add_argument("--scene", default=None)
    realtime_parser.add_argument("--mode", choices=["draft", "proxy", "balanced", "high", "final_sim"], default="balanced")
    realtime_parser.add_argument("--layers", choices=["all", "text", "media"], default="all")
    realtime_parser.add_argument("-o", "--output-dir", default=None)
    realtime_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    interactive_preview_parser = subparsers.add_parser("interactive-preview", help="Generate a cached playable preview package before final export.")
    interactive_preview_parser.add_argument("project_json")
    interactive_preview_parser.add_argument("--quality-mode", choices=["draft", "proxy", "balanced", "high", "final_sim"], default="balanced")
    interactive_preview_parser.add_argument("--scope", choices=["full", "scene"], default="full")
    interactive_preview_parser.add_argument("--scene-id", default=None)
    interactive_preview_parser.add_argument("-o", "--output-dir", default=None)
    interactive_preview_parser.add_argument("--generate-placeholders", action="store_true")
    interactive_preview_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    template_pack_parser = subparsers.add_parser("template-pack", help="List, export, or install local template packs.")
    template_pack_subparsers = template_pack_parser.add_subparsers(dest="template_pack_command", required=True)
    template_pack_subparsers.add_parser("list", help="List bundled local templates.")
    template_pack_export = template_pack_subparsers.add_parser("export", help="Export a template pack zip.")
    template_pack_export.add_argument("template", choices=template_names())
    template_pack_export.add_argument("-o", "--output", default=None)
    template_pack_install = template_pack_subparsers.add_parser("install", help="Install a template pack zip.")
    template_pack_install.add_argument("package_zip")
    template_pack_install.add_argument("-o", "--output-dir", default=None)
    template_pack_install.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    brand_parser = subparsers.add_parser("brand", help="Create or apply brand kits.")
    brand_subparsers = brand_parser.add_subparsers(dest="brand_command", required=True)
    brand_init = brand_subparsers.add_parser("init", help="Create a brand kit JSON.")
    brand_init.add_argument("-o", "--output", default=None)
    brand_apply = brand_subparsers.add_parser("apply", help="Apply a brand kit to a project.")
    brand_apply.add_argument("project_json")
    brand_apply.add_argument("brand_kit")
    brand_apply.add_argument("-o", "--output", default=None)
    brand_apply.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    manifest_parser = subparsers.add_parser("manifest", help="Generate collaboration manifest and portability checks.")
    manifest_parser.add_argument("project_json")
    manifest_parser.add_argument("-o", "--output", default=None)
    manifest_parser.add_argument("--check-only", action="store_true")
    manifest_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    quality_parser = subparsers.add_parser("quality-check", help="Run pre-render quality checks.")
    quality_parser.add_argument("project_json")
    quality_parser.add_argument("-o", "--output", default=None)
    quality_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    preflight_parser = subparsers.add_parser("final-preflight", help="Inspect approved preview and final export readiness.")
    preflight_subparsers = preflight_parser.add_subparsers(dest="preflight_command", required=True)
    preflight_check = preflight_subparsers.add_parser("check", help="Run final preflight checks.")
    preflight_check.add_argument("project_json")
    preflight_check.add_argument("--preview-video", default=None)
    preflight_check.add_argument("--format", choices=["mp4", "mov", "mkv", "webm", "gif", "image_sequence"], default="mp4")
    preflight_check.add_argument("-o", "--output", default=None)
    preflight_check.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    preflight_repair = preflight_subparsers.add_parser("repair", help="Apply safe final preflight repairs or accept an issue.")
    preflight_repair.add_argument("project_json")
    preflight_repair.add_argument("-o", "--output", required=True)
    preflight_repair.add_argument("--preview-video", default=None)
    preflight_repair.add_argument("--format", choices=["mp4", "mov", "mkv", "webm", "gif", "image_sequence"], default="mp4")
    preflight_repair.add_argument("--mode", choices=["all", "selected", "ignore", "accept"], default="all")
    preflight_repair.add_argument("--issue-id", default=None)
    preflight_repair.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    reformat_parser = subparsers.add_parser("reformat", help="Create social-platform JSON variants.")
    reformat_parser.add_argument("project_json")
    reformat_parser.add_argument(
        "--targets",
        nargs="+",
        default=["all"],
        choices=["all", "youtube", "youtube_landscape", "youtube_shorts", "tiktok", "instagram_reels", "instagram_square", "shorts", "discord", "x_twitter"],
    )
    reformat_parser.add_argument("-o", "--output-dir", default=None)
    reformat_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    recovery_parser = subparsers.add_parser("recovery", help="Autosave, backup, list, and restore recovery points.")
    recovery_subparsers = recovery_parser.add_subparsers(dest="recovery_command", required=True)
    recovery_auto = recovery_subparsers.add_parser("autosave", help="Write an autosave copy of a project.")
    recovery_auto.add_argument("project_json")
    recovery_backup = recovery_subparsers.add_parser("backup", help="Write a backup copy of a project.")
    recovery_backup.add_argument("project_json")
    recovery_list = recovery_subparsers.add_parser("list", help="List recovery points.")
    recovery_list.add_argument("project_json")
    recovery_restore = recovery_subparsers.add_parser("restore", help="Restore a recovery point.")
    recovery_restore.add_argument("source")
    recovery_restore.add_argument("target")
    recovery_restore_point = recovery_subparsers.add_parser("restore-point", help="Create a named manual restore point.")
    recovery_restore_point.add_argument("project_json")
    recovery_restore_point.add_argument("--label", default="manual")
    recovery_cleanup = recovery_subparsers.add_parser("cleanup", help="Delete old autosaves, backups, and restore points.")
    recovery_cleanup.add_argument("project_json")
    recovery_cleanup.add_argument("--keep", type=int, default=12)
    recovery_recover = recovery_subparsers.add_parser("recover-corrupt", help="Recover a corrupted project using repair or latest recovery point.")
    recovery_recover.add_argument("project_json")
    recovery_recover.add_argument("-o", "--output", default=None)
    recovery_integrity = recovery_subparsers.add_parser("integrity", help="Check schema, timeline, and asset integrity.")
    recovery_integrity.add_argument("project_json")
    recovery_integrity.add_argument("-o", "--output", default=None)
    recovery_relink = recovery_subparsers.add_parser("relink", help="Relink missing assets by filename from a folder.")
    recovery_relink.add_argument("project_json")
    recovery_relink.add_argument("search_folder")
    recovery_relink.add_argument("-o", "--output", default=None)
    recovery_restore.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    profile_parser = subparsers.add_parser("profile", help="Manage reusable local creator profiles.")
    profile_subparsers = profile_parser.add_subparsers(dest="profile_command", required=True)
    profile_subparsers.add_parser("list", help="List creator profiles.")
    profile_create = profile_subparsers.add_parser("create", help="Create a creator profile JSON.")
    profile_create.add_argument("name")
    profile_create.add_argument("-o", "--output", default=None)
    profile_show = profile_subparsers.add_parser("show", help="Show a creator profile.")
    profile_show.add_argument("name_or_path")
    profile_apply = profile_subparsers.add_parser("apply", help="Apply creator workflow defaults to a project JSON.")
    profile_apply.add_argument("project_json")
    profile_apply.add_argument("name_or_path")
    profile_apply.add_argument("-o", "--output", default=None)

    automation_parser = subparsers.add_parser("automation", help="Run local watch-folder or render-queue hooks.")
    automation_subparsers = automation_parser.add_subparsers(dest="automation_command", required=True)
    automation_watch = automation_subparsers.add_parser("watch", help="Render changed JSON projects in a local folder.")
    automation_watch.add_argument("watch_dir")
    automation_watch.add_argument("-o", "--output-dir", default=None)
    automation_watch.add_argument("--loop", action="store_true")
    automation_watch.add_argument("--poll", type=float, default=2)
    automation_watch.add_argument("--quality", choices=["preview", "final"], default="preview")
    automation_queue = automation_subparsers.add_parser("queue", help="Render all JSON projects in a local queue folder.")
    automation_queue.add_argument("queue_dir")
    automation_queue.add_argument("-o", "--output-dir", default=None)
    automation_queue.add_argument("--quality", choices=["preview", "final"], default="preview")

    metrics_parser = subparsers.add_parser("metrics", help="Summarize local-only generation and render metrics.")
    metrics_subparsers = metrics_parser.add_subparsers(dest="metrics_command", required=True)
    metrics_summary = metrics_subparsers.add_parser("summary", help="Write metrics summary JSON.")
    metrics_summary.add_argument("-o", "--output", default=None)

    cinematic_parser = subparsers.add_parser("cinematic-enhance", help="Apply cinematic camera, graphics, post, and audio enhancements to project JSON.")
    cinematic_parser.add_argument("project_json")
    cinematic_parser.add_argument("--preset", default="cinematic_polish", choices=list_cinematic_presets())
    cinematic_parser.add_argument("-o", "--output", default=None)
    cinematic_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    effect_graph_parser = subparsers.add_parser("effect-graph", help="List effect graph presets.")
    effect_graph_subparsers = effect_graph_parser.add_subparsers(dest="effect_graph_command", required=True)
    effect_graph_subparsers.add_parser("list", help="List built-in effect graph presets.")
    effect_graph_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    understand_parser = subparsers.add_parser("understand-clip", help="Analyze clips for action, scene changes, faces, readability, and motion direction.")
    understand_parser.add_argument("path")
    understand_parser.add_argument("-o", "--output", default=None)
    understand_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    audio_intel_parser = subparsers.add_parser("audio-intel", help="Analyze audio for mix, ducking, limiter, bass-hit, and beat-sync recommendations.")
    audio_intel_parser.add_argument("audio")
    audio_intel_parser.add_argument("-o", "--output", default=None)
    audio_intel_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    scene_build_parser = subparsers.add_parser("scene-build", help="Build a renderable cinematic sequence from a plain English scene request.")
    scene_build_parser.add_argument("prompt")
    scene_build_parser.add_argument("--duration", type=float, default=8)
    scene_build_parser.add_argument("--preset", default="shorts", choices=["youtube_1080p", "tiktok_reels", "shorts", "square", "discord_720p", "cinematic_4k"])
    scene_build_parser.add_argument("--style", default="red_black_aegis", choices=list_styles())
    scene_build_parser.add_argument("-o", "--output", default=None)
    scene_build_parser.add_argument("--render", action="store_true")
    scene_build_parser.add_argument("--quality", choices=["preview", "final"], default="preview")
    scene_build_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    project_analyze_parser = subparsers.add_parser("project-analyze", help="Analyze pacing, loudness, captions, transitions, effects, and boring sections.")
    project_analyze_parser.add_argument("project_json")
    project_analyze_parser.add_argument("--rendered-video", default=None)
    project_analyze_parser.add_argument("-o", "--output", default=None)
    project_analyze_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    workspace_parser = subparsers.add_parser("workspace", help="Manage local multi-project workspace state and layouts.")
    workspace_subparsers = workspace_parser.add_subparsers(dest="workspace_command", required=True)
    workspace_init = workspace_subparsers.add_parser("init", help="Create a workspace JSON.")
    workspace_init.add_argument("name")
    workspace_init.add_argument("-o", "--output", default=None)
    workspace_subparsers.add_parser("list", help="List saved workspaces.")
    workspace_show = workspace_subparsers.add_parser("show", help="Show workspace JSON summary.")
    workspace_show.add_argument("workspace")
    workspace_open = workspace_subparsers.add_parser("open", help="Open a project in a workspace.")
    workspace_open.add_argument("workspace")
    workspace_open.add_argument("project_json")
    workspace_close = workspace_subparsers.add_parser("close", help="Close a project in a workspace.")
    workspace_close.add_argument("workspace")
    workspace_close.add_argument("project_json")
    workspace_layout = workspace_subparsers.add_parser("layout", help="Save a preset or JSON layout in a workspace.")
    workspace_layout.add_argument("workspace")
    workspace_layout.add_argument("--preset", choices=["editing", "review", "advanced"], default="editing")
    workspace_layout.add_argument("--layout-json", default=None)
    workspace_profile = workspace_subparsers.add_parser("profile", help="Add or list local workspace profiles.")
    workspace_profile.add_argument("workspace")
    workspace_profile.add_argument("--add", default=None)
    workspace_profile.add_argument("--settings-json", default=None)

    review_parser = subparsers.add_parser("review", help="Local review notes, markers, approvals, asset locks, and roles.")
    review_subparsers = review_parser.add_subparsers(dest="review_command", required=True)
    review_show = review_subparsers.add_parser("show", help="Show review state.")
    review_show.add_argument("project_json")
    review_comment = review_subparsers.add_parser("comment", help="Add a scene comment.")
    review_comment.add_argument("project_json")
    review_comment.add_argument("scene_id")
    review_comment.add_argument("body")
    review_comment.add_argument("--author", default="local_user")
    review_comment.add_argument("--time", type=float, default=None)
    review_marker = review_subparsers.add_parser("marker", help="Add a timeline review marker.")
    review_marker.add_argument("project_json")
    review_marker.add_argument("scene_id")
    review_marker.add_argument("type", choices=["needs_cut", "too_slow", "too_fast", "bad_caption", "bad_zoom", "bad_transition", "audio_issue", "keep"])
    review_marker.add_argument("--time", type=float, required=True)
    review_marker.add_argument("--note", default="")
    review_marker.add_argument("--author", default="local_user")
    review_approve = review_subparsers.add_parser("approve", help="Set scene approval status.")
    review_approve.add_argument("project_json")
    review_approve.add_argument("scene_id")
    review_approve.add_argument("status", choices=["needs_review", "approved", "locked", "regenerated", "excluded"])
    review_lock = review_subparsers.add_parser("lock-asset", help="Lock an asset for local review/edit ownership.")
    review_lock.add_argument("project_json")
    review_lock.add_argument("asset")
    review_lock.add_argument("--owner", default="local_user")
    review_lock.add_argument("--reason", default="")
    review_role = review_subparsers.add_parser("role", help="Assign a local editor role.")
    review_role.add_argument("project_json")
    review_role.add_argument("user")
    review_role.add_argument("role", choices=["owner", "editor", "reviewer", "viewer"])
    review_report = review_subparsers.add_parser("report", help="Export a local review report.")
    review_report.add_argument("project_json")
    review_report.add_argument("-o", "--output", default=None)
    review_compare = review_subparsers.add_parser("compare", help="Compare two project JSON files side by side.")
    review_compare.add_argument("left_project_json")
    review_compare.add_argument("right_project_json")
    review_compare.add_argument("-o", "--output", default=None)

    asset_db_parser = subparsers.add_parser("asset-db", help="Index, search, and report on the local SQLite asset database.")
    asset_db_subparsers = asset_db_parser.add_subparsers(dest="asset_db_command", required=True)
    asset_db_index = asset_db_subparsers.add_parser("index", help="Index a media folder.")
    asset_db_index.add_argument("folder")
    asset_db_index.add_argument("--no-previews", action="store_true")
    asset_db_search = asset_db_subparsers.add_parser("search", help="Search indexed assets.")
    asset_db_search.add_argument("query", nargs="?", default="")
    asset_db_search.add_argument("--type", choices=["clip", "image", "music", "sound_effect", "template", "effect", "caption", "thumbnail", "creator_profile", "brand_kit"], default=None)
    asset_db_search.add_argument("--category", default=None)
    asset_db_search.add_argument("--limit", type=int, default=20)
    asset_db_subparsers.add_parser("duplicates", help="Find duplicate indexed assets.")
    asset_db_usage = asset_db_subparsers.add_parser("usage", help="Track asset usage from a project JSON.")
    asset_db_usage.add_argument("project_json")
    asset_db_report = asset_db_subparsers.add_parser("report", help="Write an asset database report.")
    asset_db_report.add_argument("-o", "--output", default=None)

    pack_parser = subparsers.add_parser("pack", help="Import/export offline ecosystem packs.")
    pack_subparsers = pack_parser.add_subparsers(dest="pack_command", required=True)
    pack_export = pack_subparsers.add_parser("export", help="Export a local pack.")
    pack_export.add_argument("source")
    pack_export.add_argument("--type", required=True, choices=["template", "effect", "transition", "creator", "brandkit", "caption", "motion", "export_preset", "automation"])
    pack_export.add_argument("--name", default=None)
    pack_export.add_argument("--author", default="local")
    pack_export.add_argument("-o", "--output", default=None)
    pack_import = pack_subparsers.add_parser("import", help="Install a local pack.")
    pack_import.add_argument("package")
    pack_import.add_argument("-o", "--output-dir", default=None)
    pack_subparsers.add_parser("list", help="List installed packs.")

    dataset_parser = subparsers.add_parser("dataset-export", help="Export anonymized local edit decisions for future local AI fine-tuning.")
    dataset_parser.add_argument("projects", nargs="+")
    dataset_parser.add_argument("-o", "--output", default=None)
    dataset_parser.add_argument("--include-text", action="store_true")

    analytics_parser = subparsers.add_parser("analytics", help="Summarize local creator workflow analytics.")
    analytics_subparsers = analytics_parser.add_subparsers(dest="analytics_command", required=True)
    analytics_summary = analytics_subparsers.add_parser("summary", help="Write creator analytics.")
    analytics_summary.add_argument("-o", "--output", default=None)

    api_parser = subparsers.add_parser("api", help="Describe the local SDK/API surface and engine split.")
    api_subparsers = api_parser.add_subparsers(dest="api_command", required=True)
    api_subparsers.add_parser("describe", help="Describe stable API commands and engines.")
    api_subparsers.add_parser("engines", help="Describe engine registry.")

    local_policy_parser = subparsers.add_parser("local-policy", help="Create or show the local-first platform policy.")
    local_policy_subparsers = local_policy_parser.add_subparsers(dest="local_policy_command", required=True)
    local_policy_init = local_policy_subparsers.add_parser("init", help="Create local-first policy JSON.")
    local_policy_init.add_argument("-o", "--output", default=None)
    local_policy_show = local_policy_subparsers.add_parser("show", help="Show local-first policy JSON.")
    local_policy_show.add_argument("--path", default=None)

    diagnostics_parser = subparsers.add_parser("diagnostics", help="Run local stability diagnostics or repair a project.")
    diagnostics_subparsers = diagnostics_parser.add_subparsers(dest="diagnostics_command", required=True)
    diagnostics_run = diagnostics_subparsers.add_parser("run", help="Run diagnostics.")
    diagnostics_run.add_argument("project_json", nargs="?")
    diagnostics_run.add_argument("-o", "--output", default=None)
    diagnostics_repair = diagnostics_subparsers.add_parser("repair", help="Repair a corrupted/invalid project JSON.")
    diagnostics_repair.add_argument("project_json")
    diagnostics_repair.add_argument("-o", "--output", required=True)

    worker_parser = subparsers.add_parser("worker", help="Run same-machine local render workers.")
    worker_subparsers = worker_parser.add_subparsers(dest="worker_command", required=True)
    worker_enqueue = worker_subparsers.add_parser("enqueue", help="Queue a local render job.")
    worker_enqueue.add_argument("project_json")
    worker_enqueue.add_argument("-o", "--output", default=None)
    worker_enqueue.add_argument("--queue-dir", default=None)
    worker_enqueue.add_argument("--quality", choices=["preview", "final"], default="preview")
    worker_run = worker_subparsers.add_parser("run", help="Run queued local render jobs.")
    worker_run.add_argument("--queue-dir", default=None)
    worker_run.add_argument("--loop", action="store_true")
    worker_run.add_argument("--timeout", type=float, default=1800)
    worker_status_parser = worker_subparsers.add_parser("status", help="Show local render worker status.")
    worker_status_parser.add_argument("--queue-dir", default=None)

    workflow_parser = subparsers.add_parser("workflow", help="Creator workflow automation: profiles, reusable pipelines, batch generation, local tasks, memory, and dashboard.")
    workflow_subparsers = workflow_parser.add_subparsers(dest="workflow_command", required=True)
    workflow_profile = workflow_subparsers.add_parser("profile", help="Create a richer reusable creator profile.")
    workflow_profile.add_argument("name")
    workflow_profile.add_argument("-o", "--output", default=None)
    workflow_pipeline_create = workflow_subparsers.add_parser("pipeline-create", help="Save a reusable content pipeline recipe.")
    workflow_pipeline_create.add_argument("name")
    workflow_pipeline_create.add_argument("--preset", default="youtube_short_product_showcase", choices=["youtube_short_product_showcase", "cybersecurity_tool_demo", "gaming_montage", "minimal_saas_promo"])
    workflow_pipeline_create.add_argument("--profile", default=None)
    workflow_pipeline_create.add_argument("--mode", default=None, choices=["youtube_shorts", "tiktok", "product_showcase", "tutorial", "promo_ad"])
    workflow_pipeline_create.add_argument("--tone", default=None, choices=["minimal", "cinematic", "aggressive", "clean"])
    workflow_pipeline_create.add_argument("--style", default=None, choices=["auto", *list_styles()])
    workflow_pipeline_create.add_argument("--duration", type=float, default=None)
    workflow_pipeline_create.add_argument("-o", "--output", default=None)
    workflow_subparsers.add_parser("pipeline-list", help="List saved workflow pipelines.")
    workflow_pipeline_show = workflow_subparsers.add_parser("pipeline-show", help="Show a workflow pipeline JSON.")
    workflow_pipeline_show.add_argument("name_or_path")
    workflow_batch = workflow_subparsers.add_parser("batch", help="Generate multiple local content variants from a saved workflow.")
    workflow_batch.add_argument("workflow")
    workflow_batch.add_argument("idea")
    workflow_batch.add_argument("--assets", default=None)
    workflow_batch.add_argument("--music", default=None)
    workflow_batch.add_argument("--logo", default=None)
    workflow_batch.add_argument("--versions", type=int, default=3)
    workflow_batch.add_argument("-o", "--output-dir", default=None)
    workflow_batch.add_argument("--render", action="store_true")
    workflow_batch.add_argument("--quality", choices=["preview", "final"], default="preview")
    workflow_task_create = workflow_subparsers.add_parser("task-create", help="Create a local scheduled task manifest.")
    workflow_task_create.add_argument("name")
    workflow_task_create.add_argument("type", choices=["render_queue", "asset_index", "proxy_generation", "cache_cleanup", "custom"])
    workflow_task_create.add_argument("--run-at", default="overnight", choices=["overnight", "now", "once", "hourly"])
    workflow_task_create.add_argument("--priority", type=int, default=0)
    workflow_task_create.add_argument("--cmd", default=None, help="Quoted local render.py command arguments, for example \"cache cleanup --max-gb 4 --dry-run\".")
    workflow_task_create.add_argument("task_args", nargs="*", help="Simple local render.py command arguments to run when due.")
    workflow_subparsers.add_parser("task-list", help="List scheduled local task manifests.")
    workflow_task_run = workflow_subparsers.add_parser("task-run", help="Run due local tasks.")
    workflow_task_run.add_argument("--force", action="store_true")
    workflow_task_run.add_argument("--limit", type=int, default=5)
    workflow_memory_update = workflow_subparsers.add_parser("memory-update", help="Add local creator memory from an approved project or plan.")
    workflow_memory_update.add_argument("profile")
    workflow_memory_update.add_argument("--project", default=None)
    workflow_memory_update.add_argument("--plan", default=None)
    workflow_memory_update.add_argument("--rating", default=None)
    workflow_memory_update.add_argument("--note", default=None)
    workflow_memory_update.add_argument("--prefer", action="append", default=[], help="Manual preference key=value. May be repeated.")
    workflow_memory_show = workflow_subparsers.add_parser("memory-show", help="Show local creator memory.")
    workflow_memory_show.add_argument("--profile", default=None)
    workflow_reuse = workflow_subparsers.add_parser("asset-reuse", help="Report asset reuse, hooks, transitions, and creator preferences.")
    workflow_reuse.add_argument("--project", default=None)
    workflow_reuse.add_argument("-o", "--output", default=None)
    workflow_dashboard = workflow_subparsers.add_parser("dashboard", help="Write the local production dashboard.")
    workflow_dashboard.add_argument("--project", default=None)
    workflow_dashboard.add_argument("-o", "--output", default=None)

    feedback_parser = subparsers.add_parser("feedback", help="Local quality feedback loops, creator identity learning, and review datasets.")
    feedback_subparsers = feedback_parser.add_subparsers(dest="feedback_command", required=True)
    feedback_review = feedback_subparsers.add_parser("review", help="Record a post-render creator review and quality scores.")
    feedback_review.add_argument("project_json")
    feedback_review.add_argument("--video", default=None)
    feedback_review.add_argument("--plan", default=None)
    feedback_review.add_argument("--profile", default="Default Creator")
    feedback_review.add_argument("--note", default=None)
    feedback_review.add_argument("--pacing", type=int, default=None)
    feedback_review.add_argument("--readability", type=int, default=None)
    feedback_review.add_argument("--transitions", type=int, default=None)
    feedback_review.add_argument("--cinematic", type=int, default=None)
    feedback_review.add_argument("--hook", type=int, default=None)
    feedback_review.add_argument("--captions", type=int, default=None)
    feedback_review.add_argument("--polish", type=int, default=None)
    feedback_review.add_argument("-o", "--output", default=None)
    feedback_analyze = feedback_subparsers.add_parser("analyze", help="Run render self-analysis for pacing, captions, transitions, motion, artifacts, and readability.")
    feedback_analyze.add_argument("project_json")
    feedback_analyze.add_argument("--video", default=None)
    feedback_analyze.add_argument("-o", "--output", default=None)
    feedback_consistency = feedback_subparsers.add_parser("consistency", help="Score style consistency against a creator profile.")
    feedback_consistency.add_argument("project_json")
    feedback_consistency.add_argument("--profile", default=None)
    feedback_consistency.add_argument("--profile-path", default=None)
    feedback_consistency.add_argument("-o", "--output", default=None)
    feedback_hook = feedback_subparsers.add_parser("hook", help="Estimate hook strength, readability speed, and retention potential.")
    feedback_hook.add_argument("--project", default=None)
    feedback_hook.add_argument("--plan", default=None)
    feedback_hook.add_argument("-o", "--output", default=None)
    feedback_ai = feedback_subparsers.add_parser("ai-event", help="Record AI improvement signals such as regenerated scenes or removed transitions.")
    feedback_ai.add_argument("profile")
    feedback_ai.add_argument("--project", default=None)
    feedback_ai.add_argument("--scene-regenerated", action="append", default=[])
    feedback_ai.add_argument("--transition-removed", action="append", default=[])
    feedback_ai.add_argument("--caption-edited", action="append", default=[])
    feedback_ai.add_argument("--section-locked", action="append", default=[])
    feedback_ai.add_argument("--note", default=None)
    feedback_ai.add_argument("-o", "--output", default=None)
    feedback_learn = feedback_subparsers.add_parser("learn", help="Build or refresh a local creator identity preference model.")
    feedback_learn.add_argument("profile")
    feedback_learn.add_argument("-o", "--output", default=None)
    feedback_identity = feedback_subparsers.add_parser("identity", help="Show a local creator identity model.")
    feedback_identity.add_argument("profile")
    feedback_identity.add_argument("-o", "--output", default=None)
    feedback_dataset = feedback_subparsers.add_parser("dataset", help="Export a local-only training dataset from approved edits.")
    feedback_dataset.add_argument("profile")
    feedback_dataset.add_argument("-o", "--output-dir", required=True)
    feedback_dataset.add_argument("--min-rating", type=float, default=4.0)

    evolution_parser = subparsers.add_parser("evolution-report", help="Write the local-first long-term evolution and controlled-expansion report.")
    evolution_parser.add_argument("--project", default=None)
    evolution_parser.add_argument("--profile", default="Default Creator")
    evolution_parser.add_argument("--include-release-check", action="store_true")
    evolution_parser.add_argument("-o", "--output", default=None)

    local_ai_parser = subparsers.add_parser("local-ai", help="Run local-only AI helpers.")
    local_ai_subparsers = local_ai_parser.add_subparsers(dest="local_ai_command", required=True)
    local_ai_subparsers.add_parser("status", help="Check local AI integrations.")
    local_ai_prompt = local_ai_subparsers.add_parser("prompt-json", help="Generate JSON from a prompt using the local prompt interpreter.")
    local_ai_prompt.add_argument("prompt")
    local_ai_prompt.add_argument("-o", "--output", default=None)
    local_ai_prompt.add_argument("--template", default=None, choices=[None, *template_names()])
    local_ai_prompt.add_argument("--preset", default=None)
    local_ai_repair = local_ai_subparsers.add_parser("repair", help="Repair project JSON locally.")
    local_ai_repair.add_argument("project_json")
    local_ai_repair.add_argument("-o", "--output", required=True)
    local_ai_suggest = local_ai_subparsers.add_parser("suggest", help="Generate local scene suggestions.")
    local_ai_suggest.add_argument("project_json")
    local_ai_suggest.add_argument("-o", "--output", default=None)
    local_ai_captions = local_ai_subparsers.add_parser("captions", help="Generate captions from a transcript locally.")
    local_ai_captions.add_argument("project_json")
    local_ai_captions.add_argument("transcript")
    local_ai_captions.add_argument("-o", "--output", required=True)
    local_ai_captions.add_argument("--mode", default="smart", choices=["phrase", "word", "word_by_word", "karaoke", "smart"])
    local_ai_captions.add_argument("--style", default="tiktok", choices=["default", "tiktok", "karaoke"])
    local_ai_transcribe = local_ai_subparsers.add_parser("transcribe", help="Run local Whisper CLI transcription when installed.")
    local_ai_transcribe.add_argument("audio")
    local_ai_transcribe.add_argument("-o", "--output", required=True)

    model_parser = subparsers.add_parser("model-manager", help="Detect, health-check, and select local AI models.")
    model_subparsers = model_parser.add_subparsers(dest="model_command", required=True)
    model_status = model_subparsers.add_parser("status", help="Write local model health status.")
    model_status.add_argument("-o", "--output", default=None)
    model_select = model_subparsers.add_parser("select", help="Select a local model for a task.")
    model_select.add_argument("task", choices=["prompt_to_json", "json_repair", "scene_suggestions", "captions", "transcription"])
    model_select.add_argument("model")

    dependency_parser = subparsers.add_parser("dependency-check", help="Check offline dependencies, codecs, storage, memory, and GPU encoders.")
    dependency_parser.add_argument("-o", "--output", default=None)

    installer_parser = subparsers.add_parser("installer", help="Prepare local installer assets and portable builds.")
    installer_subparsers = installer_parser.add_subparsers(dest="installer_command", required=True)
    installer_prepare = installer_subparsers.add_parser("prepare", help="Create local app folders and first-run setup JSON.")
    installer_prepare.add_argument("--base-dir", default=None)
    installer_prepare.add_argument("-o", "--output", default=None)
    installer_manifest = installer_subparsers.add_parser("manifest", help="Create a Windows installer manifest.")
    installer_manifest.add_argument("--bundled-ffmpeg", default=None)
    installer_manifest.add_argument("-o", "--output", default=None)
    installer_portable = installer_subparsers.add_parser("portable", help="Create a portable ZIP package.")
    installer_portable.add_argument("-o", "--output", default=None)

    privacy_parser = subparsers.add_parser("privacy-report", help="Write local-first privacy and plugin safety report.")
    privacy_parser.add_argument("-o", "--output", default=None)

    reliable_parser = subparsers.add_parser("reliable-render", help="Render with retry, crash-safe partial files, logs, and cache resume.")
    reliable_parser.add_argument("project_json")
    reliable_parser.add_argument("-o", "--output", default=None)
    reliable_parser.add_argument("--attempts", type=int, default=2)
    reliable_parser.add_argument("--quality", choices=["preview", "final"], default="final")
    reliable_parser.add_argument("--cache", action="store_true", default=True)
    reliable_parser.add_argument("--no-cache", action="store_false", dest="cache")
    reliable_parser.add_argument("--resume", action="store_true", default=True)
    reliable_parser.add_argument("--no-resume", action="store_false", dest="resume")
    reliable_parser.add_argument("--gpu", action="store_true")

    performance_parser = subparsers.add_parser("performance-report", help="Write local performance dashboard data.")
    performance_parser.add_argument("-o", "--output", default=None)

    docs_parser = subparsers.add_parser("docs", help="List or show bundled local documentation.")
    docs_subparsers = docs_parser.add_subparsers(dest="docs_command", required=True)
    docs_subparsers.add_parser("list", help="List bundled docs.")
    docs_show = docs_subparsers.add_parser("show", help="Print a bundled doc.")
    docs_show.add_argument("key", choices=["json", "templates", "plugins", "troubleshooting", "ffmpeg", "foundation", "charter", "local-ai", "developer", "plugin-api", "schema", "mvp", "content-generator", "content-review", "posting-package", "workflow-automation", "quality-feedback", "long-term-evolution", "beginner-auto-template", "media-compatibility", "interactive-preview", "preview-review", "final-preflight", "shorts", "beginner", "advanced", "advanced-systems", "release", "changelog", "showcase"])

    refine_parser = subparsers.add_parser("refine", help="Apply Phase 11 cinematic workflow refinement to a project.")
    refine_parser.add_argument("project_json")
    refine_parser.add_argument("--preset", choices=list_polish_presets(), default="clean_cinematic")
    refine_parser.add_argument("-o", "--output", default=None)
    refine_parser.add_argument("--render", action="store_true")
    refine_parser.add_argument("--quality", choices=["preview", "final"], default="preview")

    color_parser = subparsers.add_parser("color", help="List or apply cinematic color pipeline presets and LUTs.")
    color_subparsers = color_parser.add_subparsers(dest="color_command", required=True)
    color_subparsers.add_parser("list", help="List color presets.")
    color_subparsers.add_parser("luts", help="List local LUT files.")
    color_apply = color_subparsers.add_parser("apply", help="Apply a color preset to project JSON.")
    color_apply.add_argument("project_json")
    color_apply.add_argument("preset", choices=[item["key"] for item in list_color_presets()])
    color_apply.add_argument("--lut", default=None)
    color_apply.add_argument("-o", "--output", default=None)

    advanced_parser = subparsers.add_parser("advanced", help="Apply advanced cinematic systems to an existing project JSON.")
    advanced_parser.add_argument("project_json")
    advanced_parser.add_argument("-o", "--output", default=None)
    advanced_parser.add_argument("--report", default=None, help="Advanced systems report output path.")

    cache_parser = subparsers.add_parser("cache", help="Report or clean local preview/proxy/render caches.")
    cache_subparsers = cache_parser.add_subparsers(dest="cache_command", required=True)
    cache_report_parser = cache_subparsers.add_parser("report", help="Write cache usage report.")
    cache_report_parser.add_argument("--root", default=None)
    cache_report_parser.add_argument("-o", "--output", default=None)
    cache_cleanup_parser = cache_subparsers.add_parser("cleanup", help="Delete oldest cache buckets until under size limit.")
    cache_cleanup_parser.add_argument("--root", default=None)
    cache_cleanup_parser.add_argument("--max-gb", type=float, default=5)
    cache_cleanup_parser.add_argument("--dry-run", action="store_true")

    demo_parser = subparsers.add_parser("demo", help="List built-in polished demo projects.")
    demo_subparsers = demo_parser.add_subparsers(dest="demo_command", required=True)
    demo_subparsers.add_parser("list", help="List bundled demos.")

    architecture_parser = subparsers.add_parser("architecture-audit", help="Audit architecture, docs, plugin warnings, and technical debt hotspots.")
    architecture_parser.add_argument("-o", "--output", default=None)

    profile_run_parser = subparsers.add_parser("profile-run", help="Profile parse, preview, asset analysis, AI generation, thumbnails, and optional render.")
    profile_run_parser.add_argument("project_json")
    profile_run_parser.add_argument("-o", "--output", default=None)
    profile_run_parser.add_argument("--include-render", action="store_true")

    release_parser = subparsers.add_parser("release-check", help="Run release-candidate readiness checks.")
    release_parser.add_argument("-o", "--output", default=None)
    release_parser.add_argument("--include-render-profile", action="store_true")

    showcase_parser = subparsers.add_parser("showcase", help="Create a cinematic product showcase from a raw desktop recording.")
    showcase_parser.add_argument("recording", nargs="?", help="Raw desktop recording video file.")
    showcase_parser.add_argument("--music", default=None, help="Optional music track for beat-reactive editing.")
    showcase_parser.add_argument("--logo", default=None, help="Optional logo/branding image.")
    showcase_parser.add_argument("--style", default="auto", help="Showcase preset or 'auto'.")
    showcase_parser.add_argument("--style-profile", default=None, help="JSON style profile path or inline JSON.")
    showcase_parser.add_argument("--overrides", default=None, help="Manual override JSON path or inline JSON with mustShow/cutOut/style/duration/musicSync.")
    showcase_parser.add_argument("--instructions", default="", help="Local AI Director-style instructions for tone and focus.")
    showcase_parser.add_argument("--product-name", default=None)
    showcase_parser.add_argument("--duration", type=float, default=None)
    showcase_parser.add_argument("-o", "--output", default=None, help="Project JSON output path.")
    showcase_parser.add_argument("--analysis-output", default=None, help="Desktop analysis JSON output path.")
    showcase_parser.add_argument("--spec-output", default=None, help="Structured showcase specification JSON output path.")
    showcase_parser.add_argument("--score-output", default=None, help="Showcase readiness score JSON output path.")
    showcase_parser.add_argument("--advanced-output", default=None, help="Advanced cinematic intelligence report output path.")
    showcase_parser.add_argument("--render", action="store_true", help="Render the generated showcase project.")
    showcase_parser.add_argument("--render-output", default=None, help="Rendered MP4 output path.")
    showcase_parser.add_argument("--quality", choices=["preview", "final"], default="preview")
    showcase_parser.add_argument("--cache", action="store_true")
    showcase_parser.add_argument("--gpu", action="store_true")
    showcase_parser.add_argument("--list-styles", action="store_true")
    showcase_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    return parser


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

    if args.command == "render":
        return _cmd_render(args)
    if args.command == "validate":
        return _cmd_validate(args)
    if args.command == "preview":
        return _cmd_preview(args)
    if args.command == "quick-create":
        return _cmd_quick_create(args)
    if args.command == "foundation-pass":
        return _cmd_foundation_pass(args)
    if args.command == "repair":
        return _cmd_repair(args)
    if args.command == "template":
        return _cmd_template(args)
    if args.command == "ai-generate":
        return _cmd_ai_generate(args)
    if args.command == "preset":
        return _cmd_preset(args)
    if args.command == "analyze-audio":
        return _cmd_analyze_audio(args)
    if args.command == "beat-sync":
        return _cmd_beat_sync(args)
    if args.command == "auto-select":
        return _cmd_auto_select(args)
    if args.command == "smart-build":
        return _cmd_smart_build(args)
    if args.command == "pipeline":
        return _cmd_pipeline(args)
    if args.command == "autonomous":
        return _cmd_autonomous(args)
    if args.command == "youtube-short":
        return _cmd_youtube_short(args)
    if args.command == "content-generate":
        return _cmd_content_generate(args)
    if args.command == "auto-template":
        return _cmd_auto_template(args)
    if args.command == "media":
        return _cmd_media(args)
    if args.command == "content-review":
        return _cmd_content_review(args)
    if args.command == "post-package":
        return _cmd_post_package(args)
    if args.command == "post-export":
        return _cmd_post_export(args)
    if args.command == "repurpose":
        return _cmd_repurpose(args)
    if args.command == "batch":
        return _cmd_batch(args)
    if args.command == "highlight-detect":
        return _cmd_highlight_detect(args)
    if args.command == "thumbnail":
        return _cmd_thumbnail(args)
    if args.command == "suggest":
        return _cmd_suggest(args)
    if args.command == "captions":
        return _cmd_captions(args)
    if args.command == "style":
        return _cmd_style(args)
    if args.command == "director":
        return _cmd_director(args)
    if args.command == "storyboard":
        return _cmd_storyboard(args)
    if args.command == "asset-analyze":
        return _cmd_asset_analyze(args)
    if args.command == "resolve-broll":
        return _cmd_resolve_broll(args)
    if args.command == "history":
        return _cmd_history(args)
    if args.command == "package":
        return _cmd_package(args)
    if args.command == "plugin":
        return _cmd_plugin(args)
    if args.command == "realtime-preview":
        return _cmd_realtime_preview(args)
    if args.command == "interactive-preview":
        return _cmd_interactive_preview(args)
    if args.command == "template-pack":
        return _cmd_template_pack(args)
    if args.command == "brand":
        return _cmd_brand(args)
    if args.command == "manifest":
        return _cmd_manifest(args)
    if args.command == "quality-check":
        return _cmd_quality_check(args)
    if args.command == "final-preflight":
        return _cmd_final_preflight(args)
    if args.command == "reformat":
        return _cmd_reformat(args)
    if args.command == "recovery":
        return _cmd_recovery(args)
    if args.command == "profile":
        return _cmd_profile(args)
    if args.command == "automation":
        return _cmd_automation(args)
    if args.command == "metrics":
        return _cmd_metrics(args)
    if args.command == "cinematic-enhance":
        return _cmd_cinematic_enhance(args)
    if args.command == "effect-graph":
        return _cmd_effect_graph(args)
    if args.command == "understand-clip":
        return _cmd_understand_clip(args)
    if args.command == "audio-intel":
        return _cmd_audio_intel(args)
    if args.command == "scene-build":
        return _cmd_scene_build(args)
    if args.command == "project-analyze":
        return _cmd_project_analyze(args)
    if args.command == "workspace":
        return _cmd_workspace(args)
    if args.command == "review":
        return _cmd_review(args)
    if args.command == "asset-db":
        return _cmd_asset_db(args)
    if args.command == "pack":
        return _cmd_pack(args)
    if args.command == "dataset-export":
        return _cmd_dataset_export(args)
    if args.command == "analytics":
        return _cmd_analytics(args)
    if args.command == "api":
        return _cmd_api(args)
    if args.command == "local-policy":
        return _cmd_local_policy(args)
    if args.command == "diagnostics":
        return _cmd_diagnostics(args)
    if args.command == "worker":
        return _cmd_worker(args)
    if args.command == "workflow":
        return _cmd_workflow(args)
    if args.command == "feedback":
        return _cmd_feedback(args)
    if args.command == "evolution-report":
        return _cmd_evolution_report(args)
    if args.command == "local-ai":
        return _cmd_local_ai(args)
    if args.command == "model-manager":
        return _cmd_model_manager(args)
    if args.command == "dependency-check":
        return _cmd_dependency_check(args)
    if args.command == "installer":
        return _cmd_installer(args)
    if args.command == "privacy-report":
        return _cmd_privacy_report(args)
    if args.command == "reliable-render":
        return _cmd_reliable_render(args)
    if args.command == "performance-report":
        return _cmd_performance_report(args)
    if args.command == "docs":
        return _cmd_docs(args)
    if args.command == "refine":
        return _cmd_refine(args)
    if args.command == "color":
        return _cmd_color(args)
    if args.command == "advanced":
        return _cmd_advanced(args)
    if args.command == "cache":
        return _cmd_cache(args)
    if args.command == "demo":
        return _cmd_demo(args)
    if args.command == "architecture-audit":
        return _cmd_architecture_audit(args)
    if args.command == "profile-run":
        return _cmd_profile_run(args)
    if args.command == "release-check":
        return _cmd_release_check(args)
    if args.command == "showcase":
        return _cmd_showcase(args)

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
    if args.workflow_command == "profile":
        profile = create_default_creator_profile(args.name, output_path=Path(args.output).resolve() if args.output else None)
        print(f"Creator profile: {profile['path']}")
        print(f"Profile: {profile['name']} | pacing={profile.get('pacingStyle')} | cta={profile.get('preferredCTAStyle')}")
        return 0
    if args.workflow_command == "pipeline-create":
        workflow = create_workflow_pipeline(
            args.name,
            preset=args.preset,
            profile=args.profile,
            mode=args.mode,
            tone=args.tone,
            style=args.style,
            duration=args.duration,
            output_path=Path(args.output).resolve() if args.output else None,
        )
        print(f"Workflow pipeline: {workflow['path']}")
        print(f"{workflow['name']} | mode={workflow['generationRules']['mode']} | tone={workflow['generationRules']['tone']} | duration={workflow['generationRules']['duration']}s")
        return 0
    if args.workflow_command == "pipeline-list":
        rows = list_workflow_pipelines()
        if not rows:
            print("No saved workflow pipelines found.")
            return 0
        for row in rows:
            print(f"{row['id']} | {row['name']} | {row['generationRules']['mode']} | {row['path']}")
        return 0
    if args.workflow_command == "pipeline-show":
        print(json.dumps(load_workflow_pipeline(args.name_or_path), indent=2))
        return 0
    if args.workflow_command == "batch":
        output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_generated_path(f"workflow_batch_{_slug(args.idea)[:32]}")
        report = run_workflow_batch(
            args.workflow,
            idea=args.idea,
            output_dir=output_dir,
            assets_folder=Path(args.assets).resolve() if args.assets else None,
            music_path=Path(args.music).resolve() if args.music else None,
            logo_path=Path(args.logo).resolve() if args.logo else None,
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
    if args.workflow_command == "task-create":
        task_args = shlex.split(args.cmd) if args.cmd else list(args.task_args)
        if not task_args:
            raise ValueError("task-create requires --cmd or command arguments, for example: --cmd \"render examples/project.json -o output/night.mp4 --quality preview\"")
        task = schedule_local_task(args.name, task_type=args.type, command=task_args, run_at=args.run_at, priority=args.priority)
        print(f"Scheduled local task: {task['path']}")
        print(f"{task['name']} | runAt={task['runAt']} | command={' '.join(task['command'])}")
        return 0
    if args.workflow_command == "task-list":
        tasks = list_local_tasks()
        if not tasks:
            print("No local scheduled tasks found.")
            return 0
        for task in tasks:
            print(f"{task.get('id')} | {task.get('status')} | {task.get('runAt')} | {task.get('name')}")
        return 0
    if args.workflow_command == "task-run":
        report = run_due_tasks(now="force" if args.force else None, limit=args.limit)
        print(f"Ran local tasks: {report['ran']}")
        for task in report["tasks"]:
            print(f"- {task.get('name')}: {task.get('status')} code={task.get('lastResult', {}).get('returnCode')}")
        return 0 if all(task.get("status") == "completed" for task in report["tasks"]) else 1 if report["tasks"] else 0
    if args.workflow_command == "memory-update":
        memory = update_creator_memory(
            profile_name=args.profile,
            project_path=Path(args.project).resolve() if args.project else None,
            content_plan_path=Path(args.plan).resolve() if args.plan else None,
            rating=args.rating,
            note=args.note,
            preference=_parse_preferences(args.prefer),
        )
        print(f"Creator memory: {memory['path']}")
        print(f"Events={len(memory.get('events', []))} learned={len(memory.get('learnedAt', []))}")
        return 0
    if args.workflow_command == "memory-show":
        print(json.dumps(creator_memory_report(args.profile), indent=2))
        return 0
    if args.workflow_command == "asset-reuse":
        output = Path(args.output).resolve() if args.output else None
        report = asset_reuse_report(project_path=Path(args.project).resolve() if args.project else None, output_path=output)
        if output:
            print(f"Asset reuse report: {output}")
        print(f"Top clips={len(report['frequentlyUsedClips'])} hooks={len(report['bestKnownHooks'])} transitions={len(report['favoriteTransitions'])}")
        return 0
    if args.workflow_command == "dashboard":
        output = Path(args.output).resolve() if args.output else _default_generated_path("production_dashboard.json")
        dashboard = production_dashboard(project_path=Path(args.project).resolve() if args.project else None, output_path=output)
        print(f"Production dashboard: {output}")
        print(f"Recent renders={len(dashboard['recentRenders'])} queued={dashboard['queuedRenders']} cacheBytes={dashboard['storage']['cacheBytes']} success={dashboard['renderSuccessRate']}")
        return 0
    raise ValueError(f"Unknown workflow command: {args.workflow_command}")


def _cmd_feedback(args: argparse.Namespace) -> int:
    if args.feedback_command == "review":
        ratings = {
            "pacing": args.pacing,
            "readability": args.readability,
            "transitions": args.transitions,
            "cinematicQuality": args.cinematic,
            "hookStrength": args.hook,
            "captionQuality": args.captions,
            "overallPolish": args.polish,
        }
        review = record_render_review(
            Path(args.project_json).resolve(),
            rendered_video=Path(args.video).resolve() if args.video else None,
            profile_name=args.profile,
            content_plan_path=Path(args.plan).resolve() if args.plan else None,
            ratings=ratings,
            note=args.note,
            output_path=Path(args.output).resolve() if args.output else None,
        )
        print(f"Render review: {review['path']}")
        print(f"Profile={review['profile']} average={review['averageRating']} verdict={review['verdict']}")
        return 0
    if args.feedback_command == "analyze":
        output = Path(args.output).resolve() if args.output else _default_generated_path(f"{Path(args.project_json).stem}.render_self_analysis.json")
        report = render_self_analysis(
            Path(args.project_json).resolve(),
            rendered_video=Path(args.video).resolve() if args.video else None,
            output_path=output,
        )
        print(f"Render self-analysis: {output}")
        print(f"Pacing={report['pacing'].get('score')} motion={report['motionIntensityScore']} warnings={len(report['warnings'])}")
        return 0
    if args.feedback_command == "consistency":
        output = Path(args.output).resolve() if args.output else None
        report = style_consistency_report(
            Path(args.project_json).resolve(),
            profile_name=args.profile,
            profile_path=Path(args.profile_path).resolve() if args.profile_path else None,
            output_path=output,
        )
        if output:
            print(f"Style consistency: {output}")
        print(f"Profile={report['profile']} score={report['overallScore']} warnings={len(report['warnings'])}")
        return 0
    if args.feedback_command == "hook":
        if not args.project and not args.plan:
            raise ValueError("feedback hook requires --project or --plan")
        output = Path(args.output).resolve() if args.output else None
        report = hook_effectiveness_report(
            project_path=Path(args.project).resolve() if args.project else None,
            content_plan_path=Path(args.plan).resolve() if args.plan else None,
            output_path=output,
        )
        if output:
            print(f"Hook effectiveness: {output}")
        print(f"Retention={report['scores']['viewerRetentionPotential']} overload={report['visualOverloadRisk']} words={report['wordCount']}")
        return 0
    if args.feedback_command == "ai-event":
        report = record_ai_feedback_event(
            args.profile,
            project_path=Path(args.project).resolve() if args.project else None,
            regenerated_scenes=args.scene_regenerated,
            removed_transitions=args.transition_removed,
            edited_captions=args.caption_edited,
            locked_sections=args.section_locked,
            note=args.note,
            output_path=Path(args.output).resolve() if args.output else None,
        )
        print(f"AI feedback: {report['path']}")
        print(f"Events={len(report.get('events', []))} regenerated={len(report.get('summary', {}).get('oftenRegeneratedScenes', {}))}")
        return 0
    if args.feedback_command == "learn":
        report = learn_preferences(args.profile, output_path=Path(args.output).resolve() if args.output else None)
        print(f"Creator identity: {report['path']}")
        print(f"Samples={report['sampleCount']} positive={report['positiveSampleCount']} pacing={report['preferenceModel'].get('pacingStyle')}")
        return 0
    if args.feedback_command == "identity":
        report = creator_identity_report(args.profile, output_path=Path(args.output).resolve() if args.output else None)
        if args.output:
            print(f"Creator identity: {Path(args.output).resolve()}")
        print(json.dumps(report, indent=2))
        return 0
    if args.feedback_command == "dataset":
        manifest = export_local_training_dataset(
            args.profile,
            output_dir=Path(args.output_dir).resolve(),
            min_rating=args.min_rating,
        )
        print(f"Local training dataset: {Path(args.output_dir).resolve()}")
        print(f"Approved edits={manifest['approvedEditCount']} minRating={manifest['minRating']}")
        return 0
    raise ValueError(f"Unknown feedback command: {args.feedback_command}")


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
        print(f"Local prompt JSON: {result['output']}")
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


def _parse_preferences(items: list[str]) -> dict[str, Any]:
    preferences: dict[str, Any] = {}
    for item in items or []:
        if "=" not in item:
            preferences[item] = True
            continue
        key, value = item.split("=", 1)
        value = value.strip()
        if value.lower() in {"true", "false"}:
            parsed: Any = value.lower() == "true"
        else:
            try:
                parsed = float(value) if "." in value else int(value)
            except ValueError:
                parsed = value
        preferences[key.strip()] = parsed
    return preferences


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
