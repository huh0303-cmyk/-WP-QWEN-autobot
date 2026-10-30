"""Regression tests for per-article WordPress tag filtering; run by isolated CI."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

from automation_hub.article_metadata_guard import sanitize_article_labels


class ArticleMetadataGuardTests(unittest.TestCase):
    def test_removes_cross_topic_tags(self):
        title = "통합의학박람회에서 보완요법의 근거와 안전성을 확인하는 법"
        keyword = "통합의학박람회 보완요법 근거"
        labels = [
            "통합의학박람회", "보완요법", "근거중심의학", "류마티스관절염",
            "생물학적제제", "오메가3고르는법", "치매 선별검사",
            "건강관리", "면역력관리", "대사증후군",
        ]
        clean = sanitize_article_labels(labels, title=title, keyword=keyword)
        self.assertLessEqual(len(clean), 5)
        self.assertTrue(clean)
        for unrelated in ("류마티스관절염", "생물학적제제", "오메가3고르는법", "치매 선별검사"):
            self.assertNotIn(unrelated, clean)

    def test_deduplicates_labels_and_caps_length(self):
        clean = sanitize_article_labels(
            ["오메가3", "오메가3", "EPA DHA 함량", "치매", "오메가3고르는법", "오메가3 제품 비교"],
            title="오메가3 EPA·DHA 함량표 읽는 법과 제품 비교 기준",
            keyword="오메가3 EPA DHA 함량표",
        )
        self.assertLessEqual(len(clean), 5)
        self.assertEqual(len({x.casefold() for x in clean}), len(clean))
        self.assertNotIn("치매", clean)

    def test_does_not_fill_with_unrelated_sitewide_tags(self):
        clean = sanitize_article_labels(
            ["류마티스관절염", "오메가3", "치매", "제주 의료관광"],
            title="건강검진 결과를 생활 습관 계획으로 바꾸는 실천 방법",
            keyword="건강검진 결과 생활습관 관리",
        )
        self.assertNotIn("류마티스관절염", clean)
        self.assertNotIn("오메가3", clean)
        self.assertNotIn("치매", clean)
        self.assertNotIn("제주 의료관광", clean)


if __name__ == "__main__":
    unittest.main()
