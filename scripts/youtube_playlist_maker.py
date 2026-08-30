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


def _channel_flux_image(topic: str, workdir: str, service=None):
    """Generate exactly one channel-specific FLUX photograph; never use a bank fallback."""
    topic = (topic or "signature channel mood").strip()
    channel = base.CHANNEL_KEY
    if channel == "globalmusic":
        style = random.choice([
            "warm modern candid 35mm photography",
            "timeless black-and-white silver-gelatin photography",
            "soft vintage 1960s romance-film photography",
            "golden-hour cinematic editorial photography",
        ])
        subject = (
            f"A warm affectionate couple sharing a sweet, natural and emotionally intimate moment, "
            f"holding hands, embracing, dancing or smiling closely, inspired by {topic}; {style}; "
            "believable skin and hands, genuine chemistry, tasteful romantic mood, uncluttered frame, "
            "ample clean lower area for a waveform and clean upper-left space for Cafe_Romantic branding"
        )
    elif channel == "healing":
        subject = (
            f"An expansive authentic nature photograph inspired by {topic}: choose a rain-soaked jungle, "
            "dense green forest, clear stream, broad river, open wilderness vista, or peaceful temple "
            "landscape surrounded by nature; visible atmospheric water and weather, no people, deeply calm"
        )
    elif channel == "starbucks":
        season = random.choice(["summer", "winter", "spring or autumn"])
        if season == "summer":
            foreground = "a close-up glass of ice-cold sparkling juice with condensation and crisp ice"
        elif season == "winter":
            foreground = "a close-up cup of warm tea with delicate natural steam"
        else:
            foreground = "a beautiful refreshing cafe drink in a clear glass"
        backdrop = random.choice([
            "a floor-to-ceiling window overlooking a bright open sea and coastline",
            "a panoramic Paris cafe view with the Eiffel Tower in the distance",
            "a spacious coastal cafe overlooking a famous city landmark",
            "a calm sunlit ocean horizon beyond a modern cafe window",
        ])
        subject = (
            f"Premium lifestyle cafe photograph inspired by {topic}, {foreground} as the sharp foreground "
            f"hero, {backdrop}, relaxed instrumental-jazz atmosphere, fresh and spacious composition, "
            "no commercial cafe branding"
        )
    elif channel == "mbb":
        instrument = random.choice(["grand piano", "violin", "cello", "flute", "trumpet"])
        subject = (
            f"Elegant authentic classical-music photograph inspired by {topic}, featuring a {instrument}, "
            "tasteful sheet music and a refined concert-room, reading-room or rain-window setting, "
            "natural morning light or warm evening candlelight appropriate to the theme, no text, "
            "minimal composition with no overlapping typography required"
        )
    elif channel == "kpop":
        subject = (
            f"High-end Korean pop concept photograph inspired by {topic}, stylish young Korean performer "
            "or duo, bold contemporary fashion, vibrant but believable studio or neon lighting, dynamic "
            "editorial pose, realistic skin and anatomy, polished music-magazine photography"
        )
    else:
        subject = f"Authentic editorial music photograph inspired by {topic}"

    path = os.path.join(workdir, "flux_playlist_source.webp")
    if not _flux_image(subject, path):
        raise RuntimeError("FLUX image generation failed; legacy image fallback is forbidden")
    return [path]
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
base.build_ai_images = _channel_flux_image
base.GEMINI_API_KEY = ""

if __name__ == "__main__":
    base.main()
