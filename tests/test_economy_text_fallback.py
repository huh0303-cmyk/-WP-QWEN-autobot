import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import requests
import economy_text as et


def test_chain_falls_through_three_free_models(monkeypatch):
    calls = []

    def fake(prompt, temperature, model):
        calls.append(model)
        if len(calls) < 3:
            raise requests.Timeout("timeout")
        et.last_writer_model = model
        return "ok"

    monkeypatch.setattr(et, "_try_gemini", fake)
    monkeypatch.delenv("NEWSROOM_PAID_TEXT_APPROVED", raising=False)
    monkeypatch.setenv("LONDON_WRITER_MODEL", "auto_free")
    monkeypatch.setattr(et, "RETRY_SLEEP", 0)
    et.begin_article()
    assert et.generate_text("x") == "ok"
    # 첫 모델 2회 실패 → 두 번째 모델 1회째 성공... (calls<3 실패)
    assert calls == [et.FREE_GEMINI_MODELS[0], et.FREE_GEMINI_MODELS[0], et.FREE_GEMINI_MODELS[1]]


def test_all_fail_raises(monkeypatch):
    monkeypatch.setattr(et, "_try_gemini", lambda *a: (_ for _ in ()).throw(ValueError("x")))
    monkeypatch.setenv("LONDON_WRITER_MODEL", "auto_free")
    et.begin_article()
    try:
        et.generate_text("x")
        assert False
    except RuntimeError as e:
        assert "WRITERS_EXHAUSTED" in str(e)


def test_independent_engines_after_gemini(monkeypatch):
    order = []
    monkeypatch.setattr(et, "RETRY_SLEEP", 0)
    monkeypatch.setattr(et, "_try_gemini", lambda p, t, m: (_ for _ in ()).throw(ValueError("x")))

    def compat(p, t, spec):
        order.append(spec[0])
        if spec[0] == "groq":
            raise requests.ConnectionError("down")
        return "from-" + spec[0]

    monkeypatch.setattr(et, "_try_compat", compat)
    monkeypatch.setenv("LONDON_WRITER_MODEL", "auto_free")
    monkeypatch.setenv("GROQ_API_KEY", "k"); monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    et.begin_article()
    assert et.generate_text("x") == "from-openrouter"
    assert order == ["groq", "groq", "openrouter"]   # groq 2회 실패 → openrouter
