import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.vocabulary_tts import synthesize


class Response:
    headers = {'character-cost': '1'}
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return b'test-audio' * 100


class VocabularySpeechTests(unittest.TestCase):
    @patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test-only'})
    def test_cached_clip_does_not_bill_again_and_language_changes_identity(self):
        calls = []
        def fake(request, **kwargs):
            calls.append(json.loads(request.data))
            return Response()
        with tempfile.TemporaryDirectory() as folder:
            first = synthesize('school', 'en', folder, opener=fake)
            self.assertEqual(first, synthesize('school', 'en', folder, opener=fake))
            self.assertEqual(len(calls), 1)
            synthesize('school', 'de', folder, opener=fake)
            self.assertEqual([x['language_code'] for x in calls], ['en', 'de'])

    @patch.dict(os.environ, {'ELEVENLABS_API_KEY': 'test-only'})
    def test_ambiguous_failure_prevents_automatic_second_charge(self):
        def fail(*args, **kwargs): raise TimeoutError('ambiguous')
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(TimeoutError):
                synthesize('school', 'en', folder, opener=fail)
            self.assertEqual(len(list(Path(folder).glob('*.pending'))), 1)
            with self.assertRaises(FileExistsError):
                synthesize('school', 'en', folder, opener=fail)

    def test_missing_key_fails_without_silent_audio(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'no silent fallback'):
                synthesize('school', 'en', folder)


if __name__ == '__main__': unittest.main()
