#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Active archival longform pipeline with FLUX-only YouTube thumbnails.

History/Invention/Silent Era/Retro Reels keep real public-domain archival video footage.
Only thumbnail imagery is generated with black-forest-labs/flux-schnell. Legacy thumbnail
code is preserved in archive_footage_longform_legacy.py.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import archive_footage_longform_legacy as base
from flux_thumbnail_provider import generate_flux_thumbnail_url


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
        "history": "historical documentary",
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
    return base._legacy_build_thumbnail(topic, channel_key, flux_path, workdir)


base._legacy_build_thumbnail = base.build_thumbnail
base.build_thumbnail = _flux_thumbnail

if __name__ == "__main__":
    base.main()
