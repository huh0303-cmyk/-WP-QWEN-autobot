#!/usr/bin/env python3
"""Zero-cost local text fallback through Ollama on the Korea365 VPS."""
from __future__ import annotations

import os
import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")

def local_generate_text(prompt: str, *, temperature: float = 0.6, timeout: int = 75) -> str:
    response = requests.post(
        OLLAMA_URL + "/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "5m",
            "options": {"temperature": temperature, "num_predict": 1800},
        },
        timeout=timeout,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Ollama unavailable: HTTP {response.status_code}")
    text = str(response.json().get("response", "")).strip()
    if not text:
        raise RuntimeError("Ollama returned empty text")
    return text
