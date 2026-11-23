"""Single approved Gemini writer, language-aware six-stage fallback."""
from __future__ import annotations
import os
import requests
from content_engine_policy_20261110 import text_fallback_models

last_writer_model = "none"

def gemini_generate_text(prompt: str, *, temperature: float = 0.7, language: str | None = None) -> str:
    global last_writer_model
    from urllib.parse import urlparse
    host = (urlparse(os.getenv("TARGET_SITE_URL", "")).hostname or "").lower()
    lang = language or os.getenv("CONTENT_LANGUAGE") or os.getenv("SITE_LANGUAGE")
    if not lang:
        lang = "ko" if host in {"koreanews365.com", "k-health365.com", "koreanews365daily.blogspot.com"} else "en"
    # 2026-11-23: this only ever read GEMINI_API_KEY (GOOGLE_API_KEY as a
    # name fallback) -- GEMINI_API_KEY_2/_3, already configured as secrets
    # and passed into every publishing workflow, were never read at all.
    # Gemini's free-tier rate limit applies per Google Cloud project, not
    # per key, so every model attempt across every site today hammered the
    # same single project's quota; separate keys from separate projects
    # each carry their own quota. Try each configured key in turn, running
    # the full model chain under each before moving to the next.
    keys = [os.getenv(x, "").strip() for x in ("GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3", "GOOGLE_API_KEY")]
    keys = [k for k in keys if k]
    if not keys:
        raise RuntimeError("GEMINI_API_KEY missing")
    failures = []
    for key_index, key in enumerate(keys):
        for model in text_fallback_models(lang):
            try:
                response = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    headers={"x-goog-api-key": key},
                    json={"contents": [{"parts": [{"text": prompt}]}],
                          "generationConfig": {"temperature": temperature, "maxOutputTokens": 16384}},
                    timeout=120,
                )
                response.raise_for_status()
                payload = response.json()
                candidate = (payload.get("candidates") or [{}])[0]
                if candidate.get("finishReason") != "STOP":
                    raise ValueError("incomplete generation")
                result = "".join(p.get("text", "") for p in candidate.get("content", {}).get("parts", []))
                if not result.strip():
                    raise ValueError("empty generation")
                last_writer_model = model
                print(f"Gemini writer success: {lang} {model} (key #{key_index + 1})")
                return result.strip()
            except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                failures.append(f"key{key_index + 1}:{model}:{type(exc).__name__}")
                print(f"Gemini writer fallback: {lang} {model} key#{key_index + 1} {type(exc).__name__}")
    raise RuntimeError("WRITERS_EXHAUSTED: " + "; ".join(failures))
