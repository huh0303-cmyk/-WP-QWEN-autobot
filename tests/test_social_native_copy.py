import os
import pathlib
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch


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

    def test_error_sanitizer_redacts_query_tokens_and_known_secrets(self):
        old_token = social_publish.FB_PAGE_ACCESS_TOKEN
        try:
            social_publish.FB_PAGE_ACCESS_TOKEN = "page-secret-value"
            message = social_publish.sanitize_error(
                "400 https://graph.facebook.com/video?access_token=page-secret-value&phase=start"
            )
        finally:
            social_publish.FB_PAGE_ACCESS_TOKEN = old_token

        self.assertNotIn("page-secret-value", message)
        self.assertIn("access_token=[REDACTED]", message)

    def test_facebook_page_credentials_are_brand_suffixed(self):
        # 2026-09-07: mirrors meta_publish.account()'s convention so the
        # three Facebook Pages (TOPIK/ENGLISH/LANGUAGE) never cross-post to
        # the wrong page - TOPIK stays on the bare env var names.
        env = {
            "FB_PAGE_ACCESS_TOKEN": "topik-token", "FB_PAGE_ID": "topik-id",
            "FB_PAGE_ACCESS_TOKEN_ENGLISH": "en-token", "FB_PAGE_ID_ENGLISH": "en-id",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("SOCIAL_BRAND", None)
            self.assertEqual(social_publish.facebook_page_credentials(), ("topik-token", "topik-id"))
            os.environ["SOCIAL_BRAND"] = "ENGLISH"
            self.assertEqual(social_publish.facebook_page_credentials(), ("en-token", "en-id"))
            os.environ["SOCIAL_BRAND"] = "LANGUAGE"
            self.assertEqual(social_publish.facebook_page_credentials(), ("", ""))
            os.environ["SOCIAL_BRAND"] = "unknown"
            with self.assertRaises(ValueError):
                social_publish.facebook_page_credentials()
        os.environ.pop("SOCIAL_BRAND", None)


if __name__ == "__main__":
    unittest.main()
