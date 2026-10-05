import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import economy_text as writer


def test_free_chain_uses_next_model_after_quota_without_paid_call():
    writer.begin_article()
    calls = []

    def gemini(_prompt, _temperature, model, key=None):
        calls.append(model)
        if len(calls) == 1:
            raise writer.requests.HTTPError("quota")
        return "usable article"

    with patch.object(writer, "_try_gemini", side_effect=gemini), patch.dict(os.environ, {"LOCAL_TEXT_FALLBACK_ENABLED": "false", "GEMINI_API_KEY": "k" * 30}):
        writer._DEAD.clear(); writer._COOLDOWN.clear()
        assert writer.generate_text("prompt") == "usable article"
    assert calls == list(writer.FREE_GEMINI_MODELS[:2])


def test_explicit_model_runs_first_then_other_free_models():
    selected = "gemini-2.5-flash-lite"
    assert writer._model_chain(selected)[0] == selected
    assert set(writer._model_chain(selected)) == set(writer.FREE_GEMINI_MODELS)


def test_invalid_model_is_rejected():
    try:
        writer._model_chain("gemini-paid-or-unknown")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown model accepted")


def test_incomplete_gemini_response_does_not_count_as_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    response = Mock()
    response.json.return_value = {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": "partial"}]}}]}
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}), patch.object(writer.requests, "post", return_value=response):
        try:
            writer._try_gemini("prompt", 0.7, writer.FREE_GEMINI_MODELS[0])
        except ValueError:
            pass
        else:
            raise AssertionError("truncated draft accepted")


def test_paid_gpt_balance_error_falls_back_to_free_gemini():
    writer.begin_article()
    with patch.dict(os.environ, {"OPENAI_ENABLED": "true"}), \
         patch("openai_text.openai_available", return_value=True), \
         patch("openai_text.openai_generate_text", side_effect=RuntimeError("insufficient_quota")), \
         patch.object(writer, "_try_gemini", return_value="free result") as gemini:
        assert writer.generate_text("prompt", force_gpt=True) == "free result"
    assert gemini.call_args.args[2] == writer.FREE_GEMINI_MODELS[0]
