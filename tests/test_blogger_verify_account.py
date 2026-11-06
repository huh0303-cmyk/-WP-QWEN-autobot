import unittest
from scripts.blogger_verify_account import build_report

class BloggerVerifyReportTests(unittest.TestCase):
    def test_all_ids_visible_but_custom_domain_differences_are_warnings(self):
        configured = [{"site_id": f"site_{i}", "destination_id": str(i), "url": f"https://blog{i}.blogspot.com"} for i in range(33)]
        blogs = [{"id": str(i), "url": ("https://custom.example/" if i == 4 else f"https://blog{i}.blogspot.com")} for i in range(33)]
        report = build_report(configured, blogs)
        self.assertTrue(report["ok"])
        self.assertTrue(report["identity_ok"])
        self.assertFalse(report["url_alignment_ok"])
        self.assertEqual(report["matched_count"], 33)
        self.assertEqual(len(report["url_mismatches"]), 1)

    def test_missing_blog_id_still_fails_oauth_identity_check(self):
        configured = [{"site_id": "site_1", "destination_id": "1", "url": "https://blog1.blogspot.com"}]
        report = build_report(configured, [])
        self.assertFalse(report["ok"])
        self.assertFalse(report["identity_ok"])
        self.assertEqual(len(report["missing"]), 1)

if __name__ == "__main__":
    unittest.main()
