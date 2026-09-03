from unittest.mock import Mock, patch

from scripts.audit_repair_all_blogger_posts import api_request, clean_english_content, complete_description, image_sources


def test_korean_summary_is_removed_without_touching_images():
    source = '<p><img src="https://img/hero.jpg" alt="hero"></p><h2>한국어 요약</h2><p>삭제할 요약입니다.</p><h2>Plan</h2><p>Keep this.</p>'
    cleaned, count = clean_english_content(source)
    assert count == 1
    assert "삭제할 요약" not in cleaned
    assert "Keep this" in cleaned
    assert image_sources(cleaned) == ["https://img/hero.jpg"]


def test_inline_korean_summary_paragraph_and_checklist_are_removed():
    source = (
        '<p>Keep the English introduction.</p>'
        '<p><strong>한국어 요약:</strong> 이 문단은 삭제합니다.</p>'
        '<h2>Next section</h2><p>Keep the next section.</p>'
        '<p>한국어 요약 체크리스트:</p><ul><li>이 목록도 삭제합니다.</li></ul>'
    )
    cleaned, count = clean_english_content(source)
    assert count == 2
    assert "이 문단은 삭제" not in cleaned
    assert "이 목록도 삭제" not in cleaned
    assert "Keep the English introduction" in cleaned
    assert "Keep the next section" in cleaned


def test_english_search_description_is_complete_and_full_length():
    description = complete_description("Affordable Busan Weekend", "<p>Short introduction.</p>")
    assert 100 <= len(description) <= 119
    assert description.endswith(".")


def test_korean_search_description_matches_korean_blog_language():
    description = complete_description("한국 생활 건강", "<p>짧은 소개입니다.</p>", "ko")
    assert 100 <= len(description) <= 119
    assert description.endswith(".")


@patch("scripts.audit_repair_all_blogger_posts.time.sleep")
@patch("scripts.audit_repair_all_blogger_posts.requests.request")
def test_blogger_api_transient_failure_is_retried(request, sleep):
    request.side_effect = [Mock(status_code=503), Mock(status_code=200)]
    result = api_request("GET", "https://example.test", timeout=1)
    assert result.status_code == 200
    assert request.call_count == 2
    sleep.assert_called_once()
