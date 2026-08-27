#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Active YouTube video pipeline with Replicate-only image policy.

The original pipeline is preserved in youtube_video_pipeline_legacy.py. Its 10-scene
editing/TTS/subtitle/Drive flow is retained, but only ONE source image may be generated
per video. That image is reused for all scene files. Legacy Gemini/OpenAI image APIs are
never called through this entrypoint.
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
from replicate_image_provider import generate_image_url

_generated_source: str | None = None
_generation_attempted = False


def _approved_image_once(prompt: str, out_path: str) -> bool:
    global _generated_source, _generation_attempted

    if _generated_source and os.path.exists(_generated_source):
        shutil.copyfile(_generated_source, out_path)
        return True

    # Critical cost guard: only the first scene is allowed to start the approved
    # three-model chain. If that chain fails, the remaining nine scenes use the
    # legacy local placeholder rather than starting new paid predictions.
    if _generation_attempted:
        return False
    _generation_attempted = True

    url = generate_image_url(prompt, theme="YouTube educational video")
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
        base.log(f"   ⚠️ approved image download failed: {exc}")
        return False


# Disable legacy image model metadata and replace its only image generation function.
base.GEMINI_IMAGE_MODELS = []
base.gemini_generate_image = _approved_image_once

# Preserve the mature pipeline and CLI.
if __name__ == "__main__":
    base.main()
