import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from automation_hub.blogger_adapter import BloggerPublisher
from automation_hub.interactive_adapters import InteractiveEditorPublisher
from automation_hub.publishing import PublishJob


class PlatformPublisherTests(unittest.TestCase):
    def setUp(self):
        self.job = PublishJob("job-1", "site-1", "A useful title", "<p>Useful article</p>", ["guide"])

    @patch("automation_hub.blogger_adapter.verify_publication")
    def test_blogger_publishes_and_verifies_real_url(self, verify):
        session = Mock()
        session.post.return_value = Mock(status_code=200, json=lambda: {"id": "44", "url": "https://demo.blogspot.com/real.html"})
        session.post.return_value.text = ""
        verify.return_value = Mock(ok=True, final_url="https://demo.blogspot.com/real.html")
        result = BloggerPublisher("site-1", "123", "token", session=session).publish(self.job)
        self.assertTrue(result.ok)
        self.assertEqual("published", result.status)
        self.assertEqual("44", result.remote_id)
        self.assertEqual("false", session.post.call_args.kwargs["params"]["isDraft"])

    def test_blogger_fails_closed_without_credentials(self):
        result = BloggerPublisher("site-1", "", "").publish(self.job)
        self.assertFalse(result.ok)
        self.assertEqual("auth_required", result.status)

    def test_naver_never_claims_false_api_success(self):
        result = InteractiveEditorPublisher("naver", "site-1", "https://blog.naver.com").publish(self.job)
        self.assertFalse(result.ok)
        self.assertEqual("local_login_required", result.status)
        self.assertEqual("official_write_api_unavailable", result.error_code)

    def test_tistory_never_claims_false_api_success(self):
        result = InteractiveEditorPublisher("tistory", "site-1", "https://www.tistory.com").publish(self.job)
        self.assertFalse(result.ok)
        self.assertEqual("local_login_required", result.status)

    def test_result_timestamp_is_korean_time(self):
        result = InteractiveEditorPublisher("naver", "site-1", "https://blog.naver.com").publish(self.job)
        completed = datetime.fromisoformat(result.completed_at)
        self.assertEqual(9 * 60, int(completed.utcoffset().total_seconds() / 60))


if __name__ == "__main__":
    unittest.main()
