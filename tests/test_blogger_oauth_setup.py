import json
import tempfile
import unittest
from pathlib import Path

from scripts.setup_blogger_oauth_local import SCOPES, load_desktop_client


class BloggerOAuthSetupTests(unittest.TestCase):
    def test_uses_only_blogger_scope(self):
        self.assertEqual(["https://www.googleapis.com/auth/blogger"], SCOPES)

    def test_accepts_desktop_client_json_without_exposing_token(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "client.json"
            path.write_text(
                json.dumps({"installed": {"client_id": "id", "client_secret": "secret"}}),
                encoding="utf-8",
            )
            self.assertEqual("id", load_desktop_client(path)["client_id"])

    def test_rejects_non_desktop_client_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "client.json"
            path.write_text(json.dumps({"web": {"client_id": "id"}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_desktop_client(path)


if __name__ == "__main__":
    unittest.main()
