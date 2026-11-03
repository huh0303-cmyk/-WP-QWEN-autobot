import os
import unittest
from unittest.mock import patch

from scripts.social_publish import language_channel_identity


class SocialPublishLanguageRoutingTests(unittest.TestCase):
    def test_english_uses_english_channel_and_token(self):
        env = {
            "YOUTUBE_OAUTH_REFRESH_TOKEN_LANGUAGE_EN": "english-token",
            "TARGET_LANG": "en",
        }
        with patch.dict(os.environ, env, clear=True):
            lang, channel, token = language_channel_identity({"lang": "en"})
        self.assertEqual(lang, "en")
        self.assertEqual(channel, "UCrjkKWMHzAAvpLIFgHnwcWg")
        self.assertEqual(token, "english-token")

    def test_japanese_requires_language_specific_token(self):
        env = {"YOUTUBE_OAUTH_REFRESH_TOKEN": "generic-token", "TARGET_LANG": "ja"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(RuntimeError, "YOUTUBE_OAUTH_REFRESH_TOKEN_LANGUAGE_JA"):
                language_channel_identity({"lang": "ja"})

    def test_target_language_mismatch_is_blocked(self):
        env = {"YOUTUBE_OAUTH_REFRESH_TOKEN_LANGUAGE_JA": "japanese-token", "TARGET_LANG": "en"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Content language mismatch"):
                language_channel_identity({"lang": "ja"})

    def test_japanese_maps_to_japanese_channel(self):
        env = {"YOUTUBE_OAUTH_REFRESH_TOKEN_LANGUAGE_JA": "japanese-token", "TARGET_LANG": "ja"}
        with patch.dict(os.environ, env, clear=True):
            _, channel, token = language_channel_identity({"lang": "ja"})
        self.assertEqual(channel, "UCOWoNH_d6p45ywQ6W0Z1Jng")
        self.assertEqual(token, "japanese-token")


if __name__ == "__main__":
    unittest.main()
