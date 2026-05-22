from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable

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

_FeedbackHandler = Callable[[argparse.Namespace], int]


def run_feedback_command(args: argparse.Namespace) -> int:
    handler = _FEEDBACK_HANDLERS.get(args.feedback_command)
    if not handler:
        raise ValueError(f"Unknown feedback command: {args.feedback_command}")
    return handler(args)


def _feedback_review(args: argparse.Namespace) -> int:
    review = record_render_review(
        Path(args.project_json).resolve(),
        rendered_video=_optional_path(args.video),
        profile_name=args.profile,
        content_plan_path=_optional_path(args.plan),
        ratings=_review_ratings(args),
        note=args.note,
        output_path=_optional_path(args.output),
    )
    print(f"Render review: {review['path']}")
    print(f"Profile={review['profile']} average={review['averageRating']} verdict={review['verdict']}")
    return 0


def _feedback_analyze(args: argparse.Namespace) -> int:
    output = _optional_path(args.output) or _default_generated_path(f"{Path(args.project_json).stem}.render_self_analysis.json")
    report = render_self_analysis(
        Path(args.project_json).resolve(),
        rendered_video=_optional_path(args.video),
        output_path=output,
    )
    print(f"Render self-analysis: {output}")
    print(f"Pacing={report['pacing'].get('score')} motion={report['motionIntensityScore']} warnings={len(report['warnings'])}")
    return 0


def _feedback_consistency(args: argparse.Namespace) -> int:
    output = _optional_path(args.output)
    report = style_consistency_report(
        Path(args.project_json).resolve(),
        profile_name=args.profile,
        profile_path=_optional_path(args.profile_path),
        output_path=output,
    )
    if output:
        print(f"Style consistency: {output}")
    print(f"Profile={report['profile']} score={report['overallScore']} warnings={len(report['warnings'])}")
    return 0


def _feedback_hook(args: argparse.Namespace) -> int:
    if not args.project and not args.plan:
        raise ValueError("feedback hook requires --project or --plan")
    output = _optional_path(args.output)
    report = hook_effectiveness_report(
        project_path=_optional_path(args.project),
        content_plan_path=_optional_path(args.plan),
        output_path=output,
    )
    if output:
        print(f"Hook effectiveness: {output}")
    print(f"Retention={report['scores']['viewerRetentionPotential']} overload={report['visualOverloadRisk']} words={report['wordCount']}")
    return 0


def _feedback_ai_event(args: argparse.Namespace) -> int:
    report = record_ai_feedback_event(
        args.profile,
        project_path=_optional_path(args.project),
        regenerated_scenes=args.scene_regenerated,
        removed_transitions=args.transition_removed,
        edited_captions=args.caption_edited,
        locked_sections=args.section_locked,
        note=args.note,
        output_path=_optional_path(args.output),
    )
    print(f"AI feedback: {report['path']}")
    print(f"Events={len(report.get('events', []))} regenerated={len(report.get('summary', {}).get('oftenRegeneratedScenes', {}))}")
    return 0


def _feedback_learn(args: argparse.Namespace) -> int:
    report = learn_preferences(args.profile, output_path=_optional_path(args.output))
    print(f"Creator identity: {report['path']}")
    print(f"Samples={report['sampleCount']} positive={report['positiveSampleCount']} pacing={report['preferenceModel'].get('pacingStyle')}")
    return 0


def _feedback_identity(args: argparse.Namespace) -> int:
    report = creator_identity_report(args.profile, output_path=_optional_path(args.output))
    if args.output:
        print(f"Creator identity: {Path(args.output).resolve()}")
    print(json.dumps(report, indent=2))
    return 0


def _feedback_dataset(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).resolve()
    manifest = export_local_training_dataset(
        args.profile,
        output_dir=output_dir,
        min_rating=args.min_rating,
    )
    print(f"Local training dataset: {output_dir}")
    print(f"Approved edits={manifest['approvedEditCount']} minRating={manifest['minRating']}")
    return 0


def _review_ratings(args: argparse.Namespace) -> dict[str, int]:
    return {
        "pacing": args.pacing,
        "readability": args.readability,
        "transitions": args.transitions,
        "cinematicQuality": args.cinematic,
        "hookStrength": args.hook,
        "captionQuality": args.captions,
        "overallPolish": args.polish,
    }


def _optional_path(value: str | None) -> Path | None:
    return Path(value).resolve() if value else None


def _default_generated_path(filename: str) -> Path:
    return Path(__file__).resolve().parents[2] / "examples" / "generated" / filename


_FEEDBACK_HANDLERS: dict[str, _FeedbackHandler] = {
    "review": _feedback_review,
    "analyze": _feedback_analyze,
    "consistency": _feedback_consistency,
    "hook": _feedback_hook,
    "ai-event": _feedback_ai_event,
    "learn": _feedback_learn,
    "identity": _feedback_identity,
    "dataset": _feedback_dataset,
}
