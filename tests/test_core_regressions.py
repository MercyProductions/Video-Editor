from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from clips.selector import ClipAnalysis, _selection_warnings
from content.generator import _apply_source_quality_to_plan
from local_ai.engine import local_prompt_to_json
from parser.models import Layer, ProjectConfig, ProjectSettings, Scene
from preview.realtime import _cache_key
from schema.validator import validate_project


class ProductionHardeningTests(unittest.TestCase):
    def test_low_motion_source_is_warned_but_not_discarded(self) -> None:
        clip = ClipAnalysis(
            path="steady.mp4",
            duration=60,
            motionScore=0.001,
            loudnessScore=0.0,
            highlightScore=0.001,
            highlightStart=12,
            highlightDuration=4,
            highlightReason="steady context",
            tags=["dead_footage"],
            motionSpikes=[],
            silenceSections=[],
            killMomentScore=0,
            explosionScore=0,
            loudReactionScore=0,
            facecamReactionScore=0,
            deadFootage=True,
            warnings=[],
        )
        warnings = _selection_warnings([Path("steady.mp4")], [clip], [clip])
        self.assertIn("using the best steady footage instead of dropping the media", " ".join(warnings))

    def test_landscape_4k_source_promotes_archive_export(self) -> None:
        plan = {
            "contentBrief": {
                "targetPlatform": "youtube",
                "width": 1920,
                "height": 1080,
                "fps": 60,
                "exportPreset": "youtube_1080p",
            },
            "editingStyle": {},
            "warnings": [],
        }
        clip_report = {"selected": [{"path": str(ROOT / "does-not-need-to-exist.mp4"), "resolution": {"width": 3840, "height": 2160}}]}

        import content.generator as generator

        original = generator._best_source_resolution
        generator._best_source_resolution = lambda _report: {"width": 3840, "height": 2160}
        try:
            _apply_source_quality_to_plan(plan, clip_report)
        finally:
            generator._best_source_resolution = original

        self.assertEqual(plan["contentBrief"]["width"], 3840)
        self.assertEqual(plan["contentBrief"]["height"], 2160)
        self.assertEqual(plan["contentBrief"]["exportPreset"], "high_quality_archive")

    def test_realtime_preview_cache_key_changes_when_asset_changes(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            project_path = root / "project.json"
            asset_path = root / "clip.mp4"
            project_path.write_text("{}", encoding="utf-8")
            asset_path.write_bytes(b"first")
            scene = Scene(
                id="scene_1",
                start=0,
                duration=2,
                layers=[Layer("video", {"type": "video", "asset": "clip"})],
                raw={"id": "scene_1", "layers": [{"type": "video", "asset": "clip"}]},
            )
            project = ProjectConfig(
                path=project_path,
                root_dir=root,
                settings=ProjectSettings(width=1920, height=1080, fps=60, duration=2),
                assets={"clip": "clip.mp4"},
                timeline=[scene],
                audio=[],
                captions=[],
                metadata={},
                export_preset=None,
                raw={},
            )

            first = _cache_key(project, scene, 1.0, "balanced", "all")
            time.sleep(0.02)
            asset_path.write_bytes(b"changed")
            second = _cache_key(project, scene, 1.0, "balanced", "all")

        self.assertNotEqual(first, second)

    def test_local_prompt_to_json_fallback_outputs_valid_project(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "project.json"
            result = local_prompt_to_json(
                "Create a five second title card for a local desktop showcase.",
                output_path=output,
                preset="youtube_1080p",
            )
            self.assertTrue(output.exists())
            self.assertIn(result["source"], {"heuristic-local-engine", "ollama"})
            validate_project(result["project"])


if __name__ == "__main__":
    unittest.main()
