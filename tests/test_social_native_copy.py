import pathlib
import sys
import unittest
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import social_publish
import topik_quiz_shorts


class SocialNativeCopyTests(unittest.TestCase):
    def test_fallback_copy_is_distinct_for_every_platform(self):
        copy = topik_quiz_shorts.normalize_platform_copy({}, "TOPIK Words")
        captions = []
        for platform in ("tiktok", "instagram", "facebook", "threads"):
            native = copy["platform_copy"][platform]
            captions.append((native["hook"], native["caption"], native["cta"]))
        self.assertEqual(len(set(captions)), 4)

    def test_fingerprint_is_scoped_to_platform(self):
        meta = {"video_path": "video.mp4", "youtube_title": "Quiz", "platform_copy": {}}
        self.assertNotEqual(
            social_publish.content_fingerprint(meta, "tiktok"),
            social_publish.content_fingerprint(meta, "instagram"),
        )

    def test_recommended_times_are_staggered_and_stable(self):
        meta = {"created_at": datetime(2026, 8, 27, tzinfo=timezone.utc).isoformat(), "youtube_title": "Quiz"}
        first = social_publish.recommended_publish_times(meta)
        self.assertEqual(first, social_publish.recommended_publish_times(meta))
        self.assertEqual(len(set(first.values())), 5)


if __name__ == "__main__":
    unittest.main()
