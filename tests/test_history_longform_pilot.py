"""Offline safety and smoke tests for TODAY IN HISTORY pilot. No API/upload."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from scripts.history_longform_pilot import validate, render


class HistoryPilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.scenes = []
        for i, color in enumerate(("navy", "darkgreen")):
            image = self.root / f"still_{i}.png"
            Image.new("RGB", (960, 540), color).save(image)
            audio = self.root / f"voice_{i}.wav"
            if shutil.which("ffmpeg"):
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                                "-i", "sine=frequency=450:duration=1.5", str(audio)], check=True)
            self.scenes.append(dict(image=image.name, audio=audio.name,
                                    source_url="https://example.org/fixture",
                                    rights_basis="Synthetic fixture created by test",
                                    captions=[dict(start=0.05, end=1.25, text=f"Scene {i+1} test audio")]))
        self.manifest = dict(channel_key="history", language="en",
                             upload_visibility="private", episode_date="2026-11-12",
                             thumbnail_title="TWO HISTORICAL TURNING POINTS",
                             events=[
                                 dict(date="1954-11-12", fact_sources=["https://example.org/fixture"]),
                                 dict(date="1927-11-12", fact_sources=["https://example.org/fixture"]),
                             ], scenes=self.scenes)

    def test_demo_contract(self):
        if not shutil.which("ffprobe"):
            self.skipTest("ffprobe missing")
        self.assertEqual(validate(self.manifest, self.root, demo=True), [])

    def test_production_requires_40_distinct_and_12_minutes(self):
        if not shutil.which("ffprobe"):
            self.skipTest("ffprobe missing")
        errors = validate(self.manifest, self.root, demo=False)
        self.assertTrue(any("40-60" in x for x in errors))
        self.assertTrue(any("12-18" in x for x in errors))

    def test_rejects_duplicate_images_and_unlicensed_stills(self):
        if not shutil.which("ffprobe"):
            self.skipTest("ffprobe missing")
        self.manifest["scenes"][1]["image"] = self.manifest["scenes"][0]["image"]
        self.manifest["scenes"][1]["rights_basis"] = ""
        errors = validate(self.manifest, self.root, demo=True)
        self.assertTrue(any("duplicate" in x or "rights basis" in x for x in errors))

    def test_rejects_oversized_and_out_of_sync_caption(self):
        if not shutil.which("ffprobe"):
            self.skipTest("ffprobe missing")
        self.scenes[0]["captions"] = [dict(start=0, end=4, text="this caption is far too long for a documentary subtitle")]
        self.assertTrue(validate(self.manifest, self.root, demo=True))

    def test_demo_renders_three_thumbnails_and_srt(self):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("ffmpeg missing")
        try:
            from PIL import features
            if not features.check("freetype2"):
                self.skipTest("Pillow freetype missing")
            report = render(self.manifest, self.root, self.root / "out", demo=True)
        except RuntimeError as exc:
            if "subtitles" in str(exc) and "No such filter" in str(exc):
                self.skipTest("ffmpeg libass missing")
            raise
        self.assertEqual(report["status"], "rendered_for_review_not_uploaded")
        self.assertFalse(report["upload_performed"])
        self.assertTrue((self.root / "out" / "review.mp4").exists())
        self.assertEqual(len(list((self.root / "out").glob("thumbnail_*.jpg"))), 3)
        self.assertIn("00:00:00", (self.root / "out" / "captions.srt").read_text())


if __name__ == "__main__":
    unittest.main()
