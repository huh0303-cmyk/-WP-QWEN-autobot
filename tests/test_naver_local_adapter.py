import unittest

from automation_hub.naver_local_adapter import NaverLocalPublisher, html_to_naver_text
from automation_hub.publishing import PublishJob


class _Visible:
    def __init__(self):
        self.clicked = False

    def click(self):
        self.clicked = True

    def is_visible(self, timeout=0):
        return True


class _TextLookup:
    def __init__(self, locator):
        self.first = locator


class _DraftPage:
    def __init__(self):
        self.confirmation = _Visible()
        self.waited = 0

    def wait_for_timeout(self, milliseconds):
        self.waited = milliseconds

    def get_by_text(self, _pattern):
        return _TextLookup(self.confirmation)


class NaverLocalAdapterTests(unittest.TestCase):
    def test_html_is_converted_without_images_or_scripts(self):
        value = '<h2>제목</h2><p>본문&nbsp;내용<br>둘째 줄</p><img src="paid-api"><script>bad()</script>'
        converted = html_to_naver_text(value)
        self.assertEqual("제목\n\n본문 내용\n\n둘째 줄", converted)
        self.assertNotIn("paid-api", converted)
        self.assertNotIn("bad", converted)

    def test_entities_are_decoded(self):
        self.assertEqual("A & B", html_to_naver_text("<p>A &amp; B</p>"))

    def test_draft_mode_clicks_save_and_requires_confirmation(self):
        publisher = NaverLocalPublisher("naver_n3", "https://example.test", "sky-only")
        save_button = _Visible()
        publisher._first_visible = lambda _page, _selectors: save_button
        job = PublishJob("job-1", "naver_n3", "제목", "<p>본문</p>", publish_now=False)

        result = publisher.submit(_DraftPage(), job)

        self.assertTrue(result.ok)
        self.assertEqual("draft_saved", result.status)
        self.assertTrue(save_button.clicked)

    def test_active_homefeed_policy_is_safe_and_rate_limited(self):
        import json
        from pathlib import Path

        policy = json.loads((Path(__file__).parents[1] / "config" / "naver_homefeed_automation.json").read_text(encoding="utf-8"))
        self.assertEqual("naver_n3", policy["primary_site_id"])
        self.assertEqual(["naver_n1", "naver_n2", "naver_n3"], policy["active_site_ids"])
        self.assertEqual((8, 10), tuple(policy["per_site_cadence"]["naver_n3"][key] for key in ("daily_min", "daily_max")))
        self.assertEqual((3, 4), tuple(policy["per_site_cadence"]["naver_n1"][key] for key in ("daily_min", "daily_max")))
        self.assertEqual((3, 4), tuple(policy["per_site_cadence"]["naver_n2"][key] for key in ("daily_min", "daily_max")))
        self.assertGreaterEqual(policy["per_site_cadence"]["naver_n3"]["minimum_interval_minutes"], 75)
        self.assertTrue(policy["quality_gate"]["official_source_required_for_policy_posts"])
        self.assertTrue(policy["quality_gate"]["source_attribution_required"])


if __name__ == "__main__":
    unittest.main()
