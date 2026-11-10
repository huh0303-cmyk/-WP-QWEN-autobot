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
    keys = [os.getenv(x, "").strip() for x in ("GEMINI_API_KEY", "GOOGLE_API_KEY")]
    key = next((k for k in keys if k), "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing")
    failures = []
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
            print(f"Gemini writer success: {lang} {model}")
            return result.strip()
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            failures.append(f"{model}:{type(exc).__name__}")
            print(f"Gemini writer fallback: {lang} {model} {type(exc).__name__}")
    raise RuntimeError("WRITERS_EXHAUSTED: " + "; ".join(failures))
