import sys
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from three_model_consensus import three_model_consensus


def test_two_independent_gpt_passes_both_approve():
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
        )
    assert result["ok"] is True
    assert set(result["checks"]) == {"gpt_1", "gpt_2"}
    assert reviewer.call_count == 2


def test_either_gpt_pass_rejecting_blocks():
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
        )
    assert result["ok"] is False


def test_gemini_generate_argument_is_never_invoked():
    """Backward-compat argument only; Gemini is never called network-wide."""
    responses = ['{"ok": true, "issues": []}', '{"ok": true, "issues": []}']
    with patch("three_model_consensus.openai_available", return_value=True), patch(
        "three_model_consensus.openai_generate_text", side_effect=responses
    ):
        result = three_model_consensus(
            title="Headline",
            content="<p>Claim.</p>",
            meta="Summary",
            keyword="claim",
            gemini_generate=lambda _: (_ for _ in ()).throw(AssertionError("gemini_generate must not be called")),
        )
    assert result["ok"] is True
