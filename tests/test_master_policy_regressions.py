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
    def test_wordpress_text_generator_has_no_gemini_fallback(self):
        source = (ROOT / "scripts" / "autopost_mega.py").read_text(encoding="utf-8")
        block = source.split("def generate_content_gemini(prompt):", 1)[1].split("def strip_code_fences", 1)[0]
        self.assertNotIn("gemini_client.models.generate_content", block)
        self.assertIn("Gemini fallback is prohibited", block)

    def test_platform_queue_fails_workflow_when_publisher_fails(self):
        source = (ROOT / "scripts" / "process_platform_queue.py").read_text(encoding="utf-8")
        self.assertIn("if not result.ok:", source)
        self.assertIn("processed queue job(s) failed", source)
    def test_newsroom_trim_cannot_cross_minimum(self):
        helpers = load_autopost_functions("newsroom_char_count", "trim_newsroom_html")
        body = "<p>" + ("검증된 사실 문장입니다. " * 180) + "</p>"
        trimmed = helpers["trim_newsroom_html"](body, target_chars=max(1500, 2000 - 220))
        length = helpers["newsroom_char_count"](trimmed)
        self.assertGreaterEqual(length, 1500)
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
