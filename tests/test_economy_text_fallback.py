import os, sys, types
sys.path.insert(0, "scripts")
import requests
import economy_text as e


def _http(status):
    r = requests.Response(); r.status_code = status
    return requests.HTTPError(response=r)


def setup_function(_):
    e._DEAD.clear(); e._COOLDOWN.clear()
    for n in ("GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3", "GROQ_API_KEY", "OPENROUTER_API_KEY", "CEREBRAS_API_KEY"):
        os.environ.pop(n, None)
    os.environ["WRITER_RETRY_SLEEP"] = "0"


def test_placeholder_gemini_key_ignored():
    os.environ["GEMINI_API_KEY"] = "x"
    os.environ["GEMINI_API_KEY_2"] = "k" * 30
    assert [n for n, _ in e._gemini_keys()] == ["GEMINI_API_KEY_2"]


def test_second_key_used_when_first_rejected(monkeypatch):
    os.environ["GEMINI_API_KEY"] = "a" * 30
    os.environ["GEMINI_API_KEY_2"] = "b" * 30
    calls = []
    def fake(prompt, temp, model, key=None):
        calls.append(key[0])
        if key[0] == "a":
            raise _http(403)
        return "ok-from-b"
    monkeypatch.setattr(e, "_try_gemini", fake)
    e.begin_article()
    assert e.generate_text("p") == "ok-from-b"
    assert calls[0] == "a" and "b" in calls
    assert ("gemini", "GEMINI_API_KEY", "*") in e._DEAD       # bad key parked for the rest of the run
    calls.clear(); e.begin_article()
    assert e.generate_text("p") == "ok-from-b" and calls == ["b"]  # never retried the dead key


def test_groq_model_rotation_on_404_and_429(monkeypatch):
    os.environ["GROQ_API_KEY"] = "g" * 30
    seen = []
    def fake(prompt, temp, spec, model=None):
        seen.append(model)
        if model == "openai/gpt-oss-120b":
            raise _http(429)
        if model == "openai/gpt-oss-20b":
            raise _http(404)
        return "ok-" + model
    monkeypatch.setattr(e, "_try_compat", fake)
    e.begin_article()
    assert e.generate_text("p") == "ok-llama-3.3-70b-versatile"
    assert seen[:3] == ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"]
    seen.clear(); e.begin_article()
    assert e.generate_text("p") == "ok-llama-3.3-70b-versatile" and seen == ["llama-3.3-70b-versatile"]
