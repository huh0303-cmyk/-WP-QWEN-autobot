import unittest
from unittest.mock import Mock, patch

from scripts.london_four_agent_pipeline import _publish_wordpress_native


class TestLondonNativeWordPressPublisher(unittest.TestCase):
    def test_draft_uses_wordpress_rest_without_vps(self):
        state = {
            "site_id": "wp_ktrip365",
            "run_id": "native-test-1",
            "article": {
                "title": "Native publisher test",
                "content_html": "<p>test</p>",
                "meta_description": "test",
                "tags": ["test"],
            },
            "category_assignment": {"status": "ok", "id": 12, "name": "Travel"},
            "image": {"url": ""},
        }
        profile = {
            "wordpress": {
                "url": "https://example.com",
                "secret_name": "TEST_WP_PASSWORD",
            }
        }
        response = Mock(status_code=201)
        response.json.return_value = {
            "id": 123,
            "link": "https://example.com/native-publisher-test/",
            "status": "draft",
        }

        with patch.dict("os.environ", {"TEST_WP_PASSWORD": "secret"}):
            with patch("scripts.create_manual_wp_draft.resolve_tag_ids", return_value=[]):
                with patch("scripts.london_four_agent_pipeline.requests.post", return_value=response) as post:
                    result = _publish_wordpress_native(state, profile, public=False)

        self.assertEqual(result["publisher"], "github-native")
        self.assertEqual(result["post_id"], 123)
        self.assertEqual(result["status"], "draft")
        self.assertEqual(post.call_args.kwargs["json"]["status"], "draft")
        self.assertEqual(post.call_args.kwargs["json"]["categories"], [12])


if __name__ == "__main__":
    unittest.main()
