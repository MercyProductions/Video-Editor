from __future__ import annotations

import hashlib
import json
import shutil
import time
from collections import Counter
from pathlib import Path
from typing import Any

from content.profiles import load_profile
from intelligence.project_analyzer import analyze_project
from metrics.store import record_metric
from quality.checker import run_quality_check
from utils.media import media_duration, run_ffmpeg


RATING_KEYS = {
    "pacing",
    "readability",
    "transitions",
    "cinematicQuality",
    "hookStrength",
    "captionQuality",
    "overallPolish",
}


def feedback_root() -> Path:
    return Path(__file__).resolve().parents[2] / "feedback"


def reviews_dir() -> Path:
    return feedback_root() / "reviews"


def identity_dir() -> Path:
    return feedback_root() / "identity"


def ai_feedback_dir() -> Path:
    return feedback_root() / "ai_feedback"


def datasets_dir() -> Path:
    return feedback_root() / "datasets"


def record_render_review(
    project_path: Path,
    *,
    rendered_video: Path | None = None,
    profile_name: str = "Default Creator",
    ratings: dict[str, int | float | str | None] | None = None,
    note: str | None = None,
    content_plan_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    project_path = project_path.resolve()
    project = _read_json(project_path)
    clean_ratings = _normalize_ratings(ratings or {})
    self_analysis = render_self_analysis(project_path, rendered_video=rendered_video)
    consistency = style_consistency_report(project_path, profile_name=profile_name)
    hook = hook_effectiveness_report(project_path=project_path, content_plan_path=content_plan_path)
    average = _average_rating(clean_ratings)
    verdict = "approved" if average >= 4.0 else "needs_improvement" if average >= 2.8 else "reject"
    review = {
        "reviewVersion": 1,
        "localOnly": True,
        "createdAt": _now(),
        "profile": profile_name,
        "project": str(project_path),
        "renderedVideo": str(rendered_video.resolve()) if rendered_video else None,
        "contentPlan": str(content_plan_path.resolve()) if content_plan_path else None,
        "projectFingerprint": _fingerprint(project),
        "ratings": clean_ratings,
        "averageRating": average,
        "verdict": verdict,
        "note": note,
        "styleConsistency": consistency,
        "hookEffectiveness": hook,
        "renderSelfAnalysis": self_analysis,
        "preferenceHints": _preference_hints(project, clean_ratings, consistency, hook, self_analysis),
        "explainability": _review_explanation(clean_ratings, consistency, hook, self_analysis),
    }
    path = reviews_dir() / profile_name_slug(profile_name) / f"{project_path.stem}_{int(time.time() * 1000)}.render-review.json"
    _write_json(path, review)
    if output_path and output_path.resolve() != path.resolve():
        _write_json(output_path, review)
        review["outputPath"] = str(output_path.resolve())
    review["path"] = str(path.resolve())
    record_metric("render_review", {"profile": profile_name, "averageRating": average, "verdict": verdict})
    return review


def render_self_analysis(
    project_path: Path,
    *,
    rendered_video: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    project_path = project_path.resolve()
    project_analysis = analyze_project(project_path, rendered_video=rendered_video)
    quality = run_quality_check(project_path)
    project = _read_json(project_path)
    artifact_report = _render_artifacts(rendered_video)
    transition_counts = project_analysis.get("transitions", {}).get("counts", {})
    motion_score = _motion_intensity_score(project)
    overprocess = _overprocessed_visuals(project)
    warnings = list(project_analysis.get("warnings", []))
    if project_analysis.get("pacing", {}).get("score", 100) < 70:
        warnings.append("Pacing score is weak for short-form retention.")
    if project_analysis.get("transitions", {}).get("spamRisk") == "high":
        warnings.append("Transitions are repetitive enough to feel automated.")
    if motion_score > 85:
        warnings.append("Motion intensity is high; consider reducing zooms/shakes.")
    if overprocess["score"] > 75:
        warnings.append("Visual processing is heavy; check glow, vignette, and effect stacking.")
    unreadable = [
        issue for issue in quality.get("issues", [])
        if "contrast" in str(issue.get("message", "")).lower() or "caption" in str(issue.get("message", "")).lower()
    ]
    report = {
        "analysisVersion": 1,
        "project": str(project_path),
        "renderedVideo": str(rendered_video.resolve()) if rendered_video else None,
        "duration": project_analysis.get("duration"),
        "renderedDuration": project_analysis.get("renderedDuration"),
        "sceneCount": project_analysis.get("sceneCount", len(project.get("timeline", []))),
        "pacing": project_analysis.get("pacing", {}),
        "captions": project_analysis.get("captions", {}),
        "transitions": project_analysis.get("transitions", {}),
        "transitionCounts": transition_counts,
        "deadSections": project_analysis.get("boringSections", []),
        "motionIntensityScore": motion_score,
        "readabilityIssues": unreadable,
        "overprocessedVisuals": overprocess,
        "renderArtifacts": artifact_report,
        "warnings": warnings,
        "recommendations": _self_analysis_recommendations(project_analysis, quality, motion_score, overprocess, artifact_report),
    }
    if output_path:
        _write_json(output_path, report)
    return report


def style_consistency_report(
    project_path: Path,
    *,
    profile_name: str | None = None,
    profile_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    project_path = project_path.resolve()
    project = _read_json(project_path)
    profile = load_profile(profile_path or profile_name)
    scenes = project.get("timeline", [])
    durations = [float(scene.get("duration", 0) or 0) for scene in scenes]
    transitions = [_transition_type(scene) for scene in scenes if scene.get("transitionOut")]
    preferred = set(str(item) for item in profile.get("favoriteTransitions", []))
    style = str(project.get("stylePreset") or project.get("metadata", {}).get("stylePreset") or "")
    scores = {
        "pacing": _pacing_consistency_score(durations, str(profile.get("pacingStyle", ""))),
        "branding": _branding_score(project, profile, style),
        "transitions": _transition_consistency_score(transitions, preferred),
        "lighting": _lighting_consistency_score(project, style),
    }
    total = round(sum(scores.values()) / max(len(scores), 1), 1)
    report = {
        "consistencyVersion": 1,
        "project": str(project_path),
        "profile": profile.get("name", profile_name or "Default Creator"),
        "stylePreset": style or None,
        "scores": scores,
        "overallScore": total,
        "matchedPreferredTransitions": sorted(set(transitions) & preferred),
        "warnings": _consistency_warnings(scores, transitions),
    }
    if output_path:
        _write_json(output_path, report)
    return report


def hook_effectiveness_report(
    *,
    content_plan_path: Path | None = None,
    project_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    hook = ""
    duration = 3.0
    source = None
    if content_plan_path and content_plan_path.exists():
        plan = _read_json(content_plan_path)
        hook = str(plan.get("hook") or "")
        source = str(content_plan_path.resolve())
    if not hook and project_path and project_path.exists():
        project = _read_json(project_path)
        hook, duration = _hook_from_project(project)
        source = str(project_path.resolve())
    words = [word for word in hook.replace("\n", " ").split(" ") if word.strip()]
    word_count = len(words)
    action_words = sum(1 for word in words if word.strip(".,!?").lower() in {"stop", "fix", "save", "scan", "detect", "reveal", "avoid", "watch", "turn", "make"})
    has_specifics = any(len(word.strip(".,!?")) >= 8 for word in words)
    intensity = min(100, 40 + action_words * 12 + (12 if "?" in hook or "!" in hook else 0) + (12 if has_specifics else 0) + max(0, 8 - abs(word_count - 8)) * 2)
    pacing = max(20, min(100, 105 - max(0, duration - 3.0) * 14 - max(0, word_count - 14) * 4))
    readability_speed = round(word_count / max(duration, 0.1), 2)
    overload_risk = "high" if readability_speed > 4.2 or word_count > 18 else "medium" if readability_speed > 3.2 or word_count > 13 else "low"
    retention = round((intensity * 0.45 + pacing * 0.35 + (100 if overload_risk == "low" else 70 if overload_risk == "medium" else 40) * 0.2), 1)
    report = {
        "hookVersion": 1,
        "source": source,
        "hook": hook,
        "duration": round(duration, 3),
        "wordCount": word_count,
        "scores": {
            "hookIntensity": round(intensity, 1),
            "pacingMomentum": round(pacing, 1),
            "viewerRetentionPotential": retention,
            "readabilitySpeed": readability_speed,
        },
        "visualOverloadRisk": overload_risk,
        "recommendations": _hook_recommendations(hook, duration, word_count, overload_risk),
    }
    if output_path:
        _write_json(output_path, report)
    return report


def record_ai_feedback_event(
    profile_name: str,
    *,
    project_path: Path | None = None,
    regenerated_scenes: list[str] | None = None,
    removed_transitions: list[str] | None = None,
    edited_captions: list[str] | None = None,
    locked_sections: list[str] | None = None,
    note: str | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    path = ai_feedback_dir() / f"{profile_name_slug(profile_name)}.ai-feedback.json"
    data = _read_json(path, default={"feedbackVersion": 1, "profile": profile_name, "events": [], "summary": {}})
    event = {
        "timestamp": _now(),
        "project": str(project_path.resolve()) if project_path else None,
        "regeneratedScenes": regenerated_scenes or [],
        "removedTransitions": removed_transitions or [],
        "editedCaptions": edited_captions or [],
        "lockedSections": locked_sections or [],
        "note": note,
    }
    data.setdefault("events", []).append(event)
    data["summary"] = _ai_feedback_summary(data["events"])
    _write_json(path, data)
    if output_path and output_path.resolve() != path.resolve():
        _write_json(output_path, data)
        data["outputPath"] = str(output_path.resolve())
    data["path"] = str(path.resolve())
    record_metric("ai_feedback", {"profile": profile_name, "events": len(data["events"])})
    return data


def learn_preferences(profile_name: str, *, output_path: Path | None = None) -> dict[str, Any]:
    reviews = _reviews_for_profile(profile_name)
    ai_feedback = _ai_feedback_for_profile(profile_name)
    positive = [review for review in reviews if str(review.get("verdict")) == "approved" or float(review.get("averageRating", 0) or 0) >= 4.0]
    all_for_stats = positive or reviews
    preference_model = {
        "pacingStyle": _learn_pacing_style(all_for_stats),
        "transitionIntensity": _learn_transition_intensity(all_for_stats),
        "captionDensity": _learn_caption_density(all_for_stats),
        "motionAggressiveness": _learn_motion_aggressiveness(all_for_stats),
        "colorGradingPreference": _learn_color_preference(all_for_stats),
        "titleCardBehavior": _learn_title_cards(all_for_stats),
    }
    identity = {
        "identityVersion": 1,
        "localOnly": True,
        "profile": profile_name,
        "updatedAt": _now(),
        "sampleCount": len(reviews),
        "positiveSampleCount": len(positive),
        "preferenceModel": preference_model,
        "creatorIdentity": {
            "pacingRhythm": preference_model["pacingStyle"],
            "motionStyle": preference_model["motionAggressiveness"],
            "captionBehavior": preference_model["captionDensity"],
            "transitionPhilosophy": preference_model["transitionIntensity"],
            "styleFingerprint": _style_fingerprint(all_for_stats),
        },
        "aiImprovementSignals": ai_feedback.get("summary", {}),
        "generationGuidance": _generation_guidance(preference_model, ai_feedback.get("summary", {})),
        "explainability": _identity_explanation(reviews, positive, preference_model),
    }
    path = identity_dir() / f"{profile_name_slug(profile_name)}.creator-identity.json"
    _write_json(path, identity)
    if output_path and output_path.resolve() != path.resolve():
        _write_json(output_path, identity)
        identity["outputPath"] = str(output_path.resolve())
    identity["path"] = str(path.resolve())
    record_metric("preference_learning", {"profile": profile_name, "sampleCount": len(reviews), "positiveSampleCount": len(positive)})
    return identity


def creator_identity_report(profile_name: str, *, output_path: Path | None = None) -> dict[str, Any]:
    path = identity_dir() / f"{profile_name_slug(profile_name)}.creator-identity.json"
    data = _read_json(path, default={"identityVersion": 1, "profile": profile_name, "sampleCount": 0, "preferenceModel": {}, "creatorIdentity": {}, "generationGuidance": []})
    data["path"] = str(path.resolve())
    if output_path:
        _write_json(output_path, data)
    return data


def export_local_training_dataset(
    profile_name: str,
    *,
    output_dir: Path,
    min_rating: float = 4.0,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    reviews = [review for review in _reviews_for_profile(profile_name) if float(review.get("averageRating", 0) or 0) >= min_rating]
    successful_timelines = output_dir / "successful_timelines.jsonl"
    approved_edits = output_dir / "approved_edits.jsonl"
    pacing_maps = []
    transition_patterns = Counter()
    fingerprints = []
    with successful_timelines.open("w", encoding="utf-8") as timelines_handle, approved_edits.open("w", encoding="utf-8") as edits_handle:
        for review in reviews:
            project_path = Path(str(review.get("project", "")))
            if not project_path.exists():
                continue
            project = _read_json(project_path)
            timelines_handle.write(json.dumps({"project": str(project_path), "timeline": project.get("timeline", [])}, sort_keys=True) + "\n")
            edits_handle.write(json.dumps(_dataset_review_row(review), sort_keys=True) + "\n")
            pacing_maps.append(_pacing_map(project_path, project, review))
            transition_patterns.update(_transition_type(scene) for scene in project.get("timeline", []) if scene.get("transitionOut"))
            fingerprints.append(_style_fingerprint([review]))
    _write_json(output_dir / "pacing_maps.json", {"profile": profile_name, "items": pacing_maps})
    _write_json(output_dir / "transition_patterns.json", {"profile": profile_name, "patterns": dict(transition_patterns.most_common())})
    _write_json(output_dir / "style_fingerprints.json", {"profile": profile_name, "fingerprints": fingerprints})
    manifest = {
        "datasetVersion": 1,
        "localOnly": True,
        "profile": profile_name,
        "createdAt": _now(),
        "minRating": min_rating,
        "approvedEditCount": len(reviews),
        "files": {
            "approvedEdits": str(approved_edits.resolve()),
            "pacingMaps": str((output_dir / "pacing_maps.json").resolve()),
            "transitionPatterns": str((output_dir / "transition_patterns.json").resolve()),
            "successfulTimelines": str(successful_timelines.resolve()),
            "styleFingerprints": str((output_dir / "style_fingerprints.json").resolve()),
        },
        "privacy": "All dataset files are local and reference local project paths only.",
    }
    _write_json(output_dir / "dataset_manifest.json", manifest)
    return manifest


def profile_name_slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "creator"


def _normalize_ratings(ratings: dict[str, int | float | str | None]) -> dict[str, int]:
    clean = {}
    for key in RATING_KEYS:
        raw = ratings.get(key)
        if raw is None:
            continue
        try:
            value = int(round(float(raw)))
        except (TypeError, ValueError):
            continue
        clean[key] = max(1, min(5, value))
    return clean


def _average_rating(ratings: dict[str, int]) -> float:
    if not ratings:
        return 0.0
    return round(sum(ratings.values()) / len(ratings), 2)


def _preference_hints(
    project: dict[str, Any],
    ratings: dict[str, int],
    consistency: dict[str, Any],
    hook: dict[str, Any],
    self_analysis: dict[str, Any],
) -> dict[str, Any]:
    positive = _average_rating(ratings) >= 4.0
    hints = {
        "keepPacing": positive and ratings.get("pacing", 0) >= 4,
        "keepCaptionDensity": positive and ratings.get("captionQuality", 0) >= 4,
        "reduceTransitionIntensity": ratings.get("transitions", 5) <= 2 or self_analysis.get("transitions", {}).get("spamRisk") == "high",
        "increaseHookStrength": ratings.get("hookStrength", 5) <= 3 or hook.get("scores", {}).get("viewerRetentionPotential", 100) < 70,
        "protectBrandStyle": consistency.get("overallScore", 0) >= 80,
        "stylePreset": project.get("stylePreset") or project.get("metadata", {}).get("stylePreset"),
    }
    return hints


def _review_explanation(ratings: dict[str, int], consistency: dict[str, Any], hook: dict[str, Any], self_analysis: dict[str, Any]) -> list[str]:
    lines = []
    if ratings:
        weakest = sorted(ratings.items(), key=lambda item: item[1])[:2]
        strongest = sorted(ratings.items(), key=lambda item: item[1], reverse=True)[:2]
        lines.append(f"Strongest user signals: {', '.join(f'{k}={v}' for k, v in strongest)}.")
        lines.append(f"Weakest user signals: {', '.join(f'{k}={v}' for k, v in weakest)}.")
    lines.append(f"Style consistency scored {consistency.get('overallScore', 0)}/100.")
    lines.append(f"Hook retention potential scored {hook.get('scores', {}).get('viewerRetentionPotential', 0)}/100.")
    if self_analysis.get("warnings"):
        lines.append(f"Self-analysis flagged {len(self_analysis['warnings'])} item(s) for review.")
    return lines


def _render_artifacts(rendered_video: Path | None) -> dict[str, Any]:
    if not rendered_video:
        return {"checked": False, "reason": "No rendered video supplied."}
    rendered_video = rendered_video.resolve()
    if not rendered_video.exists():
        return {"checked": False, "reason": f"Rendered video missing: {rendered_video}"}
    duration = media_duration(rendered_video)
    try:
        result = run_ffmpeg([
            "-hide_banner",
            "-i",
            str(rendered_video),
            "-vf",
            "blackdetect=d=0.35:pix_th=0.10,freezedetect=n=-60dB:d=1.0",
            "-an",
            "-f",
            "null",
            "-",
        ])
        output = (result.stderr or "") + (result.stdout or "")
        black = output.count("black_start:")
        frozen = output.count("freezedetect.freeze_start")
        return {"checked": True, "duration": round(duration, 3), "blackFrameEvents": black, "frozenFrameEvents": frozen, "warning": result.returncode != 0}
    except Exception as exc:
        return {"checked": False, "duration": round(duration, 3), "reason": str(exc)}


def _motion_intensity_score(project: dict[str, Any]) -> int:
    score = 18
    for scene in project.get("timeline", []):
        for layer in scene.get("layers", []):
            animation = layer.get("animation")
            if isinstance(animation, dict):
                values = " ".join(str(value) for value in animation.values())
                score += values.lower().count("zoom") * 5
                score += values.lower().count("shake") * 8
                score += values.lower().count("slide") * 3
            if isinstance(layer.get("camera"), dict):
                score += 8
            effects = layer.get("effects")
            if isinstance(effects, list):
                score += sum(7 for item in effects if str(item).lower() in {"shake", "pulse", "zoom", "glow"})
            elif isinstance(effects, str) and effects.lower() in {"shake", "pulse", "zoom", "glow"}:
                score += 7
    return max(0, min(100, score))


def _overprocessed_visuals(project: dict[str, Any]) -> dict[str, Any]:
    total = 0
    scene_count = max(len(project.get("timeline", [])), 1)
    heavy_terms = Counter()
    for scene in project.get("timeline", []):
        for container in [scene.get("postProcessing", {}), scene.get("colorGrading", {}), scene.get("lighting", {})]:
            if isinstance(container, dict):
                for key, value in container.items():
                    if value not in {None, False, 0, "none"}:
                        heavy_terms[str(key)] += 1
                        total += 1
        for layer in scene.get("layers", []):
            effects = layer.get("effects", [])
            if isinstance(effects, str):
                effects = [effects]
            for effect in effects if isinstance(effects, list) else []:
                if str(effect).lower() in {"glow", "blur", "shake", "vignette", "bloom", "rgb_shift"}:
                    heavy_terms[str(effect)] += 1
                    total += 1
    score = min(100, round(total / scene_count * 24))
    return {"score": score, "terms": dict(heavy_terms.most_common(10))}


def _self_analysis_recommendations(
    project_analysis: dict[str, Any],
    quality: dict[str, Any],
    motion_score: int,
    overprocess: dict[str, Any],
    artifacts: dict[str, Any],
) -> list[str]:
    recs = list(project_analysis.get("recommendations", []))
    if quality.get("issues"):
        recs.append("Resolve quality-check warnings before marking this edit reusable.")
    if motion_score > 80:
        recs.append("Reduce shake/zoom frequency or lower motion intensity for readability.")
    if overprocess.get("score", 0) > 70:
        recs.append("Tone down stacked post-processing so the source footage remains readable.")
    if artifacts.get("blackFrameEvents"):
        recs.append("Review black-frame events; they may be intentional fades or accidental gaps.")
    if artifacts.get("frozenFrameEvents"):
        recs.append("Review frozen-frame events for loading pauses or stalled renders.")
    return _unique(recs)


def _pacing_consistency_score(durations: list[float], pacing_style: str) -> int:
    if not durations:
        return 60
    average = sum(durations) / len(durations)
    spread = max(durations) - min(durations)
    target = 2.2 if pacing_style in {"fast", "fast_vertical", "aggressive"} else 3.8 if pacing_style in {"medium_fast", "cinematic"} else 5.0
    score = 100 - abs(average - target) * 12 - max(0, spread - 6) * 3
    return max(20, min(100, round(score)))


def _branding_score(project: dict[str, Any], profile: dict[str, Any], style: str) -> int:
    branding = profile.get("branding", {})
    primary = str(branding.get("primaryColor", "")).lower()
    has_logo = any(key.lower() == "logo" for key in project.get("assets", {}).keys())
    colors = []
    for scene in project.get("timeline", []):
        for layer in scene.get("layers", []):
            for key in ["color", "strokeColor", "boxColor", "shadowColor"]:
                if layer.get(key):
                    colors.append(str(layer[key]).lower())
    score = 62 + (15 if style else 0) + (12 if has_logo else 0) + (11 if primary and any(primary[:4] in color for color in colors) else 0)
    return min(100, score)


def _transition_consistency_score(transitions: list[str], preferred: set[str]) -> int:
    if not transitions:
        return 78
    counts = Counter(transitions)
    top_ratio = counts.most_common(1)[0][1] / len(transitions)
    preferred_ratio = sum(1 for item in transitions if item in preferred) / len(transitions) if preferred else 0.5
    score = 70 + preferred_ratio * 24 - max(0, top_ratio - 0.7) * 42
    return max(25, min(100, round(score)))


def _lighting_consistency_score(project: dict[str, Any], style: str) -> int:
    scenes = project.get("timeline", [])
    if not scenes:
        return 60
    lit = 0
    for scene in scenes:
        payload = json.dumps(scene).lower()
        if any(term in payload for term in ["glow", "vignette", "bloom", "lighting", "contrast", "red_black", "cinematic"]):
            lit += 1
    ratio = lit / len(scenes)
    if style in {"minimal_tech", "clean_cinematic"}:
        return max(55, min(100, round(92 - max(0, ratio - 0.55) * 35)))
    return max(55, min(100, round(68 + ratio * 32)))


def _consistency_warnings(scores: dict[str, int], transitions: list[str]) -> list[str]:
    warnings = [f"{key} consistency is low." for key, score in scores.items() if score < 65]
    counts = Counter(transitions)
    if transitions and counts.most_common(1)[0][1] / len(transitions) > 0.8:
        warnings.append("One transition dominates the edit.")
    return warnings


def _hook_from_project(project: dict[str, Any]) -> tuple[str, float]:
    first_scene = (project.get("timeline") or [{}])[0]
    text_bits = []
    for layer in first_scene.get("layers", []):
        if layer.get("type") in {"text", "caption", "captions"}:
            if layer.get("text"):
                text_bits.append(str(layer["text"]))
            for item in layer.get("items", []) if isinstance(layer.get("items"), list) else []:
                if item.get("text"):
                    text_bits.append(str(item["text"]))
    return " ".join(text_bits).strip(), float(first_scene.get("duration", 3) or 3)


def _hook_recommendations(hook: str, duration: float, word_count: int, overload_risk: str) -> list[str]:
    recs = []
    if not hook:
        return ["Add a clear first-line hook before the first feature reveal."]
    if duration > 4.0:
        recs.append("Shorten the hook scene or add a faster visual change before second 3.")
    if word_count < 4:
        recs.append("Make the hook more specific so viewers know why to stay.")
    if overload_risk != "low":
        recs.append("Reduce hook caption length or split it into two beats.")
    if "?" not in hook and "!" not in hook and word_count > 10:
        recs.append("Consider a stronger curiosity or problem statement.")
    if not recs:
        recs.append("Hook structure looks usable for short-form pacing.")
    return recs


def _ai_feedback_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    regenerated = Counter()
    removed = Counter()
    edited = Counter()
    locked = Counter()
    for event in events:
        regenerated.update(str(item) for item in event.get("regeneratedScenes", []))
        removed.update(str(item) for item in event.get("removedTransitions", []))
        edited.update(str(item) for item in event.get("editedCaptions", []))
        locked.update(str(item) for item in event.get("lockedSections", []))
    return {
        "eventCount": len(events),
        "oftenRegeneratedScenes": dict(regenerated.most_common(10)),
        "oftenRemovedTransitions": dict(removed.most_common(10)),
        "oftenEditedCaptions": dict(edited.most_common(10)),
        "consistentlyLockedSections": dict(locked.most_common(10)),
    }


def _reviews_for_profile(profile_name: str) -> list[dict[str, Any]]:
    root = reviews_dir() / profile_name_slug(profile_name)
    if not root.exists():
        return []
    reviews = []
    for path in sorted(root.glob("*.render-review.json")):
        try:
            item = _read_json(path)
            item["path"] = str(path.resolve())
            reviews.append(item)
        except Exception:
            continue
    return reviews


def _ai_feedback_for_profile(profile_name: str) -> dict[str, Any]:
    return _read_json(ai_feedback_dir() / f"{profile_name_slug(profile_name)}.ai-feedback.json", default={"feedbackVersion": 1, "profile": profile_name, "events": [], "summary": {}})


def _learn_pacing_style(reviews: list[dict[str, Any]]) -> str:
    averages = [float(review.get("renderSelfAnalysis", {}).get("pacing", {}).get("averageSceneDuration", 0) or 0) for review in reviews]
    average = sum(averages) / len(averages) if averages else 0
    if average and average < 2.0:
        return "fast_aggressive"
    if average and average < 4.2:
        return "medium_fast"
    if average:
        return "clean_deliberate"
    return "balanced"


def _learn_transition_intensity(reviews: list[dict[str, Any]]) -> str:
    counts = []
    for review in reviews:
        transitions = review.get("renderSelfAnalysis", {}).get("transitionCounts", {})
        scene_count = max(int(review.get("renderSelfAnalysis", {}).get("sceneCount", 0) or 0), 1)
        counts.append(sum(int(value) for value in transitions.values()) / scene_count)
    average = sum(counts) / len(counts) if counts else 0
    return "high" if average > 0.85 else "medium" if average > 0.45 else "low"


def _learn_caption_density(reviews: list[dict[str, Any]]) -> str:
    values = [float(review.get("renderSelfAnalysis", {}).get("captions", {}).get("wordsPerSecond", 0) or 0) for review in reviews]
    average = sum(values) / len(values) if values else 0
    return "caption_heavy" if average > 3.2 else "balanced" if average > 1.4 else "minimal"


def _learn_motion_aggressiveness(reviews: list[dict[str, Any]]) -> str:
    scores = [float(review.get("renderSelfAnalysis", {}).get("motionIntensityScore", 0) or 0) for review in reviews]
    average = sum(scores) / len(scores) if scores else 0
    return "aggressive" if average > 72 else "cinematic_smooth" if average > 42 else "subtle"


def _learn_color_preference(reviews: list[dict[str, Any]]) -> str:
    styles = Counter(str(review.get("preferenceHints", {}).get("stylePreset")) for review in reviews if review.get("preferenceHints", {}).get("stylePreset"))
    if styles:
        return styles.most_common(1)[0][0]
    return "profile_default"


def _learn_title_cards(reviews: list[dict[str, Any]]) -> str:
    positive_title = 0
    total = 0
    for review in reviews:
        path = Path(str(review.get("project", "")))
        if not path.exists():
            continue
        total += 1
        project = _read_json(path)
        first = (project.get("timeline") or [{}])[0]
        if any(layer.get("type") == "text" and len(str(layer.get("text", "")).split()) <= 8 for layer in first.get("layers", [])):
            positive_title += 1
    if not total:
        return "short_title_cards"
    return "title_card_first" if positive_title / total >= 0.5 else "caption_first"


def _style_fingerprint(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    transitions = Counter()
    styles = Counter()
    motion = []
    captions = []
    for review in reviews:
        transitions.update(review.get("renderSelfAnalysis", {}).get("transitionCounts", {}))
        style = review.get("preferenceHints", {}).get("stylePreset")
        if style:
            styles[str(style)] += 1
        motion.append(float(review.get("renderSelfAnalysis", {}).get("motionIntensityScore", 0) or 0))
        captions.append(float(review.get("renderSelfAnalysis", {}).get("captions", {}).get("wordsPerSecond", 0) or 0))
    return {
        "topTransitions": dict(transitions.most_common(5)),
        "topStyles": dict(styles.most_common(5)),
        "averageMotionScore": round(sum(motion) / len(motion), 2) if motion else 0,
        "averageCaptionWps": round(sum(captions) / len(captions), 2) if captions else 0,
    }


def _generation_guidance(preferences: dict[str, str], ai_summary: dict[str, Any]) -> list[str]:
    guidance = [
        f"Use {preferences.get('pacingStyle', 'balanced')} pacing unless the creator overrides it.",
        f"Keep transition intensity {preferences.get('transitionIntensity', 'medium')}.",
        f"Use {preferences.get('captionDensity', 'balanced')} caption density.",
        f"Prefer {preferences.get('motionAggressiveness', 'cinematic_smooth')} motion.",
    ]
    if ai_summary.get("oftenRemovedTransitions"):
        guidance.append(f"Avoid transitions the creator removes often: {', '.join(list(ai_summary['oftenRemovedTransitions'])[:3])}.")
    if ai_summary.get("consistentlyLockedSections"):
        guidance.append(f"Preserve commonly locked sections: {', '.join(list(ai_summary['consistentlyLockedSections'])[:3])}.")
    return guidance


def _identity_explanation(reviews: list[dict[str, Any]], positive: list[dict[str, Any]], preferences: dict[str, str]) -> list[str]:
    return [
        f"Learned from {len(reviews)} local review(s), including {len(positive)} positive sample(s).",
        f"Pacing preference inferred as {preferences['pacingStyle']}.",
        f"Caption behavior inferred as {preferences['captionDensity']}.",
        "No data leaves this machine; the model is a local JSON preference profile.",
    ]


def _dataset_review_row(review: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": review.get("project"),
        "renderedVideo": review.get("renderedVideo"),
        "contentPlan": review.get("contentPlan"),
        "ratings": review.get("ratings", {}),
        "averageRating": review.get("averageRating"),
        "styleConsistency": review.get("styleConsistency", {}).get("overallScore"),
        "hookRetention": review.get("hookEffectiveness", {}).get("scores", {}).get("viewerRetentionPotential"),
        "preferenceHints": review.get("preferenceHints", {}),
    }


def _pacing_map(project_path: Path, project: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": str(project_path.resolve()),
        "averageRating": review.get("averageRating"),
        "scenes": [
            {
                "id": scene.get("id"),
                "start": scene.get("start"),
                "duration": scene.get("duration"),
                "transitionOut": _transition_type(scene),
                "layerCount": len(scene.get("layers", [])),
            }
            for scene in project.get("timeline", [])
        ],
    }


def _fingerprint(project: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(project, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _transition_type(scene: dict[str, Any]) -> str:
    transition = scene.get("transitionOut")
    if isinstance(transition, dict):
        return str(transition.get("type", "cut"))
    return "cut"


def _read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return json.loads(json.dumps(default if default is not None else {}))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup = path.with_suffix(path.suffix + ".corrupt")
        shutil.copy2(path, backup)
        return json.loads(json.dumps(default if default is not None else {}))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _unique(items: list[str]) -> list[str]:
    seen = set()
    values = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        values.append(item)
    return values


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
