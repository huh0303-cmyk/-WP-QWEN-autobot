import unittest

from scripts.audit_adsense_sites import ADS_LINE, DOMAINS, format_checks, robots_blocks


class AdsenseAuditTests(unittest.TestCase):
    def test_exactly_26_unique_domains(self):
        self.assertEqual(26, len(DOMAINS))
        self.assertEqual(26, len(set(DOMAINS)))

    def test_exact_ads_line_and_bom_detection(self):
        good = format_checks(ADS_LINE + "\n", "text/plain")
        self.assertTrue(good["publisher_id_match"])
        self.assertFalse(good["bom"])
        bad = format_checks("\ufeff" + ADS_LINE, "text/plain")
        self.assertTrue(bad["publisher_id_match"])
        self.assertTrue(bad["bom"])

    def test_html_is_not_valid_ads_txt(self):
        self.assertTrue(format_checks("<html>oops</html>", "text/html")["looks_html"])

    def test_google_specific_and_global_robots_blocks(self):
        self.assertTrue(robots_blocks("User-agent: Google-adstxt\nDisallow: /"))
        self.assertTrue(robots_blocks("User-agent: *\nDisallow: /ads.txt"))
        self.assertFalse(robots_blocks("User-agent: *\nDisallow: /wp-admin/"))


if __name__ == "__main__":
    unittest.main()
