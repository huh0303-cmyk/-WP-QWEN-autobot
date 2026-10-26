#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refresh playlist thumbnails with collision-resistant, traceable asset names.

Each render gets a topic-derived slug, UTC timestamp, and content hash. Never
overwrite a previous local image or upload every channel as refresh_01.png.
"""
import hashlib
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import youtube_playlist_maker as policy

# Work against the patched legacy engine held by the active policy wrapper so mutable
# globals such as CHANNEL_KEY affect the functions that actually execute.
pm = policy.base

BANK_DIR = "thumbnail_bank"


def unique_asset_stem(channel_key: str, topic: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:48] or "thumbnail"
    digest = hashlib.sha256(f"{channel_key}|{topic}|{stamp}".encode("utf-8")).hexdigest()[:10]
    return f"{channel_key}_{slug}_{stamp}_{digest}"


def refresh_channel(channel_key: str):
    pm.CHANNEL_KEY = channel_key
    pm.log(f"\n{'='*50}\n[{channel_key}] approved thumbnail refresh\n{'='*50}")

    thumb_folder_id = pm._channel_env("THUMBNAIL_FOLDER_ID", pm._DEFAULT_THUMB_FOLDER)
    drive = pm.get_drive_service()
    out_dir = os.path.join(BANK_DIR, channel_key)
    os.makedirs(out_dir, exist_ok=True)

    topic, _ = pm.pick_auto_topic()
    pm.log(f"[{channel_key}] topic: {topic}")
    workdir = os.path.join("/tmp", unique_asset_stem(channel_key, topic))
    os.makedirs(workdir, exist_ok=False)
    try:
        image_paths = pm.build_ai_images(topic, workdir)
    except Exception as exc:
        pm.log(f"   ⚠️ approved image generation failed, skip: {exc}")
        return
    if not image_paths:
        pm.log("   ⚠️ no approved image generated, skip")
        return

    stem = unique_asset_stem(channel_key, topic)
    out_path = os.path.join(out_dir, f"{stem}.png")
    # Never clobber a prior asset if a provider returns an unexpected path.
    if os.path.exists(out_path):
        raise RuntimeError(f"Refusing to overwrite existing thumbnail: {out_path}")
    out_path = pm.make_channel_thumbnail(channel_key, image_paths[0], out_path, topic)
    upload_name = os.path.basename(out_path)
    try:
        pm.upload_to_drive(drive, out_path, thumb_folder_id, upload_name)
        pm.log(f"   ✅ Drive upload complete: {upload_name}")
    except Exception as exc:
        pm.log(f"   ⚠️ Drive upload failed (local copy retained): {exc}")


def main():
    for channel_key in pm.PLAYLIST_CHANNELS:
        try:
            refresh_channel(channel_key)
        except Exception as exc:
            pm.log(f"❌ [{channel_key}] failed; continue: {exc}")


if __name__ == "__main__":
    main()
