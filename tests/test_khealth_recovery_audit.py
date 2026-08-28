import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import khealth_recovery_audit as audit


def test_broken_title_code_fence_is_detected():
    assert audit.find_broken_titles("```html 임플란트 비용 총정리") == ["```html"]
    assert audit.find_broken_titles("일반 제목입니다") == []


def test_future_year_beyond_current_year_is_flagged():
    text = f"{audit.CURRENT_YEAR + 1}년 최신 정보"
    assert str(audit.CURRENT_YEAR + 1) in audit.find_future_years(text)
    assert audit.find_future_years(f"{audit.CURRENT_YEAR}년 기준 정보") == []


def test_lorem_ipsum_and_boilerplate_markers_detected_case_insensitively():
    assert "Marketer" in audit.find_boilerplate("footer credit: Marketer theme")
    assert "Lorem ipsum" in audit.find_boilerplate("lorem ipsum dolor sit amet")
    assert audit.find_boilerplate("정상적인 건강 정보 본문입니다") == []


def test_near_duplicate_titles_are_paired_once():
    posts = [
        {"id": 1, "title": {"rendered": "임플란트 비용 총정리 가이드"}},
        {"id": 2, "title": {"rendered": "임플란트 비용 총정리가이드"}},  # near-identical after normalization
        {"id": 3, "title": {"rendered": "완전히 다른 주제의 글"}},
    ]
    dupes = audit.find_near_duplicate_titles(posts)
    assert len(dupes) == 1
    assert {dupes[0]["post_id_a"], dupes[0]["post_id_b"]} == {1, 2}


def test_audit_post_returns_none_when_nothing_wrong():
    post = {
        "id": 10, "status": "publish", "date": "2026-08-01", "link": "https://k-health365.com/x/",
        "title": {"rendered": "정상 제목"},
        "content": {"rendered": "<p>정상적인 본문입니다.</p>"},
        "excerpt": {"rendered": "<p>요약</p>"},
    }
    assert audit.audit_post(post) is None


def test_audit_post_flags_every_issue_type_together():
    post = {
        "id": 11, "status": "draft", "date": "2026-08-01", "link": "https://k-health365.com/y/",
        "title": {"rendered": "```html 2099년 눈가주름 Product Highlight"},
        "content": {"rendered": "<p>lorem ipsum dolor sit amet</p>"},
        "excerpt": {"rendered": ""},
    }
    row = audit.audit_post(post)
    assert row is not None
    assert row["issues"]["broken_title"]
    assert "2099" in row["issues"]["future_year"]
    assert row["issues"]["lorem_ipsum"] is True
    assert "Product Highlight" in row["issues"]["boilerplate"]


def test_build_audit_never_writes_or_deletes_anything_it_only_reports():
    fake_posts = [
        {"id": 1, "status": "draft", "date": "2026-08-01", "link": "https://k-health365.com/a/",
         "title": {"rendered": "```html broken"}, "content": {"rendered": "<p>lorem ipsum</p>"},
         "excerpt": {"rendered": ""}},
        {"id": 2, "status": "publish", "date": "2026-08-02", "link": "https://k-health365.com/b/",
         "title": {"rendered": "정상 제목"}, "content": {"rendered": "<p>정상 본문</p>"},
         "excerpt": {"rendered": ""}},
    ]
    with patch.object(audit, "fetch_all_posts", return_value=fake_posts):
        result = audit.build_audit()
    assert result["mode"] == "AUDIT_ONLY_NO_CHANGES"
    assert result["total_posts_scanned"] == 2
    assert result["flagged_count"] == 1
    assert result["status_counts"] == {"draft": 1, "publish": 1}
