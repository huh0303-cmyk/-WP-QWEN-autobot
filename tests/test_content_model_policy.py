from automation_hub.content_model_policy import choose_writer, review_role


def test_default_writer_is_gpt_5_mini():
    decision = choose_writer()
    assert decision.provider == "openai"
    assert decision.status == "OK"


def test_rewrite_signals_keep_gpt_writer():
    assert choose_writer(quality_fail=True).provider == "openai"
    assert choose_writer(important_content=True).provider == "openai"
    assert choose_writer(high_value_content=True).provider == "openai"
    assert choose_writer(manual_override=True).provider == "openai"


def test_no_silent_model_fallback_when_primary_unavailable():
    decision = choose_writer(primary_available=False)
    assert decision.provider == "none"
    assert decision.status == "AWAITING_APPROVAL"


def test_freshness_sensitive_requires_official_verification():
    decision = choose_writer(freshness_sensitive=True, official_source_verified=False)
    assert decision.provider == "none"
    assert decision.status == "QUALITY_FAIL"


def test_gemini_is_independent_review_role_after_gpt():
    assert review_role() == "independent_final_editorial_fact_and_quality_reviewer"
