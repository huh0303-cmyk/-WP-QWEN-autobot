import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from automation_hub.repetition_guard import title_self_issues, repetition_issues
from automation_hub.editorial_language_policy import title_cliches
import retitle_repeated as R


class TitleRepeatGuard(unittest.TestCase):
    def test_keyword_parenthetical_blocked(self):
        self.assertTrue(title_self_issues("Is a Temple Stay Experience in Korea Truly a Transformative Journey? (temple stay experience Korea)"))

    def test_repeated_word_blocked(self):
        self.assertTrue(title_self_issues("The Soulful Slurp: Korean Ramen vs Japanese Ramen"))
        self.assertTrue(title_self_issues("현대인 심장 두근거림 원인과 대처법: 부정맥 증상, 심장 건강 관리"))

    def test_stock_tail_blocked(self):
        self.assertTrue(title_self_issues("Korea ATM Fees: A Closer Look at What Really Matters"))

    def test_clean_titles_pass(self):
        for t in ("Seoul Transportation Card Guide", "Tax Breaks for Foreign Direct Investment", "무릎 연골 관리가 필요한 이유"):
            self.assertEqual(title_self_issues(t), [], t)

    def test_wired_into_title_cliches_and_repetition_issues(self):
        bad = "Temple Stay Experience Tips (temple stay experience Korea)"
        self.assertTrue(title_cliches(bad))
        self.assertTrue(any(i.startswith("TITLE_REPEAT") for i in repetition_issues(bad, "<p>x</p>", [])))

    def test_det_fix_and_flag(self):
        self.assertEqual(R.det_fix("Korea ATM Withdrawal Fee (Korea ATM withdrawal fee foreigner)"), "Korea ATM Withdrawal Fee")
        d = {"s": [{"id": 1, "title": "Living in Seoul: Cost of Living Shifts", "date": "1"},
                   {"id": 2, "title": "Seoul Subway Guide", "date": "2"}]}
        self.assertEqual(list(R.flag(d)), [("s", "1")])


if __name__ == "__main__":
    unittest.main()
