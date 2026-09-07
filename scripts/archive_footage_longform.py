#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Archival longform with fresh Gemini-generated thumbnail source imagery."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import archive_footage_longform_legacy as base
import classic_reads_longform as narration_engine
from gemini_media_provider import generate_thumbnail
from knowledge_narrator import select_documentary_narrator


def _select_narrator(channel_key: str) -> None:
    """Choose one of three approved male/female voices once per production."""
    narrator = select_documentary_narrator()
    narration_engine.VOICE_ID = narrator["voice_id"]
    base.log(f"   narrator: {narrator['name']} ({narrator['accent']}, {narrator['gender']}) for {channel_key}")


def _history_date_overlay(path: str) -> str:
    from PIL import Image, ImageDraw, ImageFont

    image = Image.open(path).convert("RGB")
    draw = ImageDraw.Draw(image)
    font_path = base.ensure_thumbnail_font("en", base.DATA_DIR)
    date_text = datetime.now(timezone(timedelta(hours=9))).strftime("%B %d").upper()
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


def _gemini_thumbnail(topic: str, channel_key: str, hero_frame_path: str, workdir: str):
    del hero_frame_path
    channel_theme = {
        "history": "world history, source-grounded international events, one clear editorial subject, minimal text",
        "invention": "history of inventions documentary",
        "silent_era": "Old Hollywood silent and black-and-white cinema documentary",
        "retro_reels": "Retro USA everyday American homes and social life from the 1960s through 2000s",
        "american_archive": "American archive history documentary",
    }.get(channel_key, "archival history documentary")
    source_path = os.path.join(workdir, "thumbnail_gemini_source.bin")
    prompt = (f"Create a completely original photorealistic 16:9 documentary thumbnail source image about '{topic}'. "
              f"Editorial direction: {channel_theme}. One unmistakable focal subject, strong depth, historically "
              "plausible details, clean space for later title typography, no text, no logo, no watermark, no copied image.")
    generate_thumbnail(prompt, source_path)
    result = base._legacy_build_thumbnail(topic, channel_key, source_path, workdir)
    return _history_date_overlay(result) if channel_key == "history" else result


base._legacy_build_thumbnail = base.build_thumbnail
base.build_thumbnail = _gemini_thumbnail

if __name__ == "__main__":
    _select_narrator(sys.argv[4] if len(sys.argv) > 4 else "archive")
    base.main()
