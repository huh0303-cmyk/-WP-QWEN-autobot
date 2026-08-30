#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Active NASA archival longform pipeline with FLUX-only YouTube thumbnails.

Video footage remains real NASA archival footage. Only the thumbnail source image is
replaced with black-forest-labs/flux-schnell. Legacy thumbnail code is preserved in
nasa_archive_longform_legacy.py.
"""
from __future__ import annotations

import os
import random
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import nasa_archive_longform_legacy as base
import classic_reads_longform as narration_engine
from flux_thumbnail_provider import generate_flux_thumbnail_url


def _select_narrator() -> None:
    defaults = ["pNInz6obpgDQGcFmaJgB", "21m00Tcm4TlvDq8ikWAM", "EXAVITQu4vr4xnSDxMaL"]
    pool = [os.getenv(f"KNOWLEDGE_VOICE_{index}_ID", defaults[index - 1]).strip() for index in range(1, 4)]
    narration_engine.VOICE_ID = random.SystemRandom().choice(pool)
    base.log(f"   narrator pool: selected 1 of {len(pool)} approved voices for NASA & Space Times")


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


def _flux_thumbnail(topic: str, hero_frame_path: str, workdir: str):
    url = generate_flux_thumbnail_url(
        topic,
        theme="NASA space history documentary YouTube thumbnail",
    )
    if not url:
        raise RuntimeError("FLUX thumbnail generation failed; no non-FLUX thumbnail fallback allowed")
    flux_path = os.path.join(workdir, "thumbnail_flux_source.webp")
    if not _download_flux(url, flux_path):
        raise RuntimeError("FLUX thumbnail download failed")
    return base._legacy_build_thumbnail(topic, flux_path, workdir)


# Keep original renderer for text/layout, replace only its image source.
base._legacy_build_thumbnail = base.build_thumbnail
base.build_thumbnail = _flux_thumbnail

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
