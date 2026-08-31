import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ceo_sns_probe import format_metric, safe_error


class ProbeTests(unittest.TestCase):
    def test_unknown_not_zero(self):
        self.assertEqual(format_metric(None), "미집계(증감 미확인)")
        self.assertEqual(format_metric(0), "0(증감 미확인)")
        self.assertEqual(format_metric(1815, 0), "1,815(0)")
        self.assertEqual(format_metric(1815, -12), "1,815(-12)")
        self.assertEqual(format_metric(1815, 12), "1,815(+12)")

    def test_credentials_redacted(self):
        with patch.dict(os.environ, {"FB_PAGE_ACCESS_TOKEN": "test-sensitive-value"}):
            self.assertNotIn("test-sensitive-value", safe_error("bad test-sensitive-value"))
            self.assertNotIn("https://", safe_error("https://x/?access_token=partial"))
        self.assertEqual(safe_error("THREADS_ACCESS_TOKEN 없음"), "THREADS_ACCESS_TOKEN 없음")


if __name__ == "__main__":
    unittest.main()
