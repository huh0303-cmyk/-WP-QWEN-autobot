"""Article text generation with a free Gemini fallback chain."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

# Each listed model has a documented free Standard API tier.
FREE_GEMINI_MODELS = (
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash-lite",
)
last_writer_model = "not_called"
_article_attempts: set[str] | None = None


def begin_article():
    global _article_attempts, last_writer_model
    _article_attempts = set()
    last_writer_model = "not_called"


def _failure_summary(exc: Exception) -> str:
    status = getattr(getattr(exc, "response", None), "status_code", None)
    return f"{type(exc).__name__} HTTP {status}" if status else type(exc).__name__


def _record(provider: str, model: str, usage: dict | None = None) -> None:
    receipt = Path("artifacts/article-writer-usage.jsonl")
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with receipt.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(),
                                 "provider": provider, "model": model, "usage": usage or {}},
                                ensure_ascii=False) + "\n")


def _try_gemini(prompt: str, temperature: float, model: str) -> str:
    global last_writer_model
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing")
    if model not in FREE_GEMINI_MODELS:
        raise ValueError("unsupported Gemini model")
    config = {"temperature": temperature, "maxOutputTokens": 8192}
    if model.startswith("gemini-2.5-"):
        config["thinkingConfig"] = {"thinkingBudget": 0}
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key},
        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": config},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    candidate = (data.get("candidates") or [{}])[0]
    content = "".join(part.get("text", "") for part in candidate.get("content", {}).get("parts", []))
    if candidate.get("finishReason") != "STOP" or not content.strip():
        raise ValueError("Gemini response incomplete")
    last_writer_model = model
    _record("gemini", model, data.get("usageMetadata"))
    return content.strip()


TRIES_PER_ENGINE = int(os.getenv("WRITER_TRIES_PER_ENGINE", "2"))
RETRY_SLEEP = float(os.getenv("WRITER_RETRY_SLEEP", "3"))

# Independent free-tier engines beyond Gemini. Each activates only when its key secret exists.
# (provider, key env, endpoint, default model env, default model)
OPENAI_COMPAT = (
    ("groq", "GROQ_API_KEY", "https://api.groq.com/openai/v1/chat/completions",
     "GROQ_MODEL", "llama-3.3-70b-versatile"),
    ("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1/chat/completions",
     "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
    ("cerebras", "CEREBRAS_API_KEY", "https://api.cerebras.ai/v1/chat/completions",
     "CEREBRAS_MODEL", "llama-3.3-70b"),
)


def _try_compat(prompt: str, temperature: float, spec: tuple) -> str:
    global last_writer_model
    provider, key_env, url, model_env, default_model = spec
    key = os.getenv(key_env, "").strip()
    if not key:
        raise RuntimeError(f"{key_env} missing")
    model = os.getenv(model_env, default_model)
    response = requests.post(
        url, headers={"Authorization": f"Bearer {key}"},
        json={"model": model, "temperature": temperature, "max_tokens": 8192,
              "messages": [{"role": "user", "content": prompt}]}, timeout=90)
    response.raise_for_status()
    data = response.json()
    choice = (data.get("choices") or [{}])[0]
    text = (choice.get("message") or {}).get("content") or ""
    if choice.get("finish_reason") not in ("stop", None) or not text.strip():
        raise ValueError(f"{provider} response incomplete")
    last_writer_model = f"{provider}:{model}"
    _record(provider, model, data.get("usage"))
    return text.strip()


def _with_tries(label: str, fn, failures: list):
    """같은 엔진을 일시 장애 시 TRIES_PER_ENGINE번까지 시도."""
    import time
    for n in range(1, TRIES_PER_ENGINE + 1):
        try:
            return fn()
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            failures.append(f"{label}#{n}: {_failure_summary(exc)}")
            print(f"Article writer fallback: {failures[-1]}")
            status = getattr(getattr(exc, "response", None), "status_code", None)
            # 재시도는 일시 장애(타임아웃·연결·5xx·불완전 응답)만. 쿼터(429)·인증(401/403)·키 없음은
            # 같은 엔진을 다시 호출해도 소용없으므로 바로 다음 엔진으로.
            transient = (isinstance(exc, (requests.Timeout, requests.ConnectionError, ValueError))
                         or (status is not None and status >= 500))
            if not transient:
                break
            if n < TRIES_PER_ENGINE:
                time.sleep(RETRY_SLEEP)
    return None


def _model_chain(choice: str) -> tuple[str, ...]:
    if choice == "auto_free":
        return FREE_GEMINI_MODELS
    if choice in FREE_GEMINI_MODELS:
        return (choice,) + tuple(model for model in FREE_GEMINI_MODELS if model != choice)
    if choice in {"local_qwen", "gpt-5-mini"}:
        return ()
    raise ValueError("unsupported writer model")


def generate_text(prompt, temperature=0.7, force_gpt=False, repair=False, writer_model=None):
    global last_writer_model
    from urllib.parse import urlparse
    target = urlparse(os.getenv("TARGET_SITE_URL", "")).hostname
    if os.getenv("NEWSROOM_PAID_TEXT_APPROVED", "").lower() == "true" and target in {"koreanews365.com", "theseouljournal.com"}:
        if os.getenv("OPENAI_MODEL", "") != "gpt-5-mini":
            raise RuntimeError("Newsroom paid exception permits gpt-5-mini only")
        import newsroom_provider_recovery as recovery
        text = recovery.generate(prompt, temperature=temperature)
        last_writer_model = recovery.last_model
        return text

    choice = "gpt-5-mini" if force_gpt else (writer_model or os.getenv("LONDON_WRITER_MODEL", "auto_free"))
    models = _model_chain(choice)
    failures: list[str] = []
    for model in models:
        if _article_attempts is not None and model in _article_attempts:
            continue
        if _article_attempts is not None:
            _article_attempts.add(model)
        text = _with_tries(model, lambda m=model: _try_gemini(prompt, temperature, m), failures)
        if text:
            return text

    # 독립 무료 엔진들(키가 있을 때만): 각 엔진 2회 시도 후 다음 엔진
    if choice != "gpt-5-mini":
        for spec in OPENAI_COMPAT:
            if not os.getenv(spec[1], "").strip():
                continue
            text = _with_tries(spec[0], lambda sp=spec: _try_compat(prompt, temperature, sp), failures)
            if text:
                return text

    # GPT is paid and only used when the operator explicitly selects it.
    if choice == "gpt-5-mini":
        try:
            from openai_text import openai_available, openai_generate_text
            if not openai_available():
                raise RuntimeError("GPT API unavailable")
            text = openai_generate_text(prompt, temperature=temperature, max_retries=1, timeout=45)
            last_writer_model = "gpt-5-mini"
            _record("openai", "gpt-5-mini")
            return text
        except Exception as exc:
            failures.append(f"gpt-5-mini: {_failure_summary(exc)}")
            for model in FREE_GEMINI_MODELS:
                try:
                    return _try_gemini(prompt, temperature, model)
                except (requests.RequestException, ValueError, RuntimeError) as gemini_exc:
                    failures.append(f"{model}: {_failure_summary(gemini_exc)}")

    if os.getenv("LOCAL_TEXT_FALLBACK_ENABLED", "false").lower() in {"1", "true", "yes", "on"}:
        try:
            from local_text import local_generate_text
            text = local_generate_text(prompt, temperature=temperature, timeout=190)
            last_writer_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
            _record("ollama", last_writer_model)
            return text
        except Exception as exc:
            failures.append(f"local: {_failure_summary(exc)}")
    raise RuntimeError("WRITERS_EXHAUSTED: " + "; ".join(failures or ["no configured writer"]))
