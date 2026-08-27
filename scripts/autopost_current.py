#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Current WordPress publisher entrypoint controlled by Google Sheets.

Keeps the mature autopost_mega engine while applying current operational metadata that
must not regress to legacy labels retained in the large historical module.

2026-08-27 hard policy:
- WordPress text generation is OpenAI/GPT only. Never fall back to Gemini for WP text.
- Image generation is Replicate only, through scripts/replicate_image_provider.py.
- Pixabay, Pexels, OpenAI image, Gemini image/Nano Banana, local infographic fallbacks,
  and OpenAI/Gemini image-relevance calls are blocked from the active WP entrypoint.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Set provider policy before importing the legacy engine so import-time defaults cannot
# silently route WordPress back to Gemini or enable legacy paid image generation.
os.environ["AI_TEXT_PROVIDER"] = "openai"
os.environ["OPENAI_ENABLED"] = "true"
os.environ["PAID_IMAGE_GENERATION_ENABLED"] = "false"
os.environ["OPENAI_IMAGE_ENABLED"] = "false"
os.environ["GEMINI_IMAGE_GENERATION_ENABLED"] = "false"
os.environ["AUTOMATED_IMAGE_PUBLISHING_ENABLED"] = "true"

import autopost_mega as base

from automation_hub.wordpress_adapter import apply_wordpress_registry
from replicate_image_provider import generate_image_urls

# ---------------------------------------------------------------------------
# HARD ROUTING GUARDS
# ---------------------------------------------------------------------------
# WordPress text: GPT/OpenAI only. Clear the Gemini client after import so even stale
# fallback branches cannot spend Gemini quota or write WP copy.
base.AI_TEXT_PROVIDER = "openai"
if hasattr(base, "gemini_client"):
    base.gemini_client = None

# Images: only the approved Replicate gateway may return an image URL. The legacy module
# still contains old provider functions for historical compatibility, but every active
# WP entry through this file replaces those call sites before base.main() starts.
base.PIXABAY_KEY = None
base.PEXELS_KEY = None
base.GEMINI_IMAGE_MODELS = []
base.AUTOMATED_IMAGE_PUBLISHING_ENABLED = True


def _blocked_stock(*args, **kwargs):
    return []


def _replicate_images(keyword, count=1, theme=""):
    return generate_image_urls(keyword, count=1, theme=theme)


def _pass_generated_images(urls, *args, **kwargs):
    # Images are generated from the article subject itself. Do not spend OpenAI/Gemini
    # vision calls to re-score them; this also closes another legacy image-related cost path.
    return list(urls or [])[:1]


base.get_images_pixabay = _blocked_stock
base.get_images_pexels = _blocked_stock
base.get_multiple_images = _replicate_images
base.filter_relevant_images = _pass_generated_images
base.gemini_generate_image = lambda *args, **kwargs: False
base.get_fallback_nanobanana_image = _blocked_stock
base.get_fallback_infographic_image = _blocked_stock

# kskin365.com was restored to the active 25-blog network. The legacy module still carried
# a stale 'Retired Site' author label, which must never reach newly published content.
kskin_author = {
    "name": "Korean Skincare Editorial Desk",
    "email": "editor@kskin365.com",
    "slug": "kskin365-com-desk",
    "bio": (
        "Korean Skincare Editorial Desk. Source-checked ingredient, routine and skin-safety "
        "guidance within this site's editorial scope."
    ),
}
base.AUTHOR_BY_SITE_DEF["kskin365.com"] = kskin_author
base.AUTHOR_BY_SITE["kskin365.com"] = kskin_author


def load_dashboard_settings() -> None:
    source = os.getenv("AUTOMATION_HUB_SOURCE", "github").strip().lower()
    if source == "github":
        from automation_hub.registry import SiteRegistry

        registry = SiteRegistry.load()
    elif source == "sheets":
        from load_automation_hub_from_sheets import load_runtime_registry

        registry = load_runtime_registry()
    else:
        raise RuntimeError(f"unsupported AUTOMATION_HUB_SOURCE: {source}")

    sites, personas = apply_wordpress_registry(base.SITES_CONFIG, base.SITE_PERSONA, registry)
    base.SITES_CONFIG = sites
    base.SITE_PERSONA = personas
    print(f"🎛️ Automation Hub 설정 적용: WordPress {len(sites)}개 / source={source}")


if __name__ == "__main__":
    load_dashboard_settings()
    base.main()
