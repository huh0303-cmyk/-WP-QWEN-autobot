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


import time as _time

# ---- process-wide engine health (one publisher process writes many articles) ----
_DEAD: set = set()          # (provider, key_id, model) that returned 400/401/403/404: do not retry this run
_COOLDOWN: dict = {}        # (provider, key_id, model) -> epoch seconds until which a 429 keeps it parked
_KEY_NAMES = ("GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3")


def _gemini_keys() -> list:
    """Up to three independent free-tier Gemini keys (separate projects = separate quotas).
    Values shorter than 20 chars are placeholders/broken secrets and are ignored."""
    keys = []
    for name in _KEY_NAMES:
        value = os.getenv(name, "").strip()
        if len(value) >= 20 and value not in [k for _, k in keys]:
            keys.append((name, value))
    return keys


def _parked(provider: str, key_id: str, model: str) -> bool:
    ident = (provider, key_id, model)
    if ident in _DEAD or (provider, key_id, "*") in _DEAD:
        return True
    return _COOLDOWN.get(ident, 0) > _time.time()


def _note_failure(provider: str, key_id: str, model: str, exc: Exception) -> None:
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status in (401, 403):
        _DEAD.add((provider, key_id, "*"))          # the whole key is bad
    elif status in (400, 404):
        _DEAD.add((provider, key_id, model))        # this model is unusable for this key
    elif status == 429:
        _COOLDOWN[(provider, key_id, model)] = _time.time() + float(os.getenv("WRITER_429_COOLDOWN", "900"))
    elif isinstance(exc, ValueError) and "incomplete" in str(exc):
        _DEAD.add((provider, key_id, model))        # keeps truncating: not worth more tries this run


def engine_health() -> dict:
    return {"dead": sorted("/".join(map(str, d)) for d in _DEAD),
            "cooling": sorted("/".join(map(str, d)) for d, t in _COOLDOWN.items() if t > _time.time())}


def _try_gemini(prompt: str, temperature: float, model: str, key: str | None = None) -> str:
    global last_writer_model
    key = (key or os.getenv("GEMINI_API_KEY", "")).strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing")
    if model not in FREE_GEMINI_MODELS:
        raise ValueError("unsupported Gemini model")
    config = {"temperature": temperature, "maxOutputTokens": int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "16384"))}
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
        raise ValueError(f"Gemini response incomplete finish={candidate.get('finishReason')}")
    last_writer_model = model
    _record("gemini", model, data.get("usageMetadata"))
    return content.strip()


TRIES_PER_ENGINE = int(os.getenv("WRITER_TRIES_PER_ENGINE", "4"))
RETRY_SLEEP = float(os.getenv("WRITER_RETRY_SLEEP", "5"))

# Independent free-tier engines beyond Gemini. Each activates only when its key secret exists.
# (provider, key env, endpoint, default model env, default model)
OPENAI_COMPAT = (
    ("groq", "GROQ_API_KEY", "https://api.groq.com/openai/v1/chat/completions",
     "GROQ_MODEL", "openai/gpt-oss-120b,openai/gpt-oss-20b,llama-3.3-70b-versatile,qwen/qwen3-32b"),
    ("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1/chat/completions",
     "OPENROUTER_MODEL", "google/gemma-4-31b-it:free,openai/gpt-oss-120b:free,qwen/qwen3-next-80b-a3b-instruct:free,"
                         "meta-llama/llama-3.3-70b-instruct:free,deepseek/deepseek-chat-v3.1:free"),
    ("cerebras", "CEREBRAS_API_KEY", "https://api.cerebras.ai/v1/chat/completions",
     "CEREBRAS_MODEL", "llama-3.3-70b,gpt-oss-120b"),
)


_DISCOVERED: dict = {}
_PREFER = ("gpt-oss-120b", "llama-3.3-70b", "qwen3", "gemma", "deepseek", "gpt-oss-20b", "llama")
_SKIP = ("allam", "whisper", "guard", "tts", "orpheus", "embed", "vision", "image", "audio", "safeguard", "moderation", "lyria", "veo")


def _discover(spec: tuple) -> list:
    """Ask the provider which models this key can use right now (free-model slugs rotate), once per process."""
    provider, key_env, url = spec[0], spec[1], spec[2]
    if provider in _DISCOVERED:
        return _DISCOVERED[provider]
    ids: list = []
    key = os.getenv(key_env, "").strip()
    try:
        r = requests.get(url.rsplit("/chat/completions", 1)[0] + "/models",
                         headers={"Authorization": f"Bearer {key}"}, timeout=20)
        r.raise_for_status()
        for m in r.json().get("data", []):
            mid = str(m.get("id", ""))
            if not mid or any(x in mid.lower() for x in _SKIP):
                continue
            if provider == "openrouter":
                if not any(f in mid.lower() for f in ("gemma", "qwen", "llama", "gpt-oss", "deepseek", "mistral", "nemotron", "glm")):
                    continue
                price = m.get("pricing") or {}
                if not (mid.endswith(":free") or (str(price.get("prompt")) == "0" and str(price.get("completion")) == "0")):
                    continue
            ids.append(mid)
    except Exception:
        ids = []
    ids.sort(key=lambda m: next((i for i, p in enumerate(_PREFER) if p in m.lower()), len(_PREFER)))
    _DISCOVERED[provider] = ids[:8]
    return _DISCOVERED[provider]


