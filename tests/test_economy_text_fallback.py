import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import requests
import economy_text as et


def test_chain_falls_through_three_free_models(monkeypatch):
    calls = []

    def fake(prompt, temperature, model):
        calls.append(model)
        if len(calls) < 3:
            raise requests.RequestException("timeout")
        et.last_writer_model = model
        return "ok"

    monkeypatch.setattr(et, "_try_gemini", fake)
    monkeypatch.delenv("NEWSROOM_PAID_TEXT_APPROVED", raising=False)
    monkeypatch.setenv("LONDON_WRITER_MODEL", "auto_free")
    et.begin_article()
    assert et.generate_text("x") == "ok"
    assert calls == list(et.FREE_GEMINI_MODELS[:3])


def test_all_fail_raises(monkeypatch):
    monkeypatch.setattr(et, "_try_gemini", lambda *a: (_ for _ in ()).throw(ValueError("x")))
    monkeypatch.setenv("LONDON_WRITER_MODEL", "auto_free")
    et.begin_article()
    try:
        et.generate_text("x")
        assert False
    except RuntimeError as e:
        assert "WRITERS_EXHAUSTED" in str(e)
