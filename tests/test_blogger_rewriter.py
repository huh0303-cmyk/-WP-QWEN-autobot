import re
import unittest
from unittest.mock import Mock

from automation_hub.blogger_rewriter import FreeImage, attach_single_image, blogger_quality_score, extract_http_links, find_one_free_image, image_is_relevant, normalize_rewrite_format, parse_rewrite_json, plain_text, similarity
from scripts.blogger_search_description import build_search_description


class BloggerRewriterTests(unittest.TestCase):
    def test_unlock_title_is_blocked_by_blogger_quality_gate(self):
        source_url = "https://example.com/korea-travel"
        content = (
            '<p>A direct answer for Korea travel planning.</p>'
            '<h2>Before departure</h2><p>' + ('Check current requirements carefully. ' * 35) + '</p>'
            '<h2>Transport planning</h2><p>' + ('Compare routes and timing before booking. ' * 35) + '</p>'
            '<h2>Final checklist</h2><p>' + ('Confirm reservations and official details. ' * 35) + '</p>'
            f'<p><a href="{source_url}">Detailed source</a></p>'
        )
        article = {
            "title": "Unlocking Korea Travel Planning",
            "meta_description": "Practical source-led Korea travel planning guidance covering transport, reservations, timing, and essential checks.",
            "content_html": content,
            "labels": ["Korea", "Travel", "Planning", "Transport", "Booking", "Hotels", "Seoul", "Routes"],
        }
        _, failures, _ = blogger_quality_score(article, source_title="Korea Travel Planning", source_url=source_url, source_html="<p>Short source.</p>", target_chars=2400)
        self.assertTrue(any("mass-produced AI title formula" in item for item in failures))

    def test_search_description_is_100_to_119_characters(self):
        for keyword in ("한국 보험 가입 전 확인사항", "Korea housing contract checklist"):
            description = build_search_description(keyword)
            self.assertGreaterEqual(len(description), 100)
            self.assertLess(len(description), 120)
    def test_normalize_rewrite_format_clips_generated_fields(self):
        paragraph = "<p>" + ("useful Korea planning detail " * 30) + "</p>"
        article = {
            "title": "A very long Korea planning title " * 4,
            "meta_description": "A practical source-led description " * 8,
            "content_html": "<h2>Plan</h2>" + paragraph * 8,
        }
        result = normalize_rewrite_format(article, target_chars=1200)
        self.assertLessEqual(len(result["title"]), 70)
        self.assertLessEqual(len(result["meta_description"]), 120)
        self.assertLessEqual(len(re.sub(r"\s+", "", plain_text(result["content_html"]))), 1620)

    def test_normalize_preserves_source_and_ymyl_tail(self):
        source_url = "https://example.com/source"
        filler = "<p>" + ("recovery planning detail " * 25) + "</p>"
        article = {
            "title": "Medical recovery planning in Korea",
            "meta_description": "A practical medical recovery guide for international patients planning safe accommodation and follow-up care in Korea.",
            "content_html": "<h2>Plan</h2>" + filler * 8 + f'<p>Read the <a href="{source_url}">original guide</a>.</p><p>As of 2026, rules can change. Consult your clinician. This is not medical advice.</p>',
        }
        result = normalize_rewrite_format(article, target_chars=1200, source_url=source_url, ymyl=True)
        self.assertIn(source_url, result["content_html"])
        self.assertIn("As of 2026", result["content_html"])
        self.assertFalse(result["content_html"].rstrip().endswith("</h2>"))

    def test_parse_json_code_fence(self):
        value = parse_rewrite_json('```json\n{"title":"New","meta_description":"A practical Korea guide with current steps, source-led checks, and clear details for readers planning their next move.","content_html":"<p>Body</p>","image_queries":[],"labels":["Korea","Guide","Planning","Travel","Booking","Transport","Hotels","Seoul"]}\n```')
        self.assertEqual("New", value["title"])

    def test_similarity_catches_near_copy(self):
        self.assertGreater(similarity("<p>The same useful article</p>", "<div>The same useful article</div>"), 0.95)

    def test_verified_links_are_extracted_without_duplicates(self):
        html = '<a href="https://example.gov/a">A</a><a href="https://example.gov/a">Again</a>'
        self.assertEqual(["https://example.gov/a"], extract_http_links(html))

    def test_exactly_one_free_image_is_attached(self):
        session = Mock()
        session.get.return_value = Mock(status_code=200, json=lambda: {"photos": [{"src": {"large": "https://img/1.jpg"}, "url": "https://pexels/p", "photographer": "Kim"}]})
        image = find_one_free_image("market", pexels_key="key", session=session)
        html = attach_single_image("<p>Article</p>", image, "Alt")
        self.assertEqual(1, html.count("<img "))
        self.assertIn("Photo by Kim", html)

    def test_no_free_key_means_no_image_not_ai_fallback(self):
        self.assertIsNone(find_one_free_image("market"))

    def test_irrelevant_stock_image_is_rejected(self):
        image = FreeImage("https://img", "https://page", "credit", "Pexels", "snowy mountain landscape")
        self.assertFalse(image_is_relevant(image, query="Korea visa application", title="Korea Visa Application Steps"))

    def test_blogger_quality_gate_can_pass_without_images(self):
        source_url = "https://example.com/korea-travel"
        content = (
            '<p>A direct answer for Korea travel planning.</p>'
            '<h2>Before departure</h2><p>' + ('Check current official requirements carefully. ' * 20) + '</p>'
            '<h2>Transport planning</h2><p>' + ('Compare routes, timing, and costs before booking. ' * 20) + '</p>'
            '<h2>Final checklist</h2><p>' + ('Confirm reservations and keep the official details accessible. ' * 20) + '</p>'
            f'<p><a href="{source_url}">Detailed Korea travel source</a></p>'
        )
        meta_description = "Practical, source-led guidance for planning a Korea trip, covering transport, checklists, and booking timing."
        article = {"title": "Korea Travel Planning: Practical Steps", "meta_description": meta_description, "content_html": content, "labels": ["Korea", "Travel", "Planning", "Transport", "Booking", "Hotels", "Seoul", "Routes"]}
        score, failures, _ = blogger_quality_score(article, source_title="Korea Travel Planning", source_url=source_url, source_html="<p>Short original source.</p>", target_chars=2400)
        self.assertGreaterEqual(score, 80, failures)


if __name__ == "__main__":
    unittest.main()
