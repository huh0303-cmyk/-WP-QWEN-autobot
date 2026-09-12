from automation_hub.content_model_policy import choose_writer, review_role


def test_default_writer_is_randomly_gpt_or_gemini():
    """2026-09-12 (user directive): the routine writer is randomly gpt-5
    mini or Gemini 2.5 Flash per article, not gpt-5-mini exclusively."""
    seen = {choose_writer().provider for _ in range(60)}
    assert seen == {"openai", "gemini"}
    decision = choose_writer()
    assert decision.provider in {"openai", "gemini"}
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
