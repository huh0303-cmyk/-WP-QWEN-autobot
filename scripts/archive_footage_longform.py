#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Archival longform with fresh Gemini-generated thumbnail source imagery."""
from __future__ import annotations

import os
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import archive_footage_longform_legacy as base
import classic_reads_longform as narration_engine
from gemini_media_provider import generate_thumbnail
from knowledge_narrator import select_documentary_narrator


KNOWLEDGE_IMAGE_FILENAMES = {
    "history": "history-source.png",
    "invention": "invention-source.png",
    "silent_era": "silent-era-source.png",
    "retro_reels": "retro-reels-source.png",
}


def _reviewed_image(channel_key: str, workdir: str) -> str:
    episode_date = os.environ.get("EPISODE_DATE", "").strip()
    if not episode_date:
        raise RuntimeError("WAITING_ASSETS: EPISODE_DATE is required for a unique knowledge image")
    filename = KNOWLEDGE_IMAGE_FILENAMES.get(channel_key)
    if not filename:
        raise RuntimeError(f"WAITING_ASSETS: no reviewed knowledge image mapping for {channel_key}")
    root = Path(os.environ.get(
        "KNOWLEDGE_OWNER_IMAGE_ROOT",
        str(Path(__file__).resolve().parents[1] / "assets" / "youtube" / "knowledge" / episode_date),
    )).resolve()
    source = (root / filename).resolve()
    if source.parent != root or not source.is_file():
        raise RuntimeError(f"WAITING_ASSETS: reviewed knowledge image is missing: {filename}")
    target = Path(workdir) / filename
    shutil.copyfile(source, target)
    return str(target)


def _select_narrator(channel_key: str) -> None:
    """Choose one of three approved male/female voices once per production."""
    narrator = select_documentary_narrator(channel_key)
    narration_engine.VOICE_ID = narrator["voice_id"]
    base.log(f"   narrator: {narrator['name']} ({narrator['accent']}, {narrator['gender']}) for {channel_key}")


def _history_date_overlay(path: str, workdir: str) -> str:
    import json
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    records = json.loads((Path(workdir) / "scene_manifest.json").read_text(encoding="utf-8"))
    label = records[0]["clip"].get("event_label", "")
    year = label.rsplit("·", 1)[-1].strip()
    if not year.isdigit():
        raise RuntimeError("Missing verified historical event year")
    episode_date = date.fromisoformat(os.environ["EPISODE_DATE"]) if os.environ.get("EPISODE_DATE") else datetime.now(timezone(timedelta(hours=9))).date()
    image = Image.new("RGB", (1280, 720), "#f2ead8")
    draw = ImageDraw.Draw(image)
    def centered(text, y, size, bold=False):
        names = ["DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"] if bold else ["DejaVuSerif.ttf", "LiberationSerif-Regular.ttf"]
        for name in names + [base.ensure_thumbnail_font("en", base.DATA_DIR)]:
            try:
                font = ImageFont.truetype(name, size)
                break
            except OSError:
                continue
        draw.text((640, y), text, font=font, fill="#211e19", anchor="mt")
    centered("TODAY IN HISTORY", 20, 58, True)
    draw.line((45, 95, 1235, 95), fill="#211e19", width=3)
    with Image.open(path) as source:
        photo = ImageOps.fit(source.convert("RGB"), (1190, 410))
        image.paste(photo, (45, 108))
    draw.line((45, 530, 1235, 530), fill="#211e19", width=2)
    centered(episode_date.strftime("%B %d").upper(), 540, 78, True)
    centered(year, 635, 55)
    target = str(Path(workdir) / "history_newspaper_thumbnail.jpg")
    image.save(target, quality=94)
    return target


def _gemini_thumbnail(topic: str, channel_key: str, hero_frame_path: str, workdir: str):
    channel_theme = {
        "history": "world history, source-grounded international events, one clear editorial subject, minimal text",
        "invention": "history of inventions documentary",
        "silent_era": "Old Hollywood silent and black-and-white cinema documentary",
        "retro_reels": "Retro USA everyday American homes and social life from the 1960s through 2000s",
        "american_archive": "American archive history documentary",
    }.get(channel_key, "archival history documentary")
    del channel_theme

    source_path = None
    if hero_frame_path and Path(hero_frame_path).is_file():
        source_path = hero_frame_path
    else:
        try:
            source_path = _reviewed_image(channel_key, workdir)
        except Exception as exc:
            base.log(f"   [thumbnail] Pre-reviewed image unavailable ({exc}), generating via Gemini...")
            gemini_out = os.path.join(workdir, "thumbnail_gemini_source.jpg")
            prompt = (
                f"Create a completely original photorealistic 16:9 documentary thumbnail source image about '{topic}'. "
                f"Editorial direction: {channel_theme}. One unmistakable focal subject, strong depth, historically "
                "plausible details, clean space for later title typography, no text, no logo, no watermark, no copied image."
            )
            try:
                generate_thumbnail(prompt, gemini_out)
                source_path = gemini_out
            except Exception as gerr:
                base.log(f"   [thumbnail] Gemini generation failed ({gerr}), falling back to emergency background...")
                source_path = os.path.join(workdir, "thumbnail_fallback.jpg")
                from PIL import Image
                Image.new("RGB", (1280, 720), (30, 30, 36)).save(source_path, quality=90)

    if channel_key == "history":
        return _history_date_overlay(source_path, workdir)
    return base._legacy_build_thumbnail(topic, channel_key, source_path, workdir)


base._legacy_build_thumbnail = base.build_thumbnail
base.build_thumbnail = _gemini_thumbnail

if __name__ == "__main__":
    _select_narrator(sys.argv[4] if len(sys.argv) > 4 else "archive")
    base.main()
