#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NASA archival longform with a fresh Gemini-generated thumbnail source."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import nasa_archive_longform_legacy as base
import classic_reads_longform as narration_engine
from gemini_media_provider import generate_thumbnail
from knowledge_narrator import select_documentary_narrator


def _select_narrator() -> None:
    narrator = select_documentary_narrator()
    narration_engine.VOICE_ID = narrator["voice_id"]
    base.log(f"   narrator: {narrator['name']} ({narrator['accent']}, {narrator['gender']}) for NASA & Space Times")


def _gemini_thumbnail(topic: str, hero_frame_path: str, workdir: str):
    del hero_frame_path
    source_path = os.path.join(workdir, "thumbnail_gemini_source.bin")
    generate_thumbnail(
        f"Create a completely original photorealistic 16:9 NASA space-history documentary thumbnail source "
        f"about '{topic}'. One iconic focal subject, scientifically and historically plausible detail, dramatic "
        "cinematic depth, clean space for later title typography, no text, no logo, no watermark, no copied image.",
        source_path,
    )
    return base._legacy_build_thumbnail(topic, source_path, workdir)


# Keep original renderer for text/layout, replace only its image source.
base._legacy_build_thumbnail = base.build_thumbnail
base.build_thumbnail = _gemini_thumbnail

# Re-export helpers imported by archive_footage_longform.py.
normalize_clip = base.normalize_clip
build_visual_track = base.build_visual_track
extract_hero_frame = base.extract_hero_frame
W = base.W
H = base.H
CLIP_TRIM_SECONDS = base.CLIP_TRIM_SECONDS

if __name__ == "__main__":
    _select_narrator()
    base.main()
