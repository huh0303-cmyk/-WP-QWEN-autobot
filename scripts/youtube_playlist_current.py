#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Policy wrapper for youtube_playlist_maker.py.

Hard policy (2026-08-27): all generated/still imagery must come through the approved
Replicate 3-model gateway. Legacy Gemini/OpenAI image generation and Pexels/Pixabay
photo fallbacks are blocked. YouTube playlist text remains OpenAI/GPT-only.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

# Force GPT text policy and disable legacy paid image switches before importing the
# historical maker module.
os.environ["AI_TEXT_PROVIDER"] = "openai"
os.environ["OPENAI_ENABLED"] = "true"
os.environ["OPENAI_IMAGE_ENABLED"] = "false"
os.environ["PAID_IMAGE_GENERATION_ENABLED"] = "false"

import youtube_playlist_maker as base
from replicate_image_provider import generate_image_url

# Remove credentials from active legacy paths even if stale GitHub secrets still exist.
base.GEMINI_API_KEY = ""
base.GEMINI_IMAGE_MODELS = []
base.PEXELS_API_KEY = ""
base.PIXABAY_KEY = ""


def _download(url: str, out_path: str) -> None:
    response = requests.get(url, timeout=90, stream=True)
    response.raise_for_status()
    with open(out_path, "wb") as handle:
        for chunk in response.iter_content(chunk_size=1 << 20):
            if chunk:
                handle.write(chunk)


def _replicate_generate_image(prompt: str, out_path: str) -> bool:
    url = generate_image_url(prompt, theme=f"YouTube playlist {base.CHANNEL_KEY or 'default'}")
    if not url:
        return False
    try:
        _download(url, out_path)
        return True
    except Exception as exc:
        base.log(f"   ⚠️ Replicate image download failed: {exc}")
        return False


def _blocked_photo_search(*args, **kwargs):
    return None


def _replicate_healing_photo(theme: str, workdir: str):
    subject = base.HEALING_THEME_TOPICS.get(theme, theme)
    url = generate_image_url(subject, theme="YouTube healing nature ambience")
    if not url:
        return None
    path = os.path.join(workdir, "healing_photo_replicate.webp")
    try:
        _download(url, path)
        return path
    except Exception as exc:
        base.log(f"   ⚠️ Replicate healing image download failed: {exc}")
        return None


# Hard replace all known legacy still-image generation/search call sites.
base.gemini_generate_image = _replicate_generate_image
base._search_pexels_photo = _blocked_photo_search
base._search_pixabay_photo = _blocked_photo_search
base.fetch_healing_photo = _replicate_healing_photo

if __name__ == "__main__":
    base.main()
