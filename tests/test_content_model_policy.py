from automation_hub.content_model_policy import choose_writer, claude_role


def test_default_writer_is_gemini():
    decision = choose_writer()
    assert decision.provider == "gemini"
    assert decision.status == "OK"


def test_gpt_only_for_explicit_fallback_signal():
    assert choose_writer(quality_fail=True).provider == "openai"
    assert choose_writer(important_content=True).provider == "openai"
    assert choose_writer(high_value_content=True).provider == "openai"
    assert choose_writer(manual_override=True).provider == "openai"


def test_no_silent_paid_fallback_when_free_primary_unavailable():
    decision = choose_writer(primary_available=False)
    assert decision.provider == "none"
    assert decision.status == "AWAITING_APPROVAL"


def test_freshness_sensitive_requires_official_verification():
    decision = choose_writer(freshness_sensitive=True, official_source_verified=False)
    assert decision.provider == "none"
    assert decision.status == "QUALITY_FAIL"


def test_claude_is_audit_role_not_default_writer():
    assert claude_role() == "development_code_system_audit"
