import unittest

from automation_hub.kinvest_title_guard import kinvest_title_issues


class KInvestTitleGuardTests(unittest.TestCase):
    def test_rejects_south_korean_prefix(self):
        self.assertTrue(kinvest_title_issues("South Korean Equity Market Dividend Rules"))

    def test_rejects_korean_prefix(self):
        self.assertTrue(kinvest_title_issues("Korean ETF Selection for New Investors"))

    def test_allows_subject_first_title(self):
        self.assertEqual([], kinvest_title_issues("Dividend Tax: What Overseas Investors Must File"))

    def test_case_and_whitespace_insensitive(self):
        self.assertTrue(kinvest_title_issues("  SOUTH   KOREAN Bond Market Outlook"))


if __name__ == "__main__":
    unittest.main()
