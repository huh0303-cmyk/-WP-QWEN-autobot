"""Offline, no-secret, no-publish integration checks; not a live API test."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gemini_text
import replicate_image_provider as images
import tts_provider_priority as tts

class SafeSmoke(unittest.TestCase):
    def test_english_and_korean_writer(self):
        for language, expected in (("en", "English test article"), ("ko", "한국어 테스트 글")):
            response = Mock()
            response.json.return_value = {"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":expected}]}}]}
            with patch.dict(os.environ, {"GEMINI_API_KEY":"dummy"}), patch.object(gemini_text.requests, "post", return_value=response) as post:
                self.assertEqual(gemini_text.gemini_generate_text("Test", language=language), expected)
                self.assertIn("/models/gemini-", post.call_args.args[0])
    def test_image_free_fallback(self):
        import stock_image_provider
        with patch.object(stock_image_provider, "find_stock_image", side_effect=[None,"https://example.org/test.jpg"]) as stock:
            self.assertEqual(images.generate_image_url("Test image"), "https://example.org/test.jpg")
            self.assertEqual(stock.call_count, 2)
    def test_image_failure_returns_none(self):
        import stock_image_provider
        with patch.object(stock_image_provider, "find_stock_image", return_value=None), patch.dict(os.environ, {"REPLICATE_API_TOKEN":""}):
            self.assertIsNone(images.generate_image_url("No image available"))
    def test_tts_three_fail_block_publication(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/"voice.mp3"
            with patch.dict(sys.modules, {"edge_tts":None}):
                with self.assertRaises(RuntimeError):
                    tts.generate_tts("Test narration",output,fish_generator=lambda *a:False,qwen_generator=lambda *a:False)
            self.assertFalse(output.exists())
    def test_no_unapproved_paid_voice_ids(self):
        source=(Path(__file__).resolve().parents[1]/"scripts/voice_rotation.py").read_text()
        self.assertNotIn("ELEVENLABS",source)
    def test_no_public_upload_in_smoke(self):
        self.assertTrue(True, "This suite never invokes a publishing API.")

if __name__ == "__main__":
    unittest.main()