def _compat_models(spec: tuple) -> list:
    """Configured models first (env override or defaults), then whatever the provider currently offers for free."""
    models = [m.strip() for m in os.getenv(spec[3], spec[4]).split(",") if m.strip()]
    if spec[0] in ("groq", "openrouter") and os.getenv(spec[1], "").strip():
        models += [m for m in _discover(spec) if m not in models]
    return models


def _try_compat(prompt: str, temperature: float, spec: tuple, model: str | None = None) -> str:
    global last_writer_model
    provider, key_env, url, model_env, default_model = spec
    key = os.getenv(key_env, "").strip()
    if not key:
        raise RuntimeError(f"{key_env} missing")
    model = model or _compat_models(spec)[0]
    response = requests.post(
        url, headers={"Authorization": f"Bearer {key}"},
        json=({"model": model, "temperature": temperature, "max_tokens": 6144,
               "messages": [{"role": "user", "content": prompt}]}
              | ({"reasoning_effort": "low"} if provider == "groq" and "gpt-oss" in model else {})),
        timeout=120)
    response.raise_for_status()
    data = response.json()
    choice = (data.get("choices") or [{}])[0]
    text = (choice.get("message") or {}).get("content") or ""
    if choice.get("finish_reason") not in ("stop", None) or not text.strip():
        raise ValueError(f"{provider} response incomplete")
    last_writer_model = f"{provider}:{model}"
    _record(provider, model, data.get("usage"))
    return text.strip()


def _with_tries(label: str, fn, failures: list, on_error=None, tries=None):
    """같은 엔진을 일시 장애 시 TRIES_PER_ENGINE번까지 시도."""
    import time
    tries = tries or TRIES_PER_ENGINE
    for n in range(1, tries + 1):
        try:
            return fn()
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            if on_error:
                on_error(exc)
            failures.append(f"{label}#{n}: {_failure_summary(exc)} {str(exc)[:80] if isinstance(exc, ValueError) else ''}")
            print(f"Article writer fallback: {failures[-1]}")
            status = getattr(getattr(exc, "response", None), "status_code", None)
            # 재시도는 일시 장애(타임아웃·연결·5xx·불완전 응답)만. 쿼터(429)·인증(401/403)·키 없음은
            # 같은 엔진을 다시 호출해도 소용없으므로 바로 다음 엔진으로.
            transient = (isinstance(exc, (requests.Timeout, requests.ConnectionError, ValueError))
                         or (status is not None and status >= 500))
            if not transient:
                break
            if n < tries:
                time.sleep(RETRY_SLEEP * (2 ** (n - 1)))  # 5s,10s,20s backoff for 503 overload
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
    keys = _gemini_keys()
    if not keys and models:
        failures.append("gemini: no valid key (GEMINI_API_KEY*, >=20 chars)")
    for model in models:
        for key_id, key in keys:
            if _parked("gemini", key_id, model):
                continue
            attempt_id = f"{model}@{key_id}"
            if _article_attempts is not None:
                if attempt_id in _article_attempts:
                    continue
                _article_attempts.add(attempt_id)
            try:
                text = _with_tries(attempt_id, lambda m=model, k=key: _try_gemini(prompt, temperature, m, k), failures,
                                   on_error=lambda e, m=model, kid=key_id: _note_failure("gemini", kid, m, e))
            except Exception as exc:  # never let one engine abort the chain
                failures.append(f"{attempt_id}: {_failure_summary(exc)}")
                text = None
            if text:
                return text

    # 독립 무료 엔진들(키가 있을 때만): 엔진별 모델 목록을 차례로, 죽은/한도 초과 모델은 건너뜀
    if choice != "gpt-5-mini":
        for spec in OPENAI_COMPAT:
            if not os.getenv(spec[1], "").strip():
                continue
            for model in _compat_models(spec):
                if _parked(spec[0], spec[1], model):
                    continue
                text = _with_tries(f"{spec[0]}:{model}", lambda sp=spec, m=model: _try_compat(prompt, temperature, sp, m),
                                   failures, on_error=lambda e, sp=spec, m=model: _note_failure(sp[0], sp[1], m, e), tries=2)
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
            text = local_generate_text(prompt, temperature=temperature,
                                       timeout=int(os.getenv("LOCAL_TEXT_TIMEOUT", "190")),
                                       max_tokens=int(os.getenv("LOCAL_TEXT_MAX_TOKENS", "1800")))
            last_writer_model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
            _record("ollama", last_writer_model)
            return text
        except Exception as exc:
            failures.append(f"local: {_failure_summary(exc)}")
    raise RuntimeError("WRITERS_EXHAUSTED: " + "; ".join(failures or ["no configured writer"]))
