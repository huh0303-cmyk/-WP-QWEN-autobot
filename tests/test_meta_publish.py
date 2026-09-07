import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import meta_publish as m

class MetaPublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {'META_PUBLISH_ENABLED':'true', 'SOCIAL_BRAND':'TOPIK',
            'IG_ACCESS_TOKEN':'secret', 'IG_USER_ID':'123', 'THREADS_ACCESS_TOKEN':'secret',
            'THREADS_USER_ID':'456', 'META_PUBLISH_STATE_DIR': self.temp.name}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.meta = {'public_video_url':'https://example.com/video.mp4'}

    def test_both_platforms_create_poll_publish_and_deduplicate(self):
        for platform, field, create, publish in [('instagram','status_code','media','media_publish'),
                                                 ('threads','status','threads','threads_publish')]:
            with patch.object(m, 'api', side_effect=[{'id':'container'}, {field:'IN_PROGRESS'},
                    {field:'FINISHED'}, {'id':'published'}]) as api, patch.object(m.time, 'sleep'):
                result = m.publish(platform,self.meta,'caption')
                self.assertTrue(result['published'])
                self.assertTrue(api.call_args_list[0].args[1].endswith('/'+create))
                self.assertTrue(api.call_args_list[-1].args[1].endswith('/'+publish))
                self.assertEqual(api.call_args_list[-1].kwargs, {'creation_id':'container'})
                self.assertTrue(m.publish(platform,self.meta,'caption')['duplicate'])
                self.assertEqual(api.call_count,4)

    def test_ambiguous_publish_is_not_retried(self):
        with patch.object(m,'api',side_effect=[{'id':'container'}, {'status':'FINISHED'}, RuntimeError('timeout')]):
            with self.assertRaises(RuntimeError): m.publish('threads',self.meta,'caption')
        with patch.object(m,'api') as api:
            with self.assertRaisesRegex(RuntimeError,'uncertain'): m.publish('threads',self.meta,'caption')
            api.assert_not_called()

    def test_preparation_is_not_success(self):
        os.environ['META_PUBLISH_ENABLED']='false'
        with patch.object(m,'api') as api:
            self.assertFalse(m.publish('instagram',self.meta,'caption')['ok'])
            api.assert_not_called()

    def test_missing_brand_credentials_never_fall_back(self):
        os.environ['SOCIAL_BRAND']='ENGLISH'
        with self.assertRaisesRegex(ValueError,'IG_ACCESS_TOKEN_ENGLISH'):
            m.publish('instagram',self.meta,'caption')

    def test_failed_container_never_publishes(self):
        with patch.object(m,'api',side_effect=[{'id':'container'},{'status':'ERROR'}]) as api:
            with self.assertRaisesRegex(RuntimeError,'ERROR'): m.publish('threads',self.meta,'caption')
            self.assertEqual(api.call_count,2)

    def test_processing_timeout_resumes_container(self):
        with patch.object(m,'api',side_effect=[{'id':'container'}]+[{'status':'IN_PROGRESS'}]*30), patch.object(m.time,'sleep'):
            with self.assertRaises(TimeoutError): m.publish('threads',self.meta,'caption')
        with patch.object(m,'api',side_effect=[{'status':'FINISHED'},{'id':'published'}]) as api:
            self.assertTrue(m.publish('threads',self.meta,'caption')['published'])
            self.assertEqual(api.call_count,2)

    def test_invalid_content_does_not_call_api(self):
        with patch.object(m,'api') as api:
            for meta, caption in [({'public_video_url':'file:///tmp/x'},'caption'),(self.meta,''),(self.meta,'x'*501)]:
                with self.assertRaises(ValueError): m.publish('threads',meta,caption)
            api.assert_not_called()

    def test_corrupt_receipt_fails_closed(self):
        with patch.object(m,'api',side_effect=[{'id':'container'},{'status':'ERROR'}]):
            with self.assertRaises(RuntimeError): m.publish('threads',self.meta,'caption')
        next(Path(self.temp.name).glob('*.json')).write_text('invalid')
        with patch.object(m,'api') as api:
            with self.assertRaises(ValueError): m.publish('threads',self.meta,'caption')
            api.assert_not_called()

if __name__ == '__main__': unittest.main()
