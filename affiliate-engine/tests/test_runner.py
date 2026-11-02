import importlib.util
import unittest
from pathlib import Path


RUNNER_PATH = Path(__file__).resolve().parents[1] / "runner.py"
SPEC = importlib.util.spec_from_file_location("affiliate_runner", RUNNER_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class OfferSelectionTests(unittest.TestCase):
    def test_block_uses_sponsored_links_and_marker(self):
        block = runner.build_block([{"title": "Example", "url": "https://example.test/path?a=1"}])
        self.assertIn(runner.MARKER, block)
        self.assertIn('rel="sponsored nofollow noopener"', block)


if __name__ == "__main__":
    unittest.main()
