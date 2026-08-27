#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FLUX-only image provider for YouTube thumbnails and their source visuals.

Policy lock (2026-08-27):
- YouTube thumbnail imagery uses black-forest-labs/flux-schnell only.
- No SDXL fallback, no Gemini image, no OpenAI image, no Pexels/Pixabay fallback.
- Exactly one generated image per prompt/process cache key.
- If FLUX fails, return None; callers may use a local non-API placeholder only.
"""
from __future__ import annotations

import hashlib
import os
import time
from typing import Optional

import requests

API = "https://api.replicate.com/v1"
FLUX_MODEL = "black-forest-labs/flux-schnell"
WAIT_SECONDS = 45
POLL_SECONDS = 2
MAX_POLL_SECONDS = 60
_cache: dict[str, Optional[str]] = {}


def _token() -> str:
    return os.getenv("REPLICATE_API_TOKEN", "").strip()


def _first_url(output) -> Optional[str]:
    if isinstance(output, str) and output.startswith("http"):
        return output
    if isinstance(output, list):
        for item in output:
            if isinstance(item, str) and item.startswith("http"):
                return item
            if isinstance(item, dict):
                url = item.get("url")
                if isinstance(url, str) and url.startswith("http"):
                    return url
    if isinstance(output, dict):
        url = output.get("url")
        if isinstance(url, str) and url.startswith("http"):
            return url
    return None


def generate_flux_thumbnail_url(subject: str, theme: str = "YouTube thumbnail") -> Optional[str]:
    token = _token()
    if not token:
        print("  ⛔ REPLICATE_API_TOKEN missing — FLUX thumbnail skipped")
        return None

    subject = " ".join(str(subject or "").split())[:500]
    theme = " ".join(str(theme or "").split())[:160]
    prompt = (
        f"High-impact professional YouTube thumbnail source image. Subject: {subject}. "
        f"Channel/theme: {theme}. Photorealistic editorial composition, strong focal subject, "
        "cinematic lighting, clean negative space for optional title overlay, highly legible at small size, "
        "no visible text, no captions, no logo, no watermark, no UI, 16:9 landscape."
    )
    key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    if key in _cache:
        return _cache[key]

    owner, name = FLUX_MODEL.split("/", 1)
    endpoint = f"{API}/models/{owner}/{name}/predictions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Prefer": f"wait={WAIT_SECONDS}",
        "Cancel-After": "60s",
    }
    payload = {
        "input": {
            "prompt": prompt,
            "num_outputs": 1,
            "aspect_ratio": "16:9",
            "output_format": "webp",
            "output_quality": 85,
        }
    }

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=WAIT_SECONDS + 15)
        response.raise_for_status()
        prediction = response.json()
        status = prediction.get("status")
        get_url = (prediction.get("urls") or {}).get("get")
        deadline = time.monotonic() + MAX_POLL_SECONDS
        while status not in {"succeeded", "failed", "canceled"} and get_url and time.monotonic() < deadline:
            time.sleep(POLL_SECONDS)
            poll = requests.get(get_url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
            poll.raise_for_status()
            prediction = poll.json()
            status = prediction.get("status")

        if prediction.get("status") == "succeeded":
            url = _first_url(prediction.get("output"))
            _cache[key] = url
            return url
        print(f"  ⚠️ FLUX thumbnail failed: {prediction.get('error') or prediction.get('status')}")
    except Exception as exc:
        print(f"  ⚠️ FLUX thumbnail error: {exc}")

    _cache[key] = None
    return None
