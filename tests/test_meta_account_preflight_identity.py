import io
import json
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from scripts import meta_account_preflight as preflight


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_instagram_login_identity_endpoint_and_fields(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        return FakeResponse({"user_id": "111222333", "username": "english_pick1"})

    monkeypatch.setattr(preflight, "urlopen", fake_urlopen)
    result = preflight.verify_identity("instagram", "FAKE_INSTAGRAM_TOKEN")

    parsed = urlparse(seen["url"])
    assert parsed.netloc == "graph.instagram.com"
    assert parsed.path.endswith("/me")
    assert parse_qs(parsed.query)["fields"] == ["user_id,username"]
    assert result["status"] == "IDENTITY_RESPONSE_OK"
    assert result["resolved_user_id"] == "111222333"
    assert result["resolved_username"] == "english_pick1"


def test_threads_identity_endpoint_and_fields(monkeypatch):
    seen = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        return FakeResponse({"id": "444555666", "username": "japanese_pick"})

    monkeypatch.setattr(preflight, "urlopen", fake_urlopen)
    result = preflight.verify_identity("threads", "FAKE_THREADS_TOKEN")

    parsed = urlparse(seen["url"])
    assert parsed.netloc == "graph.threads.net"
    assert parsed.path.endswith("/me")
    assert parse_qs(parsed.query)["fields"] == ["id,username"]
    assert result["status"] == "IDENTITY_RESPONSE_OK"
    assert result["resolved_user_id"] == "444555666"
    assert result["resolved_username"] == "japanese_pick"


def test_readiness_derives_user_id_and_checks_exact_handle(monkeypatch):
    monkeypatch.setattr(
        preflight,
        "urlopen",
        lambda request, timeout: FakeResponse(
            {"user_id": "111222333", "username": "english_pick1"}
        ),
    )
    import os
    from unittest.mock import patch

    with patch.dict(
        os.environ,
        {"META_INSTAGRAM_ENGLISH_PICK1_ACCESS_TOKEN": "FAKE_TOKEN"},
        clear=True,
    ):
        result = preflight.readiness(preflight.load_policy())

    assert result["ready_connections"] == 1
    row = next(
        x for x in result["connections"]
        if x["platform"] == "instagram" and x["handle"] == "english_pick1"
    )
    assert row["status"] == "IDENTITY_VERIFIED_WRITE_SCOPE_UNCONFIRMED"
    assert row["resolved_user_id"] == "111222333"
    assert row["resolved_username"] == "english_pick1"
    assert result["publish_enabled"] is False
    assert result["publication_performed"] is False
    assert result["write_scope_verified"] is False


def test_wrong_handle_is_blocked(monkeypatch):
    monkeypatch.setattr(
        preflight,
        "urlopen",
        lambda request, timeout: FakeResponse(
            {"user_id": "111222333", "username": "not_english_pick1"}
        ),
    )
    import os
    from unittest.mock import patch

    with patch.dict(
        os.environ,
        {"META_INSTAGRAM_ENGLISH_PICK1_ACCESS_TOKEN": "FAKE_TOKEN"},
        clear=True,
    ):
        result = preflight.readiness(preflight.load_policy())

    row = next(
        x for x in result["connections"]
        if x["platform"] == "instagram" and x["handle"] == "english_pick1"
    )
    assert row["status"] == "HANDLE_MISMATCH"
    assert result["ready_connections"] == 0


def test_expired_token_is_reported_without_logging_token(monkeypatch):
    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, 401, "Unauthorized", {}, io.BytesIO(b""))

    monkeypatch.setattr(preflight, "urlopen", fake_urlopen)
    result = preflight.verify_identity("instagram", "NEVER_LOG_THIS_TOKEN")

    assert result["status"] == "INVALID_OR_EXPIRED_TOKEN"
    assert result["http_status"] == 401
    assert "NEVER_LOG_THIS_TOKEN" not in json.dumps(result)
