import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import economy_text as m


class EconomyTests(unittest.TestCase):
    def setUp(self):
        m._unavailable = False

    def test_flash_success_never_calls_gpt(self):
        response = Mock()
        response.json.return_value = {'candidates': [{'finishReason': 'STOP',
            'content': {'parts': [{'text': 'Complete article'}]}}]}
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch.object(m.requests, 'post', return_value=response) as post, \
                patch.object(m, 'openai_generate_text') as gpt, patch.object(m, 'Path', return_value=Path(folder)/'usage.jsonl'):
            self.assertEqual(m.generate_text('prompt'), 'Complete article')
            self.assertEqual(post.call_count, 1)
            self.assertEqual(post.call_args.kwargs['json']['generationConfig']['thinkingConfig']['thinkingBudget'], 0)
            gpt.assert_not_called()

    def test_failure_falls_back_once_and_opens_circuit(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch.object(m.requests, 'post', side_effect=m.requests.Timeout) as post, \
                patch.object(m, 'openai_available', return_value=True), \
                patch.object(m, 'openai_generate_text', return_value='fallback') as gpt:
            self.assertEqual(m.generate_text('prompt'), 'fallback')
            self.assertEqual(m.generate_text('next prompt'), 'fallback')
            self.assertEqual(post.call_count, 1)
            self.assertEqual(gpt.call_args.kwargs['max_retries'], 1)

    def test_truncated_response_is_not_accepted(self):
        response = Mock()
        response.json.return_value = {'candidates': [{'finishReason': 'MAX_TOKENS',
            'content': {'parts': [{'text': 'unfinished'}]}}]}
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch.object(m.requests, 'post', return_value=response), \
                patch.object(m, 'openai_available', return_value=False):
            with self.assertRaises(RuntimeError): m.generate_text('prompt')
