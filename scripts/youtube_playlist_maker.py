#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Active YouTube playlist entrypoint — Replicate-only image policy.

The historical implementation is preserved as youtube_playlist_maker_legacy.py.
This wrapper blocks all former image providers while retaining the mature audio,
Drive, rendering, metadata and upload preparation logic.
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

# Text for YouTube stays GPT/OpenAI. Old image-generation switches are forced off.
os.environ["AI_TEXT_PROVIDER"] = "openai"
os.environ["OPENAI_ENABLED"] = "true"
os.environ["OPENAI_IMAGE_ENABLED"] = "false"
os.environ["PAID_IMAGE_GENERATION_ENABLED"] = "false"

import youtube_playlist_maker_legacy as base
from replicate_image_provider import generate_image_url

# Remove all legacy image credentials from the active runtime, even if repository
# secrets with old names still exist.
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


def _approved_image(prompt: str, out_path: str) -> bool:
    url = generate_image_url(prompt, theme=f"YouTube playlist {base.CHANNEL_KEY or 'default'}")
    if not url:
        return False
    try:
        _download(url, out_path)
        return True
    except Exception as exc:
        base.log(f"   ⚠️ Replicate image download failed: {exc}")
        return False


def _blocked_search(*args, **kwargs):
    return None


def _approved_healing_photo(theme: str, workdir: str):
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


# Every known legacy image call is replaced before main() runs.
base.gemini_generate_image = _approved_image
base._search_pexels_photo = _blocked_search
base._search_pixabay_photo = _blocked_search
base.fetch_healing_photo = _approved_healing_photo

# The legacy module's Gemini key may still be needed by no active text path because GPT is
# enforced above; blank it to ensure it cannot generate or inspect imagery accidentally.
base.GEMINI_API_KEY = ""

if __name__ == "__main__":
    base.main()
