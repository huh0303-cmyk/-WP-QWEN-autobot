import unittest
from unittest.mock import Mock

from automation_hub.blogger_rewriter import attach_single_image, find_one_free_image, parse_rewrite_json, similarity


class BloggerRewriterTests(unittest.TestCase):
    def test_parse_json_code_fence(self):
        value = parse_rewrite_json('```json\n{"title":"New","content_html":"<p>Body</p>","image_query":"market","labels":[]}\n```')
        self.assertEqual("New", value["title"])

    def test_similarity_catches_near_copy(self):
        self.assertGreater(similarity("<p>The same useful article</p>", "<div>The same useful article</div>"), 0.95)

    def test_exactly_one_free_image_is_attached(self):
        session = Mock()
        session.get.return_value = Mock(status_code=200, json=lambda: {"photos": [{"src": {"large": "https://img/1.jpg"}, "url": "https://pexels/p", "photographer": "Kim"}]})
        image = find_one_free_image("market", pexels_key="key", session=session)
        html = attach_single_image("<p>Article</p>", image, "Alt")
        self.assertEqual(1, html.count("<img "))
        self.assertIn("Photo by Kim", html)

    def test_no_free_key_means_no_image_not_ai_fallback(self):
        self.assertIsNone(find_one_free_image("market"))


if __name__ == "__main__":
    unittest.main()
