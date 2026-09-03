from scripts.audit_repair_all_blogger_posts import clean_english_content, complete_description, image_sources


def test_korean_summary_is_removed_without_touching_images():
    source = '<p><img src="https://img/hero.jpg" alt="hero"></p><h2>한국어 요약</h2><p>삭제할 요약입니다.</p><h2>Plan</h2><p>Keep this.</p>'
    cleaned, count = clean_english_content(source)
    assert count == 1
    assert "삭제할 요약" not in cleaned
    assert "Keep this" in cleaned
    assert image_sources(cleaned) == ["https://img/hero.jpg"]


def test_english_search_description_is_complete_and_full_length():
    description = complete_description("Affordable Busan Weekend", "<p>Short introduction.</p>")
    assert 100 <= len(description) <= 119
    assert description.endswith(".")


def test_korean_search_description_matches_korean_blog_language():
    description = complete_description("한국 생활 건강", "<p>짧은 소개입니다.</p>", "ko")
    assert 100 <= len(description) <= 119
    assert description.endswith(".")
