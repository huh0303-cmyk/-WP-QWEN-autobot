import unittest

from automation_hub.naver_local_adapter import html_to_naver_text


class NaverLocalAdapterTests(unittest.TestCase):
    def test_html_is_converted_without_images_or_scripts(self):
        value = '<h2>제목</h2><p>본문&nbsp;내용<br>둘째 줄</p><img src="paid-api"><script>bad()</script>'
        converted = html_to_naver_text(value)
        self.assertEqual("제목\n\n본문 내용\n\n둘째 줄", converted)
        self.assertNotIn("paid-api", converted)
        self.assertNotIn("bad", converted)

    def test_entities_are_decoded(self):
        self.assertEqual("A & B", html_to_naver_text("<p>A &amp; B</p>"))


if __name__ == "__main__":
    unittest.main()
