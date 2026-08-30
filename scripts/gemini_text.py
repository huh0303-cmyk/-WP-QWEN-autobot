from __future__ import annotations

import os

import requests


def gemini_generate_text(prompt: str, *, temperature: float = 0.7) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required for every Blogger article")
    model = os.environ.get("BLOGGER_GEMINI_MODEL", "gemini-2.5-flash").strip()
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": api_key},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            # No explicit maxOutputTokens previously meant relying on the
            # model's implicit default, which real test runs showed cutting
            # articles off mid-sentence well before their target length.
            "generationConfig": {"temperature": temperature, "responseMimeType": "application/json", "maxOutputTokens": 8192},
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Gemini returned no Blogger article text") from exc
