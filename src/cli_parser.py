from __future__ import annotations

import argparse

from beginner.auto_template import template_names as beginner_template_names
from cinematic.enhancer import list_cinematic_presets
from color.pipeline import list_color_presets
from refinement.polish import list_polish_presets
from styles.presets import list_styles
from templates.catalog import template_names


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

    _register_core_commands(subparsers)
    _register_template_and_build_commands(subparsers)
    _register_autonomous_generation_commands(subparsers)
    _register_beginner_media_review_commands(subparsers)
    _register_post_export_commands(subparsers)
    _register_content_tool_commands(subparsers)
    _register_project_io_preview_commands(subparsers)
    _register_quality_recovery_commands(subparsers)
    _register_automation_analysis_commands(subparsers)
    _register_workspace_review_commands(subparsers)
    _register_asset_pack_api_commands(subparsers)
    _register_workflow_commands(subparsers)
    _register_feedback_ai_commands(subparsers)
    _register_system_maintenance_commands(subparsers)
    _register_release_showcase_commands(subparsers)

    return parser


def _register_core_commands(subparsers) -> None:
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


def _register_template_and_build_commands(subparsers) -> None:
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


def _register_autonomous_generation_commands(subparsers) -> None:
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


def _register_beginner_media_review_commands(subparsers) -> None:
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


def _register_post_export_commands(subparsers) -> None:
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


def _register_content_tool_commands(subparsers) -> None:
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


def _register_project_io_preview_commands(subparsers) -> None:
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


def _register_quality_recovery_commands(subparsers) -> None:
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


def _register_automation_analysis_commands(subparsers) -> None:
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


def _register_workspace_review_commands(subparsers) -> None:
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


def _register_asset_pack_api_commands(subparsers) -> None:
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


def _register_workflow_commands(subparsers) -> None:
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


def _register_feedback_ai_commands(subparsers) -> None:
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


def _register_system_maintenance_commands(subparsers) -> None:
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


def _register_release_showcase_commands(subparsers) -> None:
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
