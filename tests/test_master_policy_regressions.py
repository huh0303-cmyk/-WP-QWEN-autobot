import ast
import json
import re
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from automation_hub.youtube_registry import load_channels


ROOT = Path(__file__).resolve().parents[1]


def load_autopost_functions(*names):
    source = (ROOT / "scripts" / "autopost_mega.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {"BeautifulSoup": BeautifulSoup, "re": re}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "autopost_helpers", "exec"), namespace)
    return namespace


class MasterPolicyRegressionTests(unittest.TestCase):
    def test_site_editorial_playbook_covers_all_network_destinations(self):
        playbook = (ROOT / "config" / "SITE_EDITORIAL_PLAYBOOKS.md").read_text(encoding="utf-8")
        registry = json.loads((ROOT / "config" / "automation_hub_sites.json").read_text(encoding="utf-8"))
        tistory = json.loads((ROOT / "config" / "tistory_portfolio.json").read_text(encoding="utf-8"))
        wp_domains = [row["url"].split("//", 1)[-1].rstrip("/") for row in registry["sites"] if row["platform"] == "wordpress"]
        tistory_domains = [row["url"].split("//", 1)[-1].rstrip("/") for row in tistory["sites"]]
        assert all(domain in playbook for domain in wp_domains + tistory_domains)
        assert "### Blogger" in playbook

    def test_wordpress_text_generator_uses_gpt_primary(self):
        source = (ROOT / "scripts" / "autopost_mega.py").read_text(encoding="utf-8")
        block = source.split("def generate_content_gemini(prompt, use_gpt=False):", 1)[1].split(
            "def strip_code_fences", 1
        )[0]
        self.assertIn("_gemini_generate_text_raw(prompt)", block)
        self.assertIn("openai_generate_text(prompt", block)
        self.assertIn("use_gpt", block)

    def test_wordpress_default_goes_straight_to_gpt_never_calls_gemini(self):
        import sys
        from unittest.mock import patch

        sys.path.insert(0, str(ROOT / "scripts"))
        import autopost_mega as am

        with patch.object(am, "_gemini_generate_text_raw") as gemini_call, \
             patch("openai_text.openai_available", return_value=True), \
             patch("openai_text.openai_generate_text", return_value="gpt output") as gpt_call:
            result = am.generate_content_gemini("prompt", use_gpt=False)
        gemini_call.assert_not_called()
        gpt_call.assert_called_once()
        self.assertEqual(result, "gpt output")

    def test_wordpress_use_gpt_true_goes_straight_to_gpt_never_calls_gemini(self):
        import sys
        from unittest.mock import patch

        sys.path.insert(0, str(ROOT / "scripts"))
        import autopost_mega as am

        with patch.object(am, "_gemini_generate_text_raw") as gemini_call, \
             patch("openai_text.openai_available", return_value=True), \
             patch("openai_text.openai_generate_text", return_value="gpt output") as gpt_call:
            result = am.generate_content_gemini("prompt", use_gpt=True)
        gemini_call.assert_not_called()
        gpt_call.assert_called_once()
        self.assertEqual(result, "gpt output")

    def test_platform_queue_fails_workflow_when_publisher_fails(self):
        source = (ROOT / "scripts" / "process_platform_queue.py").read_text(encoding="utf-8")
        self.assertIn("if not result.ok:", source)
        self.assertIn("processed queue job(s) failed", source)

    def test_blogger_generation_requires_explicit_publish_input_and_logs_prequeue_failures(self):
        source = (ROOT / "scripts" / "queue_blogger_rewrite.py").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "blogger-rewrite.yml").read_text(encoding="utf-8")
        self.assertIn('os.environ.get("BLOGGER_PUBLISH_NOW", "false")', source)
        self.assertIn('error_code="NO_NEW_SOURCE"', source)
        self.assertIn('error_code="SOURCE_FETCH"', source)
        self.assertIn('"image_pass": True', source)
        self.assertIn("pass_no_image", source)
        self.assertIn("BLOGGER_PUBLISH_NOW: ${{ inputs.publish_now }}", workflow)
        self.assertIn("gh workflow run platform-publish-v2.yml", workflow)

    def test_blogger_oauth_is_separate_from_shared_drive_token(self):
        workflow = (ROOT / ".github" / "workflows" / "platform-publish-v2.yml").read_text(encoding="utf-8")
        setup = (ROOT / "scripts" / "setup_blogger_oauth_local.py").read_text(encoding="utf-8")
        for name in (
            "BLOGGER_GOOGLE_CLIENT_ID",
            "BLOGGER_GOOGLE_CLIENT_SECRET",
            "BLOGGER_GOOGLE_REFRESH_TOKEN",
        ):
            self.assertIn(name, workflow)
        self.assertIn('SCOPES = ["https://www.googleapis.com/auth/blogger"]', setup)
        self.assertNotIn("print(credentials.refresh_token)", setup)

    def test_newsroom_trim_cannot_cross_minimum(self):
        helpers = load_autopost_functions("newsroom_char_count", "trim_newsroom_html")
        body = "<p>" + ("검증된 사실 문장입니다. " * 180) + "</p>"
        trimmed = helpers["trim_newsroom_html"](body, target_chars=1500)
        length = helpers["newsroom_char_count"](trimmed)
        self.assertLessEqual(length, 1500)
        self.assertLessEqual(length, 1800)
        self.assertTrue(BeautifulSoup(trimmed, "html.parser").find("p"))

    def test_enabled_site_has_no_retired_identity(self):
        registry = json.loads((ROOT / "config" / "automation_hub_sites.json").read_text(encoding="utf-8"))
        enabled_domains = {s["url"].split("//", 1)[-1].strip("/") for s in registry["sites"] if s.get("enabled", True)}
        source = (ROOT / "scripts" / "autopost_mega.py").read_text(encoding="utf-8")
        self.assertIn("kskin365.com", enabled_domains)
        self.assertNotIn('"name": "Retired Site"', source)

    def test_reporting_registry_has_no_duplicates_or_retired_keys(self):
        scheduled = [(c.display_name, c.channel_id) for c in load_channels() if c.enabled]
        reporting = json.loads((ROOT / "config" / "youtube_reporting_channels.json").read_text(encoding="utf-8"))["channels"]
        combined = scheduled + [(c["display_name"], c["channel_id"]) for c in reporting if c.get("enabled", True)]
        self.assertEqual(len(combined), len({label for label, _ in combined}))
        self.assertEqual(len(combined), len({channel_id for _, channel_id in combined}))
        retired = {"SCIENCE_FACTS_TIMES", "CLASSICAL_TIMES", "MYTH_LEGEND_TIMES", "AMERICAN_ARCHIVE_TIMES", "CLASSIC_READS_TIMES"}
        self.assertFalse(any(any(key in label for key in retired) for label, _ in combined))


if __name__ == "__main__":
    unittest.main()
