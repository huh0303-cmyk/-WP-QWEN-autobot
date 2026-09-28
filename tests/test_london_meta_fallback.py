from scripts.auto_write_and_draft import _finish_meta_description


def test_korean_short_model_meta_is_completed_without_unverified_cost_claim():
    article = {"title": "코로나 백신 접종 현황과 확인할 사항", "meta_description": "코로나 백신 정보"}
    meta = _finish_meta_description(article, keyword="코로나 백신 접종 현황")["meta_description"]
    assert 100 <= len(meta) <= 119 and meta.endswith(".")
    assert "비용" not in meta and "코로나 백신 접종 현황" in meta


def test_english_short_model_meta_is_completed():
    article = {"title": "Korea job interview preparation and next steps", "meta_description": "Prepare for an interview"}
    meta = _finish_meta_description(article, keyword="Korea job interview")["meta_description"]
    assert 100 <= len(meta) <= 119 and meta.endswith(".")
    assert "Korea job interview" in meta
