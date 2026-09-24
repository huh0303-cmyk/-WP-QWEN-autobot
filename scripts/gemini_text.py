from __future__ import annotations

import os
import time

import requests


def gemini_generate_text(prompt: str, *, temperature: float = 0.7) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required for every Blogger article")
    model = os.environ.get("BLOGGER_GEMINI_MODEL", "gemini-2.5-flash").strip()
    response = None
    for attempt in range(4):
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                # No explicit maxOutputTokens previously meant relying on the
                # model's implicit default, which real test runs showed cutting
                # articles off mid-sentence well before their target length.
                "generationConfig": {"temperature": temperature, "responseMimeType": "application/json", "maxOutputTokens": 16384},
            },
            timeout=120,
        )
        if response.status_code not in {429, 500, 502, 503, 504}:
            break
        if attempt < 3:
            time.sleep(5 * (2 ** attempt))
    assert response is not None
    if not response.ok:
        try:
            detail = response.json().get("error", {}).get("message", "")
        except (ValueError, AttributeError):
            detail = ""
        raise RuntimeError(f"Gemini request failed with HTTP {response.status_code}: {detail[:300]}")
    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Gemini returned no Blogger article text") from exc
