import unittest
from automation_hub.seoulmall_widget import MARKER, append_widget, has_widget, render_widget

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

if __name__ == "__main__":
    unittest.main()
