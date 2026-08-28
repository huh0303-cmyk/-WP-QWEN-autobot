#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Active YouTube video pipeline with FLUX-only thumbnail/image policy.

The original pipeline is preserved in youtube_video_pipeline_legacy.py. Its 10-scene
editing/TTS/subtitle/Drive flow is retained, but only ONE FLUX source image may be generated
per video. That source is reused for all scenes and the YouTube thumbnail.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import youtube_video_pipeline_legacy as base
from flux_thumbnail_provider import generate_flux_thumbnail_url

_generated_source: str | None = None
_generation_attempted = False


def _flux_image_once(prompt: str, out_path: str) -> bool:
    global _generated_source, _generation_attempted

    if _generated_source and os.path.exists(_generated_source):
        shutil.copyfile(_generated_source, out_path)
        return True
    if _generation_attempted:
        return False
    _generation_attempted = True

    url = generate_flux_thumbnail_url(prompt, theme="YouTube educational video thumbnail")
    if not url:
        return False
    try:
        response = requests.get(url, timeout=90, stream=True)
        response.raise_for_status()
        with open(out_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                if chunk:
                    handle.write(chunk)
        _generated_source = out_path
        return True
    except Exception as exc:
        base.log(f"   ⚠️ FLUX image download failed: {exc}")
        return False


base.GEMINI_IMAGE_MODELS = []
base.gemini_generate_image = _flux_image_once

if __name__ == "__main__":
    base.main()
