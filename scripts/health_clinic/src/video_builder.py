"""Active Health Clinic video builder with repository-wide image cost policy.

The previous Gemini + Pexels/Pixabay implementation is preserved in
video_builder_legacy.py. This active module allows one generated source image per video,
using only the approved Replicate three-model gateway. The mature ffmpeg/TTS/subtitle
assembly logic remains unchanged through the legacy implementation.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve()
SCRIPTS_DIR = HERE.parents[2]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from replicate_image_provider import generate_image_url
from . import video_builder_legacy as base


def _download(url: str, out_path: str) -> bool:
    try:
        response = requests.get(url, timeout=90, stream=True)
        response.raise_for_status()
        with open(out_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                if chunk:
                    handle.write(chunk)
        return True
    except Exception as exc:
        print(f"[Video] approved image download failed: {exc}")
        return False


def _approved_generate(prompt: str, out_path: str, max_retries: int = 0) -> bool:
    """Compatibility replacement: one approved Replicate request chain, no legacy retries."""
    url = generate_image_url(prompt, theme="Health Clinic educational video")
    return bool(url and _download(url, out_path))


def _blocked_stock(*args, **kwargs) -> bool:
    return False


def _approved_fetch_images(keywords: list, out_dir: str, title: str = "", ai_count: int = 0, lang: str = "") -> list:
    """Generate exactly one source image for the whole video and reuse it in motion clips."""
    keyword = next((str(k).strip() for k in keywords if str(k).strip()), "senior healthy lifestyle")
    ethnicity = {"kr": "Korean", "jp": "Japanese", "en": ""}.get(lang, "")
    people_clause = f" People shown should look {ethnicity}." if ethnicity else ""
    prompt = (
        f"Photorealistic editorial health education scene for '{title or keyword}'. "
        f"Scene focus: {keyword}.{people_clause} Warm natural lighting, credible senior-friendly setting, "
        "no visible text, no logo, no watermark, 16:9."
    )
    safe = re.sub(r"[^a-z0-9]+", "_", keyword.lower()).strip("_")[:60] or "health"
    path = os.path.join(out_dir, f"00_{safe}.webp")
    if not _approved_generate(prompt, path):
        raise RuntimeError("Approved Replicate image chain failed; legacy image fallback is forbidden")
    print("[Video] cost guard: 1 approved image generated and reused for the full video")
    return [path]


# Block every legacy still-image route before its build_video executes.
base.PEXELS_API_KEY = None
base.PIXABAY_API_KEY = None
base.GEMINI_API_KEY = None
base.AI_IMAGE_COUNT = 1
base.INTRO_CLIP_COUNT = 1
base._fetch_from_pexels = _blocked_stock
base._fetch_from_pixabay = _blocked_stock
base._generate_ai_image = _approved_generate
base._fetch_images = _approved_fetch_images

# Public API expected by pipeline.py.
build_video = base.build_video
