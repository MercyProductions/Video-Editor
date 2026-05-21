from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from assets.resolver import AssetResolutionError, AssetResolver  # noqa: E402
from mvp.quick_create import create_quick_project  # noqa: E402
from parser.project_parser import ProjectParser  # noqa: E402
from quality.checker import run_quality_check  # noqa: E402
from schema.validator import ProjectValidationError, validate_project  # noqa: E402


class SmokeTests(unittest.TestCase):
    def test_sample_project_validates(self) -> None:
        data = json.loads((ROOT / "examples" / "project.json").read_text(encoding="utf-8"))
        validate_project(data)

    def test_bad_project_reports_schema_error(self) -> None:
        with self.assertRaises(ProjectValidationError) as error:
            validate_project({"project": {"width": 1280, "height": 720, "fps": 30, "duration": 5}, "assets": {}})

        message = str(error.exception)
        self.assertIn("Project JSON failed validation", message)
        self.assertIn("timeline", message)

    def test_missing_asset_error_is_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "missing_asset_project.json"
            project_path.write_text(
                json.dumps(
                    {
                        "project": {"width": 320, "height": 180, "fps": 24, "duration": 1},
                        "assets": {"clip": "assets/missing.mp4"},
                        "timeline": [
                            {
                                "id": "scene_1",
                                "start": 0,
                                "duration": 1,
                                "layers": [{"type": "video", "asset": "clip", "width": 320, "height": 180}],
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            project = ProjectParser().load(project_path)
            with self.assertRaises(AssetResolutionError) as error:
                AssetResolver(project).verify_referenced_assets()

            message = str(error.exception)
            self.assertIn("Asset 'clip' not found", message)
            self.assertIn("--generate-placeholders", message)

    def test_missing_audio_asset_error_is_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "missing_audio_project.json"
            project_path.write_text(
                json.dumps(
                    {
                        "project": {"width": 320, "height": 180, "fps": 24, "duration": 1},
                        "assets": {"music": "assets/missing.wav"},
                        "timeline": [
                            {
                                "id": "scene_1",
                                "start": 0,
                                "duration": 1,
                                "layers": [{"type": "text", "text": "Missing audio smoke test"}],
                            }
                        ],
                        "audio": [{"asset": "music", "start": 0}],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            project = ProjectParser().load(project_path)
            with self.assertRaises(AssetResolutionError) as error:
                AssetResolver(project).verify_referenced_assets()

            message = str(error.exception)
            self.assertIn("Asset 'music' not found", message)
            self.assertIn("audio", message)

    def test_quick_create_writes_valid_project_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "quick_create.json"
            project = create_quick_project(
                ROOT / "examples" / "assets" / "gameplay.mp4",
                music=ROOT / "examples" / "assets" / "song.wav",
                logo=ROOT / "examples" / "assets" / "logo.png",
                title="Smoke Test",
                caption="Quick create stays valid.",
                duration=4,
                output_path=output_path,
            )

            validate_project(project)
            validate_project(json.loads(output_path.read_text(encoding="utf-8")))
            self.assertGreaterEqual(len(project["timeline"]), 2)
            self.assertIn("recording", project["assets"])

    def test_sample_quality_check_has_no_issues(self) -> None:
        report = run_quality_check(ROOT / "examples" / "project.json")
        self.assertTrue(report["passed"])
        self.assertEqual([], report["issues"])


if __name__ == "__main__":
    unittest.main()
