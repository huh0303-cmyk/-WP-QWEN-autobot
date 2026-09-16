import os
import tempfile
import unittest
from unittest.mock import patch

from control_center import orchestrator


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "orchestrator.sqlite3")
        self.env = patch.dict(os.environ, {
            "ORCHESTRATOR_STATE_DB": self.db,
            "ORCHESTRATOR_COOLDOWN_SECONDS": "60",
        }, clear=False)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_openai_quota_fails_over_to_claude(self):
        calls = []

        def openai(model, prompt):
            calls.append("openai")
            raise orchestrator.ProviderUnavailable("quota exhausted")

        def claude(model, prompt):
            calls.append("anthropic")
            return '{"title":"ok"}'

        with patch.dict(orchestrator.CALLERS, {"openai": openai, "anthropic": claude, "gemini": lambda m, p: "unused"}):
            text, meta = orchestrator.generate_text("hello", task_type="wordpress")

        self.assertEqual(text, '{"title":"ok"}')
        self.assertEqual(meta["provider"], "anthropic")
        self.assertEqual(calls, ["openai", "anthropic"])
        health = {row["provider"]: row for row in orchestrator.provider_health()}
        self.assertFalse(health["openai"]["available"])
        self.assertTrue(health["openai"]["failures"] >= 1)
        self.assertTrue(health["anthropic"]["available"])

    def test_provider_in_cooldown_is_skipped(self):
        orchestrator._record_failure("openai", orchestrator.ProviderUnavailable("rate limit"), cooldown=True)
        calls = []

        with patch.dict(orchestrator.CALLERS, {
            "openai": lambda m, p: calls.append("openai") or "bad",
            "anthropic": lambda m, p: calls.append("anthropic") or "ok",
            "gemini": lambda m, p: calls.append("gemini") or "unused",
        }):
            text, meta = orchestrator.generate_text("hello", task_type="wordpress")

        self.assertEqual(text, "ok")
        self.assertEqual(meta["provider"], "anthropic")
        self.assertEqual(calls, ["anthropic"])
        self.assertEqual(meta["attempts"][0]["result"], "cooldown")

    def test_blogger_prefers_gemini_then_claude(self):
        calls = []

        def gemini(model, prompt):
            calls.append("gemini")
            raise orchestrator.ProviderUnavailable("resource exhausted")

        def claude(model, prompt):
            calls.append("anthropic")
            return "ok"

        with patch.dict(orchestrator.CALLERS, {
            "openai": lambda m, p: calls.append("openai") or "unused",
            "anthropic": claude,
            "gemini": gemini,
        }):
            text, meta = orchestrator.generate_text("hello", task_type="blogger")

        self.assertEqual(text, "ok")
        self.assertEqual(meta["provider"], "anthropic")
        self.assertEqual(calls, ["gemini", "anthropic"])

    def test_all_fail_is_explicit(self):
        def fail(model, prompt):
            raise orchestrator.ProviderUnavailable("unavailable")

        with patch.dict(orchestrator.CALLERS, {"openai": fail, "anthropic": fail, "gemini": fail}):
            with self.assertRaises(orchestrator.OrchestratorExhausted):
                orchestrator.generate_text("hello", task_type="wordpress")


if __name__ == "__main__":
    unittest.main()
