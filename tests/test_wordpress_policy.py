import unittest

from automation_hub.wordpress_policy import resolve_wordpress_post_status


class WordPressPolicyTests(unittest.TestCase):
    def test_regular_blog_publishes_once_explicitly_approved(self):
        # 2026-09-06 CEO decision: a regular WP site is no longer forced to
        # draft-only - the newsroom-only allowlist silently contradicted the
        # "no per-item review" design of daily-network-publish.yml and the
        # CEO's explicit ask for the network to actually go public.
        site = {"content_type": "blog", "mode": "blog"}
        self.assertEqual(
            "publish",
            resolve_wordpress_post_status(site, requested_status="publish", public_approved=True),
        )

    def test_regular_blog_stays_draft_without_explicit_approval(self):
        site = {"content_type": "blog", "mode": "blog"}
        self.assertEqual(
            "draft",
            resolve_wordpress_post_status(site, requested_status="publish", public_approved=False),
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
