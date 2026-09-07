#!/usr/bin/env python3
"""Generate fresh music and images through the Gemini Interactions API."""
from __future__ import annotations

import base64
import os
import time
from pathlib import Path

import requests

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/interactions"
TERMINAL_FAILURES = {"failed", "cancelled", "canceled", "expired"}


def _api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is required for fresh Lyria music and thumbnail generation")
    return key


def _request(method: str, url: str, **kwargs) -> dict:
    headers = dict(kwargs.pop("headers", {}))
    headers["x-goog-api-key"] = _api_key()
    response = requests.request(method, url, headers=headers, timeout=kwargs.pop("timeout", 180), **kwargs)
    if not response.ok:
        raise RuntimeError(f"Gemini Interactions API failed ({response.status_code}): {response.text[:500]}")
    return response.json()


def create_interaction(model: str, prompt: str, response_format: dict) -> dict:
    payload = _request("POST", API_ROOT, json={"model": model, "input": prompt, "response_format": response_format})
    deadline = time.monotonic() + int(os.environ.get("GEMINI_INTERACTION_TIMEOUT_SECONDS", "1200"))
    while str(payload.get("status", "completed")).lower() not in {"completed", "succeeded"}:
        status = str(payload.get("status", "")).lower()
        if status in TERMINAL_FAILURES:
            raise RuntimeError(f"Gemini interaction ended with status={status}: {payload.get('error')}")
        interaction_id = payload.get("id")
        if not interaction_id or time.monotonic() >= deadline:
            raise RuntimeError("Gemini interaction did not complete before the timeout")
        time.sleep(float(os.environ.get("GEMINI_INTERACTION_POLL_SECONDS", "5")))
        payload = _request("GET", f"{API_ROOT}/{interaction_id}")
    return payload


def _media_bytes(payload: dict, media_type: str) -> bytes:
    candidates = []
    for step in payload.get("steps", []) or []:
        if step.get("type") == "model_output":
            candidates.extend(step.get("content", []) or [])
    output = payload.get("output")
    candidates.extend(output if isinstance(output, list) else [output] if isinstance(output, dict) else [])
    for block in candidates:
        if not isinstance(block, dict) or block.get("type") != media_type:
            continue
        data = block.get("data")
        if isinstance(data, str) and data:
            try:
                return base64.b64decode(data, validate=True)
            except ValueError as exc:
                raise RuntimeError(f"Gemini returned invalid base64 {media_type} data") from exc
    raise RuntimeError(f"Gemini interaction completed without {media_type} data")


def generate_lyria_track(prompt: str, output_path: str | Path) -> Path:
    payload = create_interaction(os.environ.get("LYRIA_MODEL", "lyria-3.5").strip(), prompt, {"type": "audio"})
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_media_bytes(payload, "audio"))
    if path.stat().st_size < 1024:
        raise RuntimeError("Lyria returned an unexpectedly small audio file")
    return path


def generate_thumbnail(prompt: str, output_path: str | Path) -> Path:
    payload = create_interaction(os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image").strip(), prompt,
                                 {"type": "image", "aspect_ratio": "16:9", "image_size": "2K"})
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_media_bytes(payload, "image"))
    if path.stat().st_size < 1024:
        raise RuntimeError("Gemini returned an unexpectedly small thumbnail")
    return path
