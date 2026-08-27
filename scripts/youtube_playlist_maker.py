#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Active YouTube playlist entrypoint — FLUX-only thumbnail/image policy.

All YouTube playlist source imagery and thumbnails use black-forest-labs/flux-schnell.
No SDXL, Gemini image, OpenAI image, Pexels, or Pixabay fallback is allowed.
"""
from __future__ import annotations

import os
import random
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

os.environ["AI_TEXT_PROVIDER"] = "openai"
os.environ["OPENAI_ENABLED"] = "true"
os.environ["OPENAI_IMAGE_ENABLED"] = "false"
os.environ["PAID_IMAGE_GENERATION_ENABLED"] = "false"

import youtube_playlist_maker_legacy as base
from flux_thumbnail_provider import generate_flux_thumbnail_url

base.GEMINI_IMAGE_MODELS = []
base.PEXELS_API_KEY = ""
base.PIXABAY_KEY = ""

# Compatibility exports used by tests and utility callers. These are Drive/local helpers,
# not external image providers.
list_folder_files = base.list_folder_files
download_drive_file = base.download_drive_file
IMAGE_EXTS = base.IMAGE_EXTS
THUMBNAIL_FOLDER_ID = base.THUMBNAIL_FOLDER_ID
log = base.log
PLAYLIST_CHANNELS = base.PLAYLIST_CHANNELS
CHANNEL_KEY = base.CHANNEL_KEY


def _download(url: str, out_path: str) -> None:
    response = requests.get(url, timeout=90, stream=True)
    response.raise_for_status()
    with open(out_path, "wb") as handle:
        for chunk in response.iter_content(chunk_size=1 << 20):
            if chunk:
                handle.write(chunk)


def _flux_image(prompt: str, out_path: str) -> bool:
    url = generate_flux_thumbnail_url(prompt, theme=f"YouTube playlist {base.CHANNEL_KEY or 'default'}")
    if not url:
        return False
    try:
        _download(url, out_path)
        return True
    except Exception as exc:
        base.log(f"   ⚠️ FLUX image download failed: {exc}")
        return False


def _blocked_search(*args, **kwargs):
    return None


def _flux_healing_photo(theme: str, workdir: str):
    subject = base.HEALING_THEME_TOPICS.get(theme, theme)
    url = generate_flux_thumbnail_url(subject, theme="YouTube healing nature ambience")
    if not url:
        return None
    path = os.path.join(workdir, "healing_photo_flux.webp")
    try:
        _download(url, path)
        return path
    except Exception as exc:
        base.log(f"   ⚠️ FLUX healing image download failed: {exc}")
        return None


def select_single_bank_image(workdir, service):
    """Compatibility utility: select exactly one existing Drive image, no API generation."""
    bank_images = list_folder_files(service, THUMBNAIL_FOLDER_ID, IMAGE_EXTS, "image/")
    if not bank_images:
        raise RuntimeError("채널 썸네일창고에 사용할 기존 이미지가 없습니다")
    picked = random.choice(bank_images)
    extension = os.path.splitext(picked["name"])[1] or ".jpg"
    path = os.path.join(workdir, f"playlist_background{extension}")
    download_drive_file(service, picked["id"], path)
    return path


base.gemini_generate_image = _flux_image
base._search_pexels_photo = _blocked_search
base._search_pixabay_photo = _blocked_search
base.fetch_healing_photo = _flux_healing_photo
base.GEMINI_API_KEY = ""

if __name__ == "__main__":
    base.main()
