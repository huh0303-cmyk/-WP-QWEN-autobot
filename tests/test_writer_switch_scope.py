import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import economy_text as engine
from editorial_topic_scope import topic_fits, choose_scoped_keyword


def test_quality_retry_uses_next_untried_free_model(monkeypatch):
    engine.begin_article()
    calls = []

    def write(_prompt, _temperature, model):
        calls.append(model)
        return "article"

    monkeypatch.setattr(engine, "_try_gemini", write)
    assert engine.generate_text("first") == "article"
    assert engine.generate_text("quality retry", repair=True) == "article"
    assert calls == list(engine.FREE_GEMINI_MODELS[:2])
    engine._article_attempts = None


def test_geography_alone_does_not_qualify_keyword():
    assert not topic_fits("https://jobinkorea365.com", "Korea election results")
    assert not topic_fits("https://k-trip365.com", "Korea salary negotiation")
    assert topic_fits("https://jobinkorea365.com", "Korea job interview preparation")
    assert topic_fits("https://k-trip365.com", "Seoul autumn walking routes")
    assert choose_scoped_keyword("https://jobinkorea365.com", "Korea election results",
                                 ["Korea bitcoin", "Korea job interview preparation"]) == "Korea job interview preparation"


def test_all_free_models_exhausted_stops_without_paid_gpt(monkeypatch):
    engine.begin_article()
    monkeypatch.setattr(engine, "_try_gemini", lambda *args: (_ for _ in ()).throw(RuntimeError("quota")))
    monkeypatch.setenv("LOCAL_TEXT_FALLBACK_ENABLED", "false")
    with pytest.raises(RuntimeError, match="WRITERS_EXHAUSTED"):
        engine.generate_text("prompt")
    assert engine._article_attempts == set(engine.FREE_GEMINI_MODELS)
    engine._article_attempts = None
