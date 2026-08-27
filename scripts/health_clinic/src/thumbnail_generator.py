"""Active Health Clinic thumbnail generator — Replicate-only background policy.

Legacy Pexels/Pixabay background code is preserved in thumbnail_generator_legacy.py but
cannot execute through this active module. One approved Replicate image is generated at
most once for each thumbnail; existing Pillow text/layout styling is reused.
"""
from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

HERE = Path(__file__).resolve()
SCRIPTS_DIR = HERE.parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from replicate_image_provider import generate_image_url
from . import thumbnail_generator_legacy as base


def _approved_background(keyword: str):
    url = generate_image_url(keyword, theme="Health Clinic YouTube thumbnail")
    if not url:
        print("[Thumbnail] approved Replicate chain failed — use local generic background; no legacy fallback")
        return None
    try:
        response = requests.get(url, timeout=90)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGB")
    except Exception as exc:
        print(f"[Thumbnail] approved background download failed: {exc}")
        return None


base.PEXELS_API_KEY = None
base.PIXABAY_API_KEY = None
base._fetch_background_photo = _approved_background

generate_thumbnail = base.generate_thumbnail
