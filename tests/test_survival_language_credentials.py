import os, unittest
from unittest.mock import patch
from publish_survival_adjective_shorts import env_for
class LanguageCredentialIsolationTests(unittest.TestCase):
 def test_generic_oauth_fallback_is_rejected(self):
  with patch.dict(os.environ, {"YOUTUBE_OAUTH_REFRESH_TOKEN":"generic-token"}, clear=True):
   with self.assertRaisesRegex(RuntimeError, "LANGUAGE_EN"):
    env_for("en", "REFRESH_TOKEN")
