import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from editorial_image_guard import strip_title_duplicate_lead_image
from fix_duplicate_hero_images_v2 import strip_leading_duplicate_block


class DuplicateLeadImageTests(unittest.TestCase):
    def test_removes_leading_paragraph_image_with_exact_title_alt(self):
        html = '<p><img src="pexels-photo-12004745.jpeg" alt="Korean Immigration Policy Updates 2026"/></p><p>Article text</p>'
        self.assertEqual(strip_title_duplicate_lead_image(html, "Korean Immigration Policy Updates 2026"),
                         "<p>Article text</p>")

    def test_removes_leading_figure_with_exact_title_alt(self):
        html = '<figure><img src="hero.jpg" alt="My Article"></figure><p>Text</p>'
        self.assertEqual(strip_title_duplicate_lead_image(html, "My Article"), "<p>Text</p>")

    def test_preserves_unrelated_lead_image(self):
        html = '<p><img src="wedding.jpg" alt="Wedding ceremony"/></p><p>Text</p>'
        self.assertEqual(strip_title_duplicate_lead_image(html, "Immigration policy"), html)

    def test_preserves_later_images_and_product_cards(self):
        html = '<p>Intro</p><p><img src="product.jpg" alt="Product"/></p>'
        self.assertEqual(strip_title_duplicate_lead_image(html, "Intro title"), html)

    def test_cleanup_detects_rehosted_same_bytes(self):
        html = '<p><img src="https://images.pexels.com/photo.jpg" alt="Title"></p><p>Text</p>'
        self.assertEqual(
            strip_leading_duplicate_block(html, "https://site.test/news-123.jpg",
                                          "same-sha", lambda _url: "same-sha"),
            "<p>Text</p>",
        )

    def test_cleanup_supports_paragraph_wrapped_image(self):
        html = '<p class="lead"><img src="https://site.test/hero.jpg" alt="Title"></p><p>Text</p>'
        self.assertEqual(
            strip_leading_duplicate_block(html, "https://site.test/hero.jpg"),
            "<p>Text</p>",
        )

    def test_cleanup_keeps_nonmatching_lead_and_later_images(self):
        html = '<p><img src="other.jpg" alt="Other"></p><p><img src="product.jpg"></p>'
        self.assertIsNone(strip_leading_duplicate_block(html, "hero.jpg", "sha", lambda _url: "different"))


if __name__ == "__main__":
    unittest.main()
