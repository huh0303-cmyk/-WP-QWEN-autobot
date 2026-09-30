"""Three free-tier Gemini model endpoints for the daily Blogger publisher."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests


KST = ZoneInfo("Asia/Seoul")
CONFIG = Path(os.environ.get("BLOGGER_FREE_WRITER_CONFIG", "/etc/korea365/free-writer.json"))
STATE = Path(os.environ.get("BLOGGER_FREE_MODEL_STATE", "/opt/korea365/data/blogger33-free-model-state.json"))
MODELS = ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite")


def _free_config(now: datetime) -> dict:
    config = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
    if config.get("billing_verified") != "free_tier":
        raise RuntimeError("free_tier_not_verified")
    # The billing tier is an explicit server-held policy setting. A date-based
    # expiry silently disabled this path on 2026-10-01 despite no tier change.
    datetime.fromisoformat(config["verified_at"])
    if not str(config.get("api_key", "")).strip():
        raise RuntimeError("free_tier_api_key_missing")
    return config


def _state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"model_cooldowns": {}}


def _save(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    temporary.replace(STATE)


def free_blogger_generate_text(prompt: str, *, temperature: float = 0.5) -> str:
    now = datetime.now(KST)
    config = _free_config(now)
    state = _state()
    cooldowns = state.setdefault("model_cooldowns", {})
    unavailable = False
    for model in MODELS:
        until = cooldowns.get(model)
        if until and datetime.fromisoformat(until) > now:
            continue
        options = {
            "temperature": temperature,
            "responseMimeType": "application/json",
            "maxOutputTokens": 16384,
        }
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": config["api_key"]},
            json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": options},
            timeout=120,
        )
        if response.status_code == 429:
            cooldowns[model] = (now + timedelta(hours=1)).isoformat()
            _save(state)
            continue
        if response.status_code in {500, 502, 503, 504}:
            unavailable = True
            continue
        if not response.ok:
            # A model may be unavailable on this project's free tier. Try the
            # next approved model, never the paid API key.
            unavailable = True
            continue
        data = response.json()
        candidate = (data.get("candidates") or [{}])[0]
        if candidate.get("finishReason") != "STOP":
            raise RuntimeError("incomplete_generation")
        text = "".join(part.get("text", "") for part in candidate.get("content", {}).get("parts", []))
        if not text.strip():
            raise RuntimeError("empty_generation")
        state["last_successful_model"] = model
        _save(state)
        return text
    if unavailable:
        raise RuntimeError("free_provider_temporarily_unavailable")
    raise RuntimeError("free_quota_wait_no_paid_fallback")
