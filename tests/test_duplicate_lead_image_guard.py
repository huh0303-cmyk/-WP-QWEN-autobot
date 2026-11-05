import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from editorial_image_guard import strip_title_duplicate_lead_image


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


if __name__ == "__main__":
    unittest.main()
