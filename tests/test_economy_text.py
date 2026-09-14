import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import economy_text as m


def _gemini_response(text='Complete article', finish='STOP'):
    response = Mock()
    response.json.return_value = {'candidates': [{'finishReason': finish,
        'content': {'parts': [{'text': text}]}}]}
    return response


class EconomyTests(unittest.TestCase):
    def setUp(self):
        m._gemini_unavailable = False
        m._gpt_unavailable = False

    def test_first_attempt_is_randomly_gemini_or_gpt(self):
        """2026-09-12 (user directive): random pick per article, not always Flash-first."""
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch.object(m, '_try_gemini', return_value='from-gemini') as gemini, \
                patch.object(m, '_try_gpt', return_value='from-gpt') as gpt:
            for _ in range(60):
                m._gemini_unavailable = False
                m._gpt_unavailable = False
                m.generate_text('prompt')
        self.assertTrue(gemini.called)
        self.assertTrue(gpt.called)

    def test_gemini_success_never_calls_gpt(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch('random.sample', return_value=['gemini', 'gpt']), \
                patch.object(m.requests, 'post', return_value=_gemini_response()) as post, \
                patch.object(m, 'openai_generate_text') as gpt, patch.object(m, 'Path', return_value=Path(folder)/'usage.jsonl'):
            self.assertEqual(m.generate_text('prompt'), 'Complete article')
            self.assertEqual(post.call_count, 1)
            gpt.assert_not_called()

    def test_gemini_failure_falls_back_to_gpt_same_call(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch('random.sample', return_value=['gemini', 'gpt']), \
                patch.object(m.requests, 'post', side_effect=m.requests.Timeout), \
                patch.object(m, 'openai_available', return_value=True), \
                patch.object(m, 'openai_generate_text', return_value='fallback') as gpt:
            self.assertEqual(m.generate_text('prompt'), 'fallback')
            self.assertEqual(gpt.call_args.kwargs['max_retries'], 1)

    def test_gpt_failure_falls_back_to_gemini_same_call(self):
        """Mutual fallback: when GPT is picked first and fails, Gemini Flash covers it."""
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch('random.sample', return_value=['gpt', 'gemini']), \
                patch.object(m, 'openai_available', return_value=True), \
                patch.object(m, 'openai_generate_text', side_effect=RuntimeError('quota')), \
                patch.object(m.requests, 'post', return_value=_gemini_response('from Gemini')):
            self.assertEqual(m.generate_text('prompt'), 'from Gemini')

    def test_once_unavailable_a_provider_is_not_probed_again_this_process(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch('random.sample', return_value=['gemini', 'gpt']), \
                patch.object(m.requests, 'post', side_effect=m.requests.Timeout) as post, \
                patch.object(m, 'openai_available', return_value=True), \
                patch.object(m, 'openai_generate_text', return_value='fallback') as gpt:
            self.assertEqual(m.generate_text('prompt'), 'fallback')
            self.assertEqual(m.generate_text('next prompt'), 'fallback')
            self.assertEqual(post.call_count, 1)

    def test_truncated_response_is_not_accepted(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch('random.sample', return_value=['gemini', 'gpt']), \
                patch.object(m.requests, 'post', return_value=_gemini_response('unfinished', finish='MAX_TOKENS')), \
                patch.object(m, 'openai_available', return_value=False):
            with self.assertRaises(RuntimeError):
                m.generate_text('prompt')

    def test_force_gpt_skips_gemini_entirely(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch.object(m.requests, 'post') as post, \
                patch.object(m, 'openai_available', return_value=True), \
                patch.object(m, 'openai_generate_text', return_value='forced-gpt') as gpt:
            self.assertEqual(m.generate_text('prompt', force_gpt=True), 'forced-gpt')
            post.assert_not_called()

    def test_both_providers_unavailable_raises_for_retry(self):
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(m, 'openai_available', return_value=False):
            with self.assertRaises(RuntimeError):
                m.generate_text('prompt')


if __name__ == '__main__':
    unittest.main()
