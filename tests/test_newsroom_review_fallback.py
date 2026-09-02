import sys
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from three_model_consensus import three_model_consensus


def test_newsroom_can_replace_unavailable_gemini_with_blocking_cold_review(monkeypatch):
    monkeypatch.setenv("EDITORIAL_GEMINI_OUTAGE_FALLBACK", "true")
    responses = [
        '{"ok": true, "issues": []}',
        '{"ok": true, "issues": []}',
    ]
    with patch("three_model_consensus.openai_available", return_value=True), patch(
        "three_model_consensus.openai_generate_text", side_effect=responses
    ) as reviewer:
        result = three_model_consensus(
            title="Verified headline",
            content="<p>Verified facts.</p>",
            meta="Verified summary",
            keyword="verified",
            gemini_generate=lambda _: (_ for _ in ()).throw(RuntimeError("quota")),
        )
    assert result["ok"] is True
    assert result["checks"]["gemini"]["provider"] == "openai_continuity_reviewer"
    assert reviewer.call_count == 2


def test_newsroom_fallback_still_blocks_a_rejection(monkeypatch):
    monkeypatch.setenv("EDITORIAL_GEMINI_OUTAGE_FALLBACK", "true")
    responses = [
        '{"ok": false, "issues": ["unsupported fact"]}',
        '{"ok": true, "issues": []}',
    ]
    with patch("three_model_consensus.openai_available", return_value=True), patch(
        "three_model_consensus.openai_generate_text", side_effect=responses
    ):
        result = three_model_consensus(
            title="Headline",
            content="<p>Claim.</p>",
            meta="Summary",
            keyword="claim",
            gemini_generate=lambda _: (_ for _ in ()).throw(RuntimeError("quota")),
        )
    assert result["ok"] is False
