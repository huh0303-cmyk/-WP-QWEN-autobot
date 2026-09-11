import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import meta_publish as m


class StaticPublishTests(unittest.TestCase):
    def test_static_formats_and_duplicate_receipts(self):
        for platform, meta, expected in [
            ('threads', {'media_type': 'TEXT'}, {'media_type': 'TEXT', 'text': 'Useful original post'}),
            ('threads', {'media_type': 'IMAGE', 'public_image_url': 'https://example.com/a.jpg'},
             {'media_type': 'IMAGE', 'image_url': 'https://example.com/a.jpg', 'text': 'Useful original post'}),
            ('instagram', {'media_type': 'IMAGE', 'public_image_url': 'https://example.com/a.jpg'},
             {'image_url': 'https://example.com/a.jpg', 'caption': 'Useful original post'}),
        ]:
            with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {
                'META_PUBLISH_ENABLED': 'true', 'SOCIAL_BRAND': 'TOPIK',
                'IG_USER_ID': '123', 'IG_ACCESS_TOKEN': 'test',
                'THREADS_USER_ID': '456', 'THREADS_ACCESS_TOKEN': 'test',
                'META_PUBLISH_STATE_DIR': folder}, clear=True):
                status = 'status' if platform == 'threads' else 'status_code'
                with patch.object(m, 'api', side_effect=[{'id': 'container'}, {status: 'FINISHED'}, {'id': 'post'}]) as api:
                    self.assertTrue(m.publish(platform, meta, 'Useful original post')['published'])
                    self.assertEqual(api.call_args_list[0].kwargs, expected)
                    self.assertTrue(m.publish(platform, meta, 'Useful original post')['duplicate'])
                    self.assertEqual(api.call_count, 3)

    def test_instagram_text_rejected_before_network(self):
        with patch.dict(os.environ, {'META_PUBLISH_ENABLED': 'true', 'IG_USER_ID': '123',
                                    'IG_ACCESS_TOKEN': 'test', 'SOCIAL_BRAND': 'TOPIK'}), patch.object(m, 'api') as api:
            with self.assertRaises(ValueError):
                m.publish('instagram', {'media_type': 'TEXT'}, 'caption')
            api.assert_not_called()
