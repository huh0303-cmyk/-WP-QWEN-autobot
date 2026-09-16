import unittest
from types import SimpleNamespace
from unittest.mock import patch

from control_center import generator_orchestrated


class OrchestratedGeneratorTests(unittest.TestCase):
    def test_generator_records_provider_metadata(self):
        site = SimpleNamespace(
            name="Test Site", theme="Test", language="en", persona="editor",
            tone="clear", target_chars=1200,
        )
        raw = '{"title":"A useful test title","meta_description":"This is a complete test meta description for the orchestrated article generation path and its metadata output.","content_html":"<p>hello</p>","labels":["test"],"image_queries":[]}'
        meta = {"provider": "anthropic", "model": "claude-test", "attempts": []}
        with patch.object(generator_orchestrated, "generate_text", return_value=(raw, meta)):
            result = generator_orchestrated.generate_article(site, "test")
        self.assertEqual(result["orchestrator"]["provider"], "anthropic")
        self.assertEqual(result["title"], "A useful test title")


if __name__ == "__main__":
    unittest.main()
