from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests


OPENAI_URL = "https://api.openai.com/v1/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    model: str


class ProviderUnavailable(RuntimeError):
    """A provider cannot serve this request and the orchestrator should fail over."""


class OrchestratorExhausted(RuntimeError):
    """Every configured provider failed or was unavailable."""


def _state_db_path() -> str:
    explicit = os.environ.get("ORCHESTRATOR_STATE_DB", "").strip()
    if explicit:
        return explicit
    control_db = os.environ.get("CONTROL_OPERATIONS_DB", "").strip()
    if control_db:
        return control_db
    root = Path(__file__).resolve().parents[1]
    return str(root / "data" / "control-operations.sqlite3")


def _connect() -> sqlite3.Connection:
    path = _state_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS provider_health (
            provider TEXT PRIMARY KEY,
            disabled_until REAL NOT NULL DEFAULT 0,
            failures INTEGER NOT NULL DEFAULT 0,
            last_error TEXT NOT NULL DEFAULT '',
            updated REAL NOT NULL DEFAULT 0
        )
        """
    )
    return db


def _cooldown_seconds() -> int:
    try:
        return max(30, int(os.environ.get("ORCHESTRATOR_COOLDOWN_SECONDS", "900")))
    except ValueError:
        return 900


def _provider_available(name: str) -> bool:
    with _connect() as db:
        row = db.execute("SELECT disabled_until FROM provider_health WHERE provider=?", (name,)).fetchone()
    return not row or float(row["disabled_until"] or 0) <= time.time()


def _record_success(name: str) -> None:
    now = time.time()
    with _connect() as db:
        db.execute(
            """
            INSERT INTO provider_health(provider, disabled_until, failures, last_error, updated)
            VALUES (?, 0, 0, '', ?)
            ON CONFLICT(provider) DO UPDATE SET
              disabled_until=0, failures=0, last_error='', updated=excluded.updated
            """,
            (name, now),
        )


def _record_failure(name: str, error: Exception, *, cooldown: bool) -> None:
    now = time.time()
    disabled_until = now + _cooldown_seconds() if cooldown else 0
    message = str(error)[:500]
    with _connect() as db:
        db.execute(
            """
            INSERT INTO provider_health(provider, disabled_until, failures, last_error, updated)
            VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(provider) DO UPDATE SET
              disabled_until=CASE WHEN excluded.disabled_until > provider_health.disabled_until
                                  THEN excluded.disabled_until ELSE provider_health.disabled_until END,
              failures=provider_health.failures+1,
              last_error=excluded.last_error,
              updated=excluded.updated
            """,
            (name, disabled_until, message, now),
        )


def _should_cooldown(status: int, body: str) -> bool:
    text = body.lower()
    quota_markers = (
        "quota", "rate limit", "rate_limit", "insufficient_quota", "resource_exhausted",
        "overloaded", "capacity", "too many requests",
    )
    return status in {401, 403, 408, 409, 429, 500, 502, 503, 504} or any(m in text for m in quota_markers)


def _openai(model: str, prompt: str) -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise ProviderUnavailable("OPENAI_API_KEY missing")
    response = requests.post(
        OPENAI_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        timeout=120,
    )
    if response.status_code >= 400:
        error = RuntimeError(f"OpenAI HTTP {response.status_code}: {response.text[:300]}")
        if _should_cooldown(response.status_code, response.text):
            raise ProviderUnavailable(str(error))
        raise error
    try:
        return response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ProviderUnavailable("OpenAI response shape invalid") from exc


def _anthropic(model: str, prompt: str) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise ProviderUnavailable("ANTHROPIC_API_KEY missing")
    response = requests.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={"model": model, "max_tokens": 8192, "messages": [{"role": "user", "content": prompt}]},
        timeout=120,
    )
    if response.status_code >= 400:
        error = RuntimeError(f"Anthropic HTTP {response.status_code}: {response.text[:300]}")
        if _should_cooldown(response.status_code, response.text):
            raise ProviderUnavailable(str(error))
        raise error
    try:
        blocks = response.json()["content"]
        return "".join(block.get("text", "") for block in blocks if block.get("type") == "text").strip()
    except (ValueError, KeyError, TypeError) as exc:
        raise ProviderUnavailable("Anthropic response shape invalid") from exc


def _gemini(model: str, prompt: str) -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise ProviderUnavailable("GEMINI_API_KEY missing")
    response = requests.post(
        GEMINI_URL.format(model=model),
        params={"key": key},
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        },
        timeout=120,
    )
    if response.status_code >= 400:
        error = RuntimeError(f"Gemini HTTP {response.status_code}: {response.text[:300]}")
        if _should_cooldown(response.status_code, response.text):
            raise ProviderUnavailable(str(error))
        raise error
    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ProviderUnavailable("Gemini response shape invalid") from exc


CALLERS: dict[str, Callable[[str, str], str]] = {
    "openai": _openai,
    "anthropic": _anthropic,
    "gemini": _gemini,
}


def _default_chain(task_type: str) -> list[ProviderSpec]:
    # CODEX/PM policy: OpenAI is primary for WordPress/general editorial work.
    # Claude is the first failover when OpenAI is quota/rate/availability limited.
    # Gemini is the low-cost/default primary for Blogger and third-line continuity provider.
    openai_model = os.environ.get("ORCHESTRATOR_OPENAI_MODEL", "gpt-5-mini")
    claude_model = os.environ.get("ORCHESTRATOR_CLAUDE_MODEL", "claude-sonnet-4-20250514")
    gemini_model = os.environ.get("ORCHESTRATOR_GEMINI_MODEL", "gemini-2.5-flash")
    if task_type == "blogger":
        return [
            ProviderSpec("gemini", gemini_model),
            ProviderSpec("anthropic", claude_model),
            ProviderSpec("openai", openai_model),
        ]
    return [
        ProviderSpec("openai", openai_model),
        ProviderSpec("anthropic", claude_model),
        ProviderSpec("gemini", gemini_model),
    ]


def _chain_from_env(task_type: str) -> list[ProviderSpec]:
    raw = os.environ.get(f"ORCHESTRATOR_CHAIN_{task_type.upper()}", "").strip()
    if not raw:
        return _default_chain(task_type)
    specs: list[ProviderSpec] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        provider, _, model = item.partition(":")
        provider = provider.strip().lower()
        if provider not in CALLERS:
            continue
        if not model.strip():
            defaults = {spec.name: spec.model for spec in _default_chain(task_type)}
            model = defaults.get(provider, "")
        specs.append(ProviderSpec(provider, model.strip()))
    return specs or _default_chain(task_type)


def generate_text(prompt: str, *, task_type: str = "wordpress") -> tuple[str, dict[str, object]]:
    """Generate text with durable provider failover.

    Returns (text, metadata). Providers in cooldown are skipped. Quota/rate/auth/
    availability failures put that provider into cooldown so concurrent jobs do
    not repeatedly hammer it. The next configured provider then receives the
    exact same prompt.
    """
    attempts: list[dict[str, str]] = []
    for spec in _chain_from_env(task_type):
        if not _provider_available(spec.name):
            attempts.append({"provider": spec.name, "model": spec.model, "result": "cooldown"})
            continue
        caller = CALLERS[spec.name]
        try:
            text = caller(spec.model, prompt)
            if not text.strip():
                raise ProviderUnavailable("empty response")
            _record_success(spec.name)
            return text, {
                "provider": spec.name,
                "model": spec.model,
                "attempts": attempts + [{"provider": spec.name, "model": spec.model, "result": "success"}],
            }
        except ProviderUnavailable as exc:
            _record_failure(spec.name, exc, cooldown=True)
            attempts.append({"provider": spec.name, "model": spec.model, "result": str(exc)[:180]})
            continue
        except requests.RequestException as exc:
            _record_failure(spec.name, exc, cooldown=True)
            attempts.append({"provider": spec.name, "model": spec.model, "result": str(exc)[:180]})
            continue
        except Exception as exc:
            _record_failure(spec.name, exc, cooldown=False)
            attempts.append({"provider": spec.name, "model": spec.model, "result": str(exc)[:180]})
            continue
    raise OrchestratorExhausted("All orchestrator providers failed: " + json.dumps(attempts, ensure_ascii=False))


def provider_health() -> list[dict[str, object]]:
    now = time.time()
    with _connect() as db:
        rows = db.execute(
            "SELECT provider, disabled_until, failures, last_error, updated FROM provider_health ORDER BY provider"
        ).fetchall()
    return [
        {
            "provider": row["provider"],
            "available": float(row["disabled_until"] or 0) <= now,
            "disabled_until": float(row["disabled_until"] or 0),
            "failures": int(row["failures"] or 0),
            "last_error": row["last_error"],
            "updated": float(row["updated"] or 0),
        }
        for row in rows
    ]
