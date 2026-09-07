import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import tistory_approval_tokens as tokens  # noqa: E402


@pytest.fixture(autouse=True)
def signing_secret(monkeypatch):
    monkeypatch.setenv("TISTORY_APPROVAL_SIGNING_SECRET", "test-secret-do-not-use-in-prod")


def test_issued_token_verifies_for_its_own_job_id():
    token = tokens.issue_token("tistory_life365:2026-08-30")
    ok, payload, reason = tokens.verify_token(token, expected_job_id="tistory_life365:2026-08-30")
    assert ok is True
    assert reason == ""
    assert payload["job_id"] == "tistory_life365:2026-08-30"


def test_token_rejected_for_a_different_job_id():
    token = tokens.issue_token("tistory_life365:2026-08-30")
    ok, _payload, reason = tokens.verify_token(token, expected_job_id="tistory_ktrip365:2026-08-30")
    assert ok is False
    assert reason == "job_id_mismatch"


def test_expired_token_rejected():
    token = tokens.issue_token("tistory_life365:2026-08-30", ttl_seconds=-1)
    ok, _payload, reason = tokens.verify_token(token, expected_job_id="tistory_life365:2026-08-30")
    assert ok is False
    assert reason == "expired"


def test_tampered_token_rejected():
    token = tokens.issue_token("tistory_life365:2026-08-30")
    payload_b64, sig_b64 = token.split(".", 1)
    tampered = payload_b64 + "x." + sig_b64
    ok, _payload, reason = tokens.verify_token(tampered, expected_job_id="tistory_life365:2026-08-30")
    assert ok is False
    assert reason == "bad_signature"


def test_token_signed_with_a_different_secret_is_rejected(monkeypatch):
    token = tokens.issue_token("tistory_life365:2026-08-30")
    monkeypatch.setenv("TISTORY_APPROVAL_SIGNING_SECRET", "a-different-secret")
    ok, _payload, reason = tokens.verify_token(token, expected_job_id="tistory_life365:2026-08-30")
    assert ok is False
    assert reason == "bad_signature"


def test_state_round_trip(tmp_path):
    state = tokens.load_state(tmp_path, "2026-08-30")
    assert state == {"date": "2026-08-30", "jobs": {}}
    state["jobs"]["tistory_life365:2026-08-30"] = {"status": "PENDING"}
    tokens.save_state(tmp_path, "2026-08-30", state)
    reloaded = tokens.load_state(tmp_path, "2026-08-30")
    assert reloaded["jobs"]["tistory_life365:2026-08-30"]["status"] == "PENDING"


def test_missing_secret_raises(monkeypatch):
    monkeypatch.delenv("TISTORY_APPROVAL_SIGNING_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        tokens.issue_token("tistory_life365:2026-08-30")
