#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Active archival longform pipeline with FLUX-only YouTube thumbnails.

History/Invention/Silent Era/Retro Reels keep real public-domain archival video footage.
Only thumbnail imagery is generated with black-forest-labs/flux-schnell. Legacy thumbnail
code is preserved in archive_footage_longform_legacy.py.
"""
from __future__ import annotations

import os
import random
import sys
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import archive_footage_longform_legacy as base
import classic_reads_longform as narration_engine
from flux_thumbnail_provider import generate_flux_thumbnail_url


def _select_narrator(channel_key: str) -> None:
    """Choose one of three approved male/female voices once per production."""
    defaults = ["pNInz6obpgDQGcFmaJgB", "21m00Tcm4TlvDq8ikWAM", "EXAVITQu4vr4xnSDxMaL"]
    pool = [os.getenv(f"KNOWLEDGE_VOICE_{index}_ID", defaults[index - 1]).strip() for index in range(1, 4)]
    narrator = random.SystemRandom().choice(pool)
    narration_engine.VOICE_ID = narrator
    base.log(f"   narrator pool: selected 1 of {len(pool)} approved voices for {channel_key}")


def _history_date_overlay(path: str) -> str:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.open(path).convert("RGB")
    draw = ImageDraw.Draw(image)
    font_path = base.ensure_thumbnail_font("en", base.DATA_DIR)
    date_text = datetime.now().strftime("%B %d").upper()
    date_font = ImageFont.truetype(font_path, max(118, image.width // 10))
    label_font = ImageFont.truetype(font_path, max(34, image.width // 32))
    for text, font, y in (
        (date_text, date_font, image.height // 24),
        ("THIS DAY IN HISTORY", label_font, image.height // 4),
    ):
        box = draw.textbbox((0, 0), text, font=font, stroke_width=6)
        x = (image.width - (box[2] - box[0])) // 2
        draw.text((x, y), text, font=font, fill=(255, 220, 40), stroke_width=6, stroke_fill=(0, 0, 0))
    image.save(path, quality=94)
    return path


def _download_flux(url: str, out_path: str) -> bool:
    try:
        response = requests.get(url, timeout=90, stream=True)
        response.raise_for_status()
        with open(out_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                if chunk:
                    handle.write(chunk)
        return True
    except Exception as exc:
        base.log(f"   ⚠️ FLUX thumbnail download failed: {exc}")
        return False


def _flux_thumbnail(topic: str, channel_key: str, hero_frame_path: str, workdir: str):
    channel_theme = {
        "history": "authentic black-and-white war photography, American prosperity era, presidents, streets and archival newspaper collage",
        "invention": "history of inventions documentary",
        "silent_era": "silent cinema history documentary",
        "retro_reels": "vintage twentieth-century culture documentary",
        "american_archive": "American archive history documentary",
    }.get(channel_key, "archival history documentary")
    url = generate_flux_thumbnail_url(topic, theme=f"{channel_theme} YouTube thumbnail")
    if not url:
        raise RuntimeError("FLUX thumbnail generation failed; no non-FLUX thumbnail fallback allowed")
    flux_path = os.path.join(workdir, "thumbnail_flux_source.webp")
    if not _download_flux(url, flux_path):
        raise RuntimeError("FLUX thumbnail download failed")
    result = base._legacy_build_thumbnail(topic, channel_key, flux_path, workdir)
    return _history_date_overlay(result) if channel_key == "history" else result


base._legacy_build_thumbnail = base.build_thumbnail
base.build_thumbnail = _flux_thumbnail

if __name__ == "__main__":
    _select_narrator(sys.argv[4] if len(sys.argv) > 4 else "archive")
    base.main()
