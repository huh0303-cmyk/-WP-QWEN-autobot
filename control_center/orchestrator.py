from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests

from . import london_activity

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    model: str


class ProviderUnavailable(RuntimeError):
    pass


class OrchestratorExhausted(RuntimeError):
    pass


def _state_db_path() -> str:
    explicit = os.environ.get("ORCHESTRATOR_STATE_DB", "").strip()
    if explicit:
        return explicit
    control_db = os.environ.get("CONTROL_OPERATIONS_DB", "").strip()
    if control_db:
        return control_db
    return str(Path(__file__).resolve().parents[1] / "data" / "control-operations.sqlite3")


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
            INSERT INTO provider_health(provider,disabled_until,failures,last_error,updated)
            VALUES (?,0,0,'',?)
            ON CONFLICT(provider) DO UPDATE SET disabled_until=0,failures=0,last_error='',updated=excluded.updated
            """,
            (name, now),
        )


def _record_failure(name: str, error: Exception, cooldown: bool) -> None:
    now = time.time()
    disabled_until = now + _cooldown_seconds() if cooldown else 0
    with _connect() as db:
        db.execute(
            """
            INSERT INTO provider_health(provider,disabled_until,failures,last_error,updated)
            VALUES (?,?,1,?,?)
            ON CONFLICT(provider) DO UPDATE SET
              disabled_until=CASE WHEN excluded.disabled_until>provider_health.disabled_until THEN excluded.disabled_until ELSE provider_health.disabled_until END,
              failures=provider_health.failures+1,
              last_error=excluded.last_error,
              updated=excluded.updated
            """,
            (name, disabled_until, str(error)[:500], now),
        )


def _should_cooldown(status: int, body: str) -> bool:
    text = body.lower()
    markers = ("quota", "rate limit", "rate_limit", "insufficient_quota", "resource_exhausted", "overloaded", "capacity", "too many requests")
    return status in {401, 403, 408, 409, 429, 500, 502, 503, 504} or any(m in text for m in markers)


def _gemini(model: str, prompt: str) -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise ProviderUnavailable("GEMINI_API_KEY missing")
    response = requests.post(
        GEMINI_URL.format(model=model),
        params={"key": key},
        headers={"Content-Type": "application/json"},
        json={"contents": [{"role": "user", "parts": [{"text": prompt}]}]},
        timeout=120,
    )
    if response.status_code >= 400:
        message = f"Gemini HTTP {response.status_code}: {response.text[:300]}"
        if _should_cooldown(response.status_code, response.text):
            raise ProviderUnavailable(message)
        raise RuntimeError(message)
    text = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    if text:
        return text
    raise ProviderUnavailable("Gemini response shape invalid or empty")


# Free Gemini text models only. OpenAI/GPT and Anthropic/Claude are intentionally
# excluded from generation, fallback, and LLM-assisted audit chains.
CALLERS: dict[str, Callable[[str, str], str]] = {
    "gemini": _gemini,
}


def _models() -> dict[str, str]:
    return {
        "gemini": os.environ.get("ORCHESTRATOR_GEMINI_MODEL", "gemini-3.8-flash").strip(),
    }


def _default_chain(task_type: str) -> list[ProviderSpec]:
    primary = _models()["gemini"]
    raw = os.environ.get(
        "ORCHESTRATOR_GEMINI_MODELS",
        "gemini-3.8-flash,gemini-2.5-flash,gemini-2.5-flash-lite,gemini-2.0-flash-lite",
    )
    ordered = [model.strip() for model in raw.split(",") if model.strip()]
    if primary:
        ordered = [primary] + [model for model in ordered if model != primary]
    # The same Gemini-only policy applies to writing, review, verification assistance,
    # and orchestration tasks. Deterministic external audit remains the final authority.
    return [ProviderSpec("gemini", model) for model in dict.fromkeys(ordered)]


def _chain_from_env(task_type: str) -> list[ProviderSpec]:
    # Legacy chain variables may still contain GPT/Claude entries; ignore them.
    # Only Gemini model names are accepted, and only from the explicit Gemini list.
    return _default_chain(task_type)



def generate_text(prompt: str, *, task_type: str = "pm", task_id: str = "",
                  actor: str = "orchestrator") -> tuple[str, dict[str, object]]:
    attempts: list[dict[str, str]] = []
    for spec in _chain_from_env(task_type):
        if not _provider_available(spec.name):
            attempts.append({"provider": spec.name, "model": spec.model, "result": "cooldown"})
            if task_id:
                london_activity.record_note(task_id, actor=actor, event_type="PROVIDER_COOLDOWN_SKIP",
                                            detail={"provider": spec.name, "model": spec.model})
            continue
        try:
            text = CALLERS[spec.name](spec.model, prompt)
            _record_success(spec.name)
            attempts.append({"provider": spec.name, "model": spec.model, "result": "success"})
            if task_id:
                london_activity.record_attempt(task_id, actor=actor, provider=spec.name,
                                               action=task_type, success=True,
                                               detail={"model": spec.model})
            return text, {"provider": spec.name, "model": spec.model, "attempts": attempts}
        except ProviderUnavailable as exc:
            _record_failure(spec.name, exc, True)
            attempts.append({"provider": spec.name, "model": spec.model, "result": str(exc)[:180]})
            if task_id:
                london_activity.record_attempt(task_id, actor=actor, provider=spec.name,
                                               action=task_type, success=False,
                                               detail={"model": spec.model}, error=str(exc))
        except requests.RequestException as exc:
            _record_failure(spec.name, exc, True)
            attempts.append({"provider": spec.name, "model": spec.model, "result": str(exc)[:180]})
            if task_id:
                london_activity.record_attempt(task_id, actor=actor, provider=spec.name,
                                               action=task_type, success=False,
                                               detail={"model": spec.model}, error=str(exc))
        except Exception as exc:
            _record_failure(spec.name, exc, False)
            attempts.append({"provider": spec.name, "model": spec.model, "result": str(exc)[:180]})
            if task_id:
                london_activity.record_attempt(task_id, actor=actor, provider=spec.name,
                                               action=task_type, success=False,
                                               detail={"model": spec.model}, error=str(exc))
    if task_id:
        london_activity.record_note(task_id, actor=actor, event_type="ORCHESTRATOR_EXHAUSTED",
                                    detail={"attempts": attempts})
    raise OrchestratorExhausted("All providers failed: " + json.dumps(attempts, ensure_ascii=False))


def provider_health() -> list[dict[str, object]]:
    now = time.time()
    with _connect() as db:
        rows = db.execute("SELECT provider,disabled_until,failures,last_error,updated FROM provider_health ORDER BY provider").fetchall()
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
