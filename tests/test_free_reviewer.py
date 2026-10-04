"""Free-tier reviewer fallback for the editorial consensus gate (2026-10-04)."""
import sys, types
import three_model_consensus as tmc


def _fake_economy(monkeypatch, reply=None, exc=None):
    mod = types.ModuleType("economy_text")
    mod.last_writer_model = "groq:test"
    def generate_text(prompt, temperature=0.0, **kw):
        if exc:
            raise exc
        return reply
    mod.generate_text = generate_text
    monkeypatch.setitem(sys.modules, "economy_text", mod)


def test_free_reviewer_approves_when_openai_off(monkeypatch):
    monkeypatch.setattr(tmc, "openai_available", lambda: False)
    _fake_economy(monkeypatch, '{"ok": true, "issues": [], "suggestions": []}')
    r = tmc._gpt_check("first", "rule")
    assert r["ok"] is True and r["model"] == "groq:test"


def test_free_reviewer_issue_blocks(monkeypatch):
    monkeypatch.setattr(tmc, "openai_available", lambda: False)
    _fake_economy(monkeypatch, '{"ok": true, "issues": ["unsupported claim"]}')
    assert tmc._gpt_check("first", "rule")["ok"] is False


def test_free_reviewer_fail_closed_on_error_and_bad_json(monkeypatch):
    monkeypatch.setattr(tmc, "openai_available", lambda: False)
    _fake_economy(monkeypatch, exc=RuntimeError("WRITERS_EXHAUSTED"))
    assert tmc._gpt_check("first", "rule")["ok"] is False
    _fake_economy(monkeypatch, "not json")
    assert tmc._gpt_check("first", "rule")["ok"] is False


def test_kill_switch_restores_old_behavior(monkeypatch):
    monkeypatch.setattr(tmc, "openai_available", lambda: False)
    monkeypatch.setenv("FREE_REVIEWER_ENABLED", "false")
    assert tmc._gpt_check("first", "rule") == {"ok": False, "issues": ["GPT checker unavailable"]}
