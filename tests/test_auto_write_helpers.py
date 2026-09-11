from scripts.auto_write_and_draft import _finish_meta_description


def test_meta_description_never_ends_with_chopped_korean_word():
    article = {
        "title": "국제교육문화 교류 준비 체크리스트",
        "meta_description": "국제교육문화 프로그램을 처음 준비하는 독자를 위해 국가와 기관 선택, 예산, 비자, 보험, 서류, 일정, 안전 확인 절차와 실제 계획 전 확인할 내용을 차근차근 살펴보세요",
    }
    meta = _finish_meta_description(article)["meta_description"]
    assert 100 <= len(meta) <= 120
    assert not meta.endswith("차.")
    assert meta.endswith(".")


def test_short_english_meta_gets_complete_search_snippet():
    article = {
        "title": "Questions to Ask Before a Korea Hospital Consultation",
        "meta_description": "Prepare for a safer hospital consultation in Korea",
    }
    meta = _finish_meta_description(article)["meta_description"]
    assert 100 <= len(meta) <= 120
    assert meta.endswith(".")
    assert not meta.endswith((" to.", " for.", " and.", " with."))


def test_bus_an_meta_does_not_end_with_chopped_phrase():
    article = {
        "title": "Busan Weekend: Smart Savings, Big Memories",
        "meta_description": "Plan your affordable Busan weekend trip with this budget guide",
    }
    meta = _finish_meta_description(article)["meta_description"]
    assert 100 <= len(meta) <= 119
    assert "what to." not in meta.lower()
    assert meta.endswith(".")

