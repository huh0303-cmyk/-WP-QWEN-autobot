import unittest
import os
from datetime import datetime
from unittest.mock import Mock, patch

from automation_hub.blogger_adapter import BloggerPublisher
from automation_hub.interactive_adapters import InteractiveEditorPublisher
from automation_hub.publishing import PublishJob
from scripts import process_platform_queue


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

    def test_blogger_draft_returns_human_review_link(self):
        session = Mock()
        session.post.return_value = Mock(status_code=200, json=lambda: {"id": "44"}, text="")
        draft = PublishJob("job-2", "site-1", "Draft title", "<p>Draft</p>", ["guide"], publish_now=False)
        result = BloggerPublisher("site-1", "123", "token", session=session).publish(draft)
        self.assertEqual("drafted", result.status)
        self.assertEqual("https://www.blogger.com/blog/post/edit/123/44", result.public_url)
        self.assertEqual("true", session.post.call_args.kwargs["params"]["isDraft"])

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

    def test_blogger_platform_filter_does_not_select_naver(self):
        account = {"platform": "naver"}
        platform_filter = "blogger"
        self.assertNotEqual(platform_filter, account["platform"])

    def test_blogger_account_can_be_resolved_by_numeric_destination_id(self):
        account = {"site_id": "blogger_medical", "destination_id": "270775542645307723", "enabled": "ON"}
        by_site, by_destination = process_platform_queue._account_indexes([account])
        self.assertIs(account, by_site["blogger_medical"])
        self.assertIs(account, by_destination["270775542645307723"])

    @patch.dict(os.environ, {
        "BRAND2_GOOGLE_CLIENT_ID": "client", "BRAND2_GOOGLE_CLIENT_SECRET": "secret",
        "BRAND2_GOOGLE_REFRESH_TOKEN": "refresh",
    }, clear=False)
    @patch("scripts.process_platform_queue.requests.post")
    def test_named_auth_profile_uses_its_own_oauth_bundle(self, post):
        post.return_value = Mock(status_code=200, json=lambda: {"access_token": "token"})
        post.return_value.raise_for_status.return_value = None
        self.assertEqual("token", process_platform_queue._access_token("brand2"))
        sent = post.call_args.kwargs["data"]
        self.assertEqual("client", sent["client_id"])
        self.assertEqual("refresh", sent["refresh_token"])

    @patch.dict(os.environ, {
        "BLOGGER_GOOGLE_CLIENT_ID": "blogger-client",
        "BLOGGER_GOOGLE_CLIENT_SECRET": "blogger-secret",
        "BLOGGER_GOOGLE_REFRESH_TOKEN": "blogger-refresh",
        "GOOGLE_OAUTH_CLIENT_ID": "general-client",
        "GOOGLE_OAUTH_CLIENT_SECRET": "general-secret",
        "GOOGLE_OAUTH_REFRESH_TOKEN": "general-refresh",
    }, clear=False)
    @patch("scripts.process_platform_queue.requests.post")
    def test_default_blogger_profile_never_falls_back_to_general_oauth(self, post):
        post.return_value = Mock(status_code=200, json=lambda: {"access_token": "token"})
        post.return_value.raise_for_status.return_value = None
        self.assertEqual("token", process_platform_queue._access_token("default"))
        sent = post.call_args.kwargs["data"]
        self.assertEqual("blogger-client", sent["client_id"])
        self.assertEqual("blogger-refresh", sent["refresh_token"])


if __name__ == "__main__":
    unittest.main()
