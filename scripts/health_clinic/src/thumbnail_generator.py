"""Active Health Clinic thumbnail generator — FLUX-only background policy."""
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

from flux_thumbnail_provider import generate_flux_thumbnail_url
from . import thumbnail_generator_legacy as base


def _flux_background(keyword: str):
    url = generate_flux_thumbnail_url(keyword, theme="Health Clinic YouTube thumbnail")
    if not url:
        print("[Thumbnail] FLUX failed — use local generic background only; no API fallback")
        return None
    try:
        response = requests.get(url, timeout=90)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGB")
    except Exception as exc:
        print(f"[Thumbnail] FLUX background download failed: {exc}")
        return None


base.PEXELS_API_KEY = None
base.PIXABAY_API_KEY = None
base._fetch_background_photo = _flux_background

generate_thumbnail = base.generate_thumbnail
