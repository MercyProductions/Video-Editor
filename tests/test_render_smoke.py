from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from media.compat import analyze_media  # noqa: E402
from mvp.quick_create import create_quick_project  # noqa: E402
from parser.project_parser import ProjectParser  # noqa: E402
from renderer.renderer import VideoRenderer  # noqa: E402


class RenderSmokeTests(unittest.TestCase):
    def test_sample_project_preview_renders_in_isolated_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = ProjectParser().load(ROOT / "examples" / "project.json")
            output_path = Path(temp_dir) / "sample_preview.mp4"

            rendered = VideoRenderer(project, output_path=output_path, quality="preview", use_cache=True, resume=True).render()

            self.assert_rendered_mp4(rendered, expected_duration=project.settings.duration)
            report = json.loads((Path(temp_dir) / "render_report.json").read_text(encoding="utf-8"))
            self.assertEqual(str(rendered.resolve()), report["output"])
            self.assertEqual(2, report["sceneCount"])
            self.assertEqual([], report["missingAssets"])

    def test_quick_create_project_preview_renders(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = self.create_quick_project(Path(temp_dir) / "quick_create_preview.json")
            output_path = Path(temp_dir) / "quick_create_preview.mp4"

            rendered = VideoRenderer(project, output_path=output_path, quality="preview", use_cache=True, resume=True).render()

            self.assert_rendered_mp4(rendered, expected_duration=project.settings.duration)
            report = json.loads((Path(temp_dir) / "render_report.json").read_text(encoding="utf-8"))
            self.assertEqual("preview", report["quality"])
            self.assertEqual([], report["missingAssets"])

    def test_quick_create_project_final_renders(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = self.create_quick_project(Path(temp_dir) / "quick_create_final.json")
            output_path = Path(temp_dir) / "quick_create_final.mp4"

            rendered = VideoRenderer(project, output_path=output_path, quality="final", use_cache=True, resume=True).render()

            self.assert_rendered_mp4(rendered, expected_duration=project.settings.duration)
            report = json.loads((Path(temp_dir) / "render_report.json").read_text(encoding="utf-8"))
            self.assertEqual("final", report["quality"])
            self.assertEqual([], report["missingAssets"])

    def create_quick_project(self, project_path: Path):
        create_quick_project(
            ROOT / "examples" / "assets" / "gameplay.mp4",
            music=ROOT / "examples" / "assets" / "song.wav",
            logo=ROOT / "examples" / "assets" / "logo.png",
            title="Quick Render Smoke",
            caption="Quick create renders to MP4.",
            duration=4,
            width=640,
            height=360,
            fps=24,
            output_path=project_path,
        )
        return ProjectParser().load(project_path)

    def assert_rendered_mp4(self, path: Path, *, expected_duration: float, tolerance: float = 0.4) -> None:
        self.assertTrue(path.exists(), f"Expected rendered file to exist: {path}")
        self.assertGreater(path.stat().st_size, 0, f"Expected rendered file to be non-empty: {path}")
        self.assertEqual(".mp4", path.suffix.lower())

        media = analyze_media(path)
        actual_duration = float(media.get("duration") or 0)
        self.assertGreater(actual_duration, 0, f"Expected detectable media duration for: {path}")
        self.assertLessEqual(
            abs(actual_duration - expected_duration),
            tolerance,
            f"Rendered duration {actual_duration}s differs from expected {expected_duration}s for {path}",
        )


if __name__ == "__main__":
    unittest.main()
