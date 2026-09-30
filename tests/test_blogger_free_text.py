import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from scripts import blogger_free_text as writer


class Response:
    def __init__(self, status, body=None):
        self.status_code = status
        self.ok = status == 200
        self.body = body or {}

    def json(self):
        return self.body


def configure(monkeypatch, tmp_path, verified="free_tier"):
    config = tmp_path / "free-writer.json"
    config.write_text(json.dumps({
        "billing_verified": verified,
        "verified_at": datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat(),
        "api_key": "test-key",
    }), encoding="utf-8")
    monkeypatch.setattr(writer, "CONFIG", config)
    monkeypatch.setattr(writer, "STATE", tmp_path / "state.json")


def test_429_switches_models_and_cools_first_model(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    calls = []

    def post(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            return Response(429)
        return Response(200, {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "article"}]}}]})

    monkeypatch.setattr(writer.requests, "post", post)
    assert writer.free_blogger_generate_text("prompt") == "article"
    assert "gemini-3.5-flash-lite" in calls[0] and "gemini-3.1-flash-lite" in calls[1]
    assert "gemini-3.5-flash-lite" in json.loads(writer.STATE.read_text())["model_cooldowns"]
    assert writer.free_blogger_generate_text("prompt") == "article"
    assert len(calls) == 3 and "gemini-3.1-flash-lite" in calls[2]


def test_three_quotas_hold_without_another_request(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path)
    calls = []

    def post(url, **kwargs):
        calls.append(url)
        return Response(429)

    monkeypatch.setattr(writer.requests, "post", post)
    with pytest.raises(RuntimeError, match="free_quota_wait_no_paid_fallback"):
        writer.free_blogger_generate_text("prompt")
    with pytest.raises(RuntimeError, match="free_quota_wait_no_paid_fallback"):
        writer.free_blogger_generate_text("prompt")
    assert len(calls) == 3


def test_unverified_free_tier_never_calls_provider(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path, verified="unknown")
    monkeypatch.setattr(writer.requests, "post", lambda *a, **kw: pytest.fail("provider called"))
    with pytest.raises(RuntimeError, match="free_tier_not_verified"):
        writer.free_blogger_generate_text("prompt")


def test_publisher_uses_three_approved_free_models():
    assert writer.MODELS == (
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash-lite",
    )


def test_schedule_uses_nearly_full_korea_day():
    from scripts.schedule_blogger33_daily_vps import build_slots, KST

    now = datetime(2026, 10, 2, 0, 5, tzinfo=KST)
    slots = build_slots(now, 33)
    assert len(slots) == 33
    assert slots[0].hour == 0
    assert slots[-1].hour == 23
    assert all(a < b for a, b in zip(slots, slots[1:]))


def test_fallback_goes_to_shared_chain_when_server_path_fails(monkeypatch):
    import sys, types
    monkeypatch.setattr(writer, "free_blogger_generate_text",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("free_quota_wait_no_paid_fallback")))
    calls = []
    fake = types.SimpleNamespace(begin_article=lambda: None,
                                 generate_text=lambda p, temperature=0.5: calls.append(p) or "from-shared-chain")
    monkeypatch.setitem(sys.modules, "economy_text", fake)
    assert writer.blogger_generate_with_fallback("prompt") == "from-shared-chain"
    assert calls == ["prompt"]


def test_transient_server_error_retried_twice_before_fallback(monkeypatch):
    import sys, types
    n = {"c": 0}

    def flaky(*a, **k):
        n["c"] += 1
        raise RuntimeError("free_provider_temporarily_unavailable")

    monkeypatch.setattr(writer, "free_blogger_generate_text", flaky)
    monkeypatch.setenv("WRITER_RETRY_SLEEP", "0")
    fake = types.SimpleNamespace(begin_article=lambda: None, generate_text=lambda p, temperature=0.5: "ok")
    monkeypatch.setitem(sys.modules, "economy_text", fake)
    assert writer.blogger_generate_with_fallback("prompt") == "ok"
    assert n["c"] == 2
