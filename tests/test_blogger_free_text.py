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
    assert "flash-lite" in calls[0] and "flash:generateContent" in calls[1]
    assert "gemini-2.5-flash-lite" in json.loads(writer.STATE.read_text())["model_cooldowns"]
    assert writer.free_blogger_generate_text("prompt") == "article"
    assert len(calls) == 3 and "flash:generateContent" in calls[2]


def test_both_quotas_hold_without_another_request(monkeypatch, tmp_path):
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
    assert len(calls) == 2


def test_unverified_free_tier_never_calls_provider(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path, verified="unknown")
    monkeypatch.setattr(writer.requests, "post", lambda *a, **kw: pytest.fail("provider called"))
    with pytest.raises(RuntimeError, match="free_tier_not_verified"):
        writer.free_blogger_generate_text("prompt")
