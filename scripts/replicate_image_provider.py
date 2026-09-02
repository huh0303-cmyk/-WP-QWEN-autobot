#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single approved image-generation gateway for the automation repository.

HARD POLICY (2026-09-02):
- SDXL Lightning 4-step is attempted first.
- FLUX Schnell is attempted once only when SDXL Lightning fails.
- Only the two models in ALLOWED_MODELS may be called.
- One shared secret: REPLICATE_API_TOKEN.
- At most one output image per content item and one attempt per model.
- No stock-photo, OpenAI image, Gemini image, Stability API, or other fallback.
- If all approved models fail, return no image rather than using a legacy provider.
"""

from __future__ import annotations

import hashlib
import os
import time
from typing import Optional

import requests

REPLICATE_API = "https://api.replicate.com/v1"

PRIMARY_MODEL = "bytedance/sdxl-lightning-4step"
SECONDARY_MODEL = "black-forest-labs/flux-schnell"
ALLOWED_MODELS = (
    PRIMARY_MODEL,
    SECONDARY_MODEL,
)

# Cost guardrails. Deliberately hard-clamped; env vars cannot raise these limits.
MAX_IMAGES_PER_CONTENT = 1
MAX_MODEL_ATTEMPTS = len(ALLOWED_MODELS)  # one attempt per approved model only
PREFER_WAIT_SECONDS = 45
POLL_INTERVAL_SECONDS = 2
MAX_POLL_SECONDS = 60

# Process-local idempotency. A repeated request for the same prompt does not create
# another paid prediction within one workflow process.
_prompt_cache: dict[str, Optional[str]] = {}
_attempted_prompts: set[str] = set()


def _token() -> str:
    return os.getenv("REPLICATE_API_TOKEN", "").strip()


def _headers(token: str, *, prefer_wait: bool = False) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if prefer_wait:
        headers["Prefer"] = f"wait={PREFER_WAIT_SECONDS}"
        headers["Cancel-After"] = "60s"
    return headers


def _first_output_url(output) -> Optional[str]:
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


def _latest_version_id(model: str, token: str) -> Optional[str]:
    """Resolve a public community model's latest version without generating an image."""
    owner, name = model.split("/", 1)
    response = requests.get(
        f"{REPLICATE_API}/models/{owner}/{name}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    response.raise_for_status()
    latest = (response.json().get("latest_version") or {}).get("id")
    return latest if isinstance(latest, str) and latest else None


def _input_for(model: str, prompt: str) -> dict:
    # Force exactly one output on every approved model.
    if model == SECONDARY_MODEL:
        return {
            "prompt": prompt,
            "num_outputs": 1,
            "aspect_ratio": "16:9",
            "output_format": "webp",
            "output_quality": 82,
        }
    if model == PRIMARY_MODEL:
        return {
            "prompt": prompt,
            "width": 1024,
            "height": 576,
            "num_outputs": 1,
            "num_inference_steps": 4,
            "guidance_scale": 0,
            "negative_prompt": "text, logo, watermark, low quality, distorted",
        }
    raise RuntimeError(f"blocked image model: {model}")


def _create_prediction(model: str, prompt: str, token: str) -> dict:
    if model not in ALLOWED_MODELS:
        raise RuntimeError(f"blocked image model: {model}")

    payload = {"input": _input_for(model, prompt)}
    if model == SECONDARY_MODEL:
        owner, name = model.split("/", 1)
        endpoint = f"{REPLICATE_API}/models/{owner}/{name}/predictions"
    else:
        version_id = _latest_version_id(model, token)
        if not version_id:
            raise RuntimeError(f"no Replicate version available for {model}")
        endpoint = f"{REPLICATE_API}/predictions"
        payload["version"] = version_id

    response = requests.post(
        endpoint,
        headers=_headers(token, prefer_wait=True),
        json=payload,
        timeout=PREFER_WAIT_SECONDS + 15,
    )
    response.raise_for_status()
    return response.json()


def _await_prediction(prediction: dict, token: str) -> dict:
    status = prediction.get("status")
    if status in {"succeeded", "failed", "canceled"}:
        return prediction
    get_url = (prediction.get("urls") or {}).get("get")
    if not get_url:
        return prediction

    deadline = time.monotonic() + MAX_POLL_SECONDS
    while time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL_SECONDS)
        response = requests.get(get_url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
        response.raise_for_status()
        prediction = response.json()
        status = prediction.get("status")
        if status in {"succeeded", "failed", "canceled"}:
            return prediction
    return prediction


def build_editorial_prompt(subject: str, theme: str = "") -> str:
    subject = " ".join(str(subject or "").split())[:260]
    theme = " ".join(str(theme or "").split())[:120]
    context = f" Topic category: {theme}." if theme else ""
    newsroom = theme.upper().startswith("NEWS ILLUSTRATION ONLY")
    visual_style = (
        "Clearly editorial conceptual illustration, not a photograph and not evidence of the real event. "
        "Do not depict an identifiable real person, exact incident, casualty, disaster damage, weapon strike, "
        "or any scene that could be mistaken for contemporaneous documentary footage. "
        if newsroom else
        "Editorial documentary-style image. "
    )
    return (
        f"{visual_style}For an article about: {subject}.{context} "
        "Accurately represent the specific subject, natural realistic lighting, clean composition, "
        "NO TEXT ANYWHERE IN THE IMAGE. Do not show letters, words, numbers, writing, labels, captions, "
        "documents, forms, checklists, certificates, screens, signs, books, packaging, logos, watermarks, "
        "UI or brand marks. Avoid paper and display surfaces that could contain generated writing. "
        "Any illegible pseudo-text, fake Hangul, fake Chinese/Japanese characters or random glyphs is forbidden. 16:9."
    )


def generate_image_url(subject: str, theme: str = "") -> Optional[str]:
    """Generate at most one image using only the approved Replicate model chain."""
    token = _token()
    if not token:
        print("  ⛔ REPLICATE_API_TOKEN missing — image generation skipped; legacy fallback forbidden")
        return None

    prompt = build_editorial_prompt(subject, theme)
    cache_key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    if cache_key in _prompt_cache:
        return _prompt_cache[cache_key]
    if cache_key in _attempted_prompts:
        return None
    _attempted_prompts.add(cache_key)

    for attempt_no, model in enumerate(ALLOWED_MODELS, start=1):
        if attempt_no > MAX_MODEL_ATTEMPTS:
            break
        try:
            print(f"  🖼️ Replicate approved image model {attempt_no}/{MAX_MODEL_ATTEMPTS}: {model}")
            prediction = _await_prediction(_create_prediction(model, prompt, token), token)
            if prediction.get("status") == "succeeded":
                url = _first_output_url(prediction.get("output"))
                if url:
                    _prompt_cache[cache_key] = url
                    return url
            error = prediction.get("error") or prediction.get("status")
            print(f"  ⚠️ approved image model failed: {model} ({error})")
        except Exception as exc:
            print(f"  ⚠️ approved image model error: {model} ({exc})")

    print("  ℹ️ SDXL Lightning and FLUX Schnell both failed — continue without an image")
    _prompt_cache[cache_key] = None
    return None


def generate_image_urls(subject: str, count: int = 1, theme: str = "") -> list[str]:
    """Compatibility helper; count is intentionally clamped to one for cost safety."""
    if int(count or 1) > MAX_IMAGES_PER_CONTENT:
        print(f"  💰 image count clamped to {MAX_IMAGES_PER_CONTENT} by cost guard")
    url = generate_image_url(subject, theme=theme)
    return [url] if url else []
