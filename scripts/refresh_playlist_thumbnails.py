#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refresh one review thumbnail per playlist channel through the approved image gateway.

Cost policy: one image per channel per manual refresh. The active youtube_playlist_maker
policy module has already replaced legacy Gemini/OpenAI/Pexels/Pixabay image calls with
Replicate's approved 3-model chain.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import youtube_playlist_maker as policy

# Work against the patched legacy engine held by the active policy wrapper so mutable
# globals such as CHANNEL_KEY affect the functions that actually execute.
pm = policy.base

THUMBNAILS_PER_CHANNEL = 1
BANK_DIR = "thumbnail_bank"


def refresh_channel(channel_key: str):
    pm.CHANNEL_KEY = channel_key
    pm.log(f"\n{'='*50}\n[{channel_key}] approved thumbnail refresh\n{'='*50}")

    thumb_folder_id = pm._channel_env("THUMBNAIL_FOLDER_ID", pm._DEFAULT_THUMB_FOLDER)
    drive = pm.get_drive_service()
    out_dir = os.path.join(BANK_DIR, channel_key)
    os.makedirs(out_dir, exist_ok=True)

    topic, _ = pm.pick_auto_topic()
    pm.log(f"[{channel_key}] topic: {topic}")
    workdir = f"/tmp/thumb_refresh_{channel_key}"
    os.makedirs(workdir, exist_ok=True)
    try:
        image_paths = pm.build_ai_images(topic, workdir)
    except Exception as exc:
        pm.log(f"   ⚠️ approved image generation failed, skip: {exc}")
        return
    if not image_paths:
        pm.log("   ⚠️ no approved image generated, skip")
        return

    out_path = os.path.join(out_dir, "01.png")
    out_path = pm.make_channel_thumbnail(channel_key, image_paths[0], out_path, topic)
    try:
        thumb_ext = os.path.splitext(out_path)[1] or ".png"
        pm.upload_to_drive(drive, out_path, thumb_folder_id, f"refresh_01{thumb_ext}")
        pm.log("   ✅ Drive upload complete")
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
