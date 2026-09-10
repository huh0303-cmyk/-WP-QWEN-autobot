from unittest.mock import patch

from scripts.auto_write_and_draft import _finish_meta_description, _write_article


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


def test_editorial_rules_reach_the_writer_prompt_when_provided():
    """A specialist channel's mandatory topic-scope rules (e.g. the medical
    qualification editorial policy's "no general symptom/treatment content")
    must actually reach the GPT prompt, not just exist as an unused string."""
    captured_prompts = []

    def fake_generate(prompt, **kwargs):
        captured_prompts.append(prompt)
        raise RuntimeError("stop after capturing prompt; content is not needed for this test")

    with patch("scripts.auto_write_and_draft.openai_available", return_value=True), \
         patch("scripts.auto_write_and_draft.openai_generate_text", side_effect=fake_generate):
        _write_article(
            keyword="요양보호사 응시자격과 교육과정 확인 방법",
            site_theme="한국 의료·보건·돌봄·복지 분야 자격 취득과 취업 준비",
            language="ko", persona="자격정보 편집자", tone="설명체",
            min_chars=1260, target_chars=1680, max_chars=2304,
            editorial_rules="\n의료·보건 자격 전문 편집 지침(필수):\n일반 건강상식·질병치료·영양제·뷰티·연예·투자 뉴스는 제외한다.",
        )
    assert captured_prompts, "the writer must call the GPT text generator"
    assert all("일반 건강상식" in prompt for prompt in captured_prompts)


def test_no_editorial_rules_does_not_change_prompt_when_absent():
    """Sites without a medical_editorial policy must not regress: an empty
    editorial_rules stays a no-op on the prompt."""
    captured_prompts = []

    def fake_generate(prompt, **kwargs):
        captured_prompts.append(prompt)
        raise RuntimeError("stop after capturing prompt; content is not needed for this test")

    with patch("scripts.auto_write_and_draft.openai_available", return_value=True), \
         patch("scripts.auto_write_and_draft.openai_generate_text", side_effect=fake_generate):
        _write_article(
            keyword="k-pop comeback album",
            site_theme="Korean pop culture",
            language="en", persona="pop culture editor", tone="upbeat",
            min_chars=1200, target_chars=1600, max_chars=2200,
        )
    assert captured_prompts
    assert "의료·보건 자격 전문 편집 지침" not in captured_prompts[0]

