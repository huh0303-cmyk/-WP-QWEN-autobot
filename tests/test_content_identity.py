import unittest

from automation_hub.content_identity import active_duplicate, canonical_source_id, is_similar_content, stable_content_id


class ContentIdentityTests(unittest.TestCase):
    def test_similar_title_or_body_is_blocked_per_destination(self):
        row = {"site_id": "tistory-a", "title": "Korea Visa Renewal Checklist", "content_html": "<p>Keep every required document and verify the current deadline.</p>"}
        self.assertTrue(is_similar_content(row, site_id="tistory-a", title="Korea Visa Renewal Checklist!", content_html="<p>Different</p>"))
        self.assertFalse(is_similar_content(row, site_id="tistory-b", title=row["title"], content_html=row["content_html"]))
    def test_url_fragment_and_trailing_slash_do_not_change_identity(self):
        left = canonical_source_id("HTTPS://Example.COM/post/#section")
        right = canonical_source_id("https://example.com/post")
        self.assertEqual(left, right)

    def test_content_id_is_stable_per_destination_and_source(self):
        first = stable_content_id("blogger", "blog_a", "https://example.com/post/")
        second = stable_content_id("blogger", "blog_a", "https://example.com/post")
        other_target = stable_content_id("blogger", "blog_b", "https://example.com/post")
        self.assertEqual(first, second)
        self.assertNotEqual(first, other_target)

    def test_active_duplicate_is_scoped_to_same_blogger(self):
        rows = [{"site_id": "blog_a", "source_keyword": "https://example.com/post", "status": "drafted", "job_id": "one"}]
        self.assertEqual(active_duplicate(rows, site_id="blog_a", source_id="https://example.com/post/")["job_id"], "one")
        self.assertIsNone(active_duplicate(rows, site_id="blog_b", source_id="https://example.com/post"))

    def test_failed_quality_does_not_permanently_lock_source(self):
        rows = [{"site_id": "blog_a", "source_keyword": "https://example.com/post", "status": "failed_quality"}]
        self.assertIsNone(active_duplicate(rows, site_id="blog_a", source_id="https://example.com/post"))


if __name__ == "__main__":
    unittest.main()
