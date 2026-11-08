import unittest
from automation_hub.seoulmall_widget import MARKER, append_widget, has_widget, render_widget
from automation_hub.coupang_partners import apply_footer

class SeoulMallWidgetTests(unittest.TestCase):
    def test_appends_after_existing_content(self):
        old = "<p>Article body</p>"
        new = append_widget(old)
        self.assertTrue(new.startswith(old))
        self.assertIn("https://influencers.coupang.com/s/seoulshop", new)
        self.assertTrue(has_widget(new))
    def test_is_idempotent(self):
        once = append_widget("<p>Article</p>")
        self.assertEqual(once, append_widget(once))
    def test_empty_content(self):
        self.assertIn(MARKER, append_widget(""))

    def test_shared_affiliate_footer_places_storefront_after_cards(self):
        rendered = apply_footer("<p>Article body</p>", "Health routine", "khealth365", "en")
        self.assertIn("LONDON-COUPANG-PARTNERS-START", rendered)
        self.assertIn(MARKER, rendered)
        self.assertGreater(rendered.index(MARKER), rendered.index("LONDON-COUPANG-PARTNERS-START"))
        self.assertEqual(rendered, append_widget(rendered))

if __name__ == "__main__":
    unittest.main()
