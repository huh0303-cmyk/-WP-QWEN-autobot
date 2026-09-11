import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RetryPolicyTests(unittest.TestCase):
    def test_active_youtube_upload_has_no_nested_client_retries(self):
        source = (ROOT / "scripts" / "youtube_publish_approved.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        retry_values = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "next_chunk":
                for keyword in node.keywords:
                    if keyword.arg == "num_retries" and isinstance(keyword.value, ast.Constant):
                        retry_values.append(keyword.value.value)
        self.assertTrue(retry_values)
        self.assertEqual({0}, set(retry_values))
        self.assertIn("max_retries = 3", source)

    def test_topik_review_upload_has_no_nested_client_retries(self):
        path = ROOT / "scripts" / "topik_quiz_shorts.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        retry_values = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "next_chunk":
                    for keyword in node.keywords:
                        if keyword.arg == "num_retries" and isinstance(keyword.value, ast.Constant):
                            retry_values.append(keyword.value.value)
        self.assertTrue(retry_values)
        self.assertTrue(all(value == 0 for value in retry_values))
        self.assertIn("max_retries = 3", source)

    def test_rankmath_check_fails_workflow_when_check_fails(self):
        workflow = (ROOT / ".github" / "workflows" / "daily-rankmath-check.yml").read_text(encoding="utf-8")
        self.assertNotIn("continue-on-error: true", workflow)


if __name__ == "__main__":
    unittest.main()
