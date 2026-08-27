import unittest

from automation_hub.wordpress_policy import resolve_wordpress_post_status


class WordPressPolicyTests(unittest.TestCase):
    def test_regular_blog_is_draft_even_when_publish_requested(self):
        site = {"content_type": "blog", "mode": "blog"}
        self.assertEqual(
            "draft",
            resolve_wordpress_post_status(site, requested_status="publish", public_approved=True),
        )

    def test_newsroom_requires_explicit_public_approval(self):
        site = {"content_type": "news_ko", "mode": "news"}
        self.assertEqual("draft", resolve_wordpress_post_status(site, requested_status="publish", public_approved=False))
        self.assertEqual("publish", resolve_wordpress_post_status(site, requested_status="publish", public_approved=True))

    def test_draft_request_never_escalates(self):
        site = {"content_type": "news_en", "mode": "news_en"}
        self.assertEqual("draft", resolve_wordpress_post_status(site, requested_status="draft", public_approved=True))


if __name__ == "__main__":
    unittest.main()
