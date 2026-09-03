#!/usr/bin/env python3
"""Sign, verify, and track single-use Tistory approval tokens.

A token authorizes publishing exactly one job_id, once, before a fixed
expiry. The signing secret (TISTORY_APPROVAL_SIGNING_SECRET) lives only in
GitHub Actions secrets; the token embedded in a public review page is inert
without it — knowing the token alone cannot forge or extend another one.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path

DEFAULT_TTL_SECONDS = 14 * 24 * 3600  # 14 days


def _secret() -> bytes:
    secret = os.environ.get("TISTORY_APPROVAL_SIGNING_SECRET", "").strip()
    if not secret:
        raise RuntimeError("TISTORY_APPROVAL_SIGNING_SECRET is not configured")
    return secret.encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def issue_token(job_id: str, *, ttl_seconds: int = DEFAULT_TTL_SECONDS, nonce: str | None = None) -> str:
    nonce = nonce or _b64(os.urandom(9))
    now = int(time.time())
    payload = {"job_id": job_id, "iat": now, "exp": now + int(ttl_seconds), "nonce": nonce}
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = _b64(payload_json)
    sig = hmac.new(_secret(), payload_b64.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_b64}.{_b64(sig)}"


def verify_token(token: str, *, expected_job_id: str | None = None) -> tuple[bool, dict, str]:
    """Returns (ok, payload, reason). reason is "" when ok is True."""
    try:
        payload_b64, sig_b64 = token.strip().split(".", 1)
        expected_sig = hmac.new(_secret(), payload_b64.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(expected_sig, _unb64(sig_b64)):
            return False, {}, "bad_signature"
        payload = json.loads(_unb64(payload_b64))
    except Exception as exc:
        return False, {}, f"malformed_token: {exc}"

    if int(time.time()) > int(payload.get("exp", 0)):
        return False, payload, "expired"
    if expected_job_id and payload.get("job_id") != expected_job_id:
        return False, payload, "job_id_mismatch"
    return True, payload, ""


def token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:24]


def _state_path(state_dir: str | Path, date: str) -> Path:
    return Path(state_dir) / f"{date}.json"


def load_state(state_dir: str | Path, date: str) -> dict:
    path = _state_path(state_dir, date)
    if not path.exists():
        return {"date": date, "jobs": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(state_dir: str | Path, date: str, state: dict) -> None:
    path = _state_path(state_dir, date)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
