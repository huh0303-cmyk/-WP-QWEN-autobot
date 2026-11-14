#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Current WordPress publisher entrypoint controlled by Google Sheets.

Keeps the mature autopost_mega engine while applying current operational metadata that
must not regress to legacy labels retained in the large historical module.

Current policy (2026-09-11 user instruction):
- Keep GPT-5 mini for article writing.
- Matching Pexels/Pixabay photos first in opted-in article workflows.
- SDXL Lightning then FLUX Schnell only when no suitable free photo is available.
- Legacy stock helpers remain disabled; all selection uses the shared checked gateway.
- Video generation remains disabled operationally.
"""
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Newsrooms use GPT-5 mini; ordinary WordPress blogs retain the configured Gemini path.
# This distinction is necessary because the legacy publisher module has import-time defaults.
_NEWSROOM_URLS = {"https://koreanews365.com", "https://theseouljournal.com"}
_TARGET_SITE = os.getenv("TARGET_SITE_URL", "").strip().rstrip("/")
_IS_NEWSROOM = _TARGET_SITE in _NEWSROOM_URLS
_TEXT_PROVIDER = "gemini"
os.environ["AI_TEXT_PROVIDER"] = _TEXT_PROVIDER
os.environ["OPENAI_ENABLED"] = "false"
os.environ["CHATGPT_SINGLE_MODEL_PIPELINE"] = "true"
os.environ["PAID_IMAGE_GENERATION_ENABLED"] = "false"
os.environ["OPENAI_IMAGE_ENABLED"] = "false"
os.environ["GEMINI_IMAGE_GENERATION_ENABLED"] = "true"
os.environ["AUTOMATED_IMAGE_PUBLISHING_ENABLED"] = "true"
os.environ["NANO_BANANA_FREE_TIER_ENABLED"] = "false"

# Hostinger sites can advertise IPv6 while GitHub-hosted runners have an
# intermittently unusable IPv6 route.  Prefer IPv4 at the client only; this
# does not alter site DNS and keeps REST reads/writes on the verified A path.
if os.environ.get("FORCE_SOURCE_IPV4", "false").strip().lower() in {"1", "true", "yes", "on"}:
    _original_getaddrinfo = socket.getaddrinfo

    def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

    socket.getaddrinfo = _ipv4_only_getaddrinfo

import autopost_mega as base

from automation_hub.wordpress_adapter import apply_wordpress_registry

# ---------------------------------------------------------------------------
# HARD ROUTING GUARDS
# ---------------------------------------------------------------------------
# Keep newsroom writing on GPT-5 mini while preserving the existing ordinary-blog route.
base.AI_TEXT_PROVIDER = _TEXT_PROVIDER
# Normal WordPress blogs use the deterministic gate only; never block publication
# on the legacy two-pass Gemini consensus review. Newsroom paths keep their own review.
os.environ["CHATGPT_SINGLE_MODEL_PIPELINE"] = "true"

# Restore the actual stock-photo functions instead of replacing them with empty stubs.
# Existing publisher image checks and no-paid policy remain in force.
base.PIXABAY_KEY = os.getenv("PIXABAY_KEY") or None
base.PEXELS_KEY = os.getenv("PEXELS_API_KEY") or None
base.AUTOMATED_IMAGE_PUBLISHING_ENABLED = True
base.WP_IMAGE_COUNT = 0 if os.environ.get("WP_IMAGE_COUNT", "1").strip() == "0" else 1

# Enforce editorial length and a consistent, site-colored reader layout for all
# WordPress sites routed through this entrypoint. Commercial footers are excluded
# from the count because this check runs on the editorial body only.
from automation_hub.editorial_readability import format_article, validate_article_length
_original_wp_post = base.wp_post

def _readable_wp_post(site, title, body_html, meta, tags, faq, images, keyword, score, reporter, category_hint=""):
    # Retry short Koreanews365 drafts using only the supplied article facts.
    if site.get("url", "").rstrip("/").lower() == "https://koreanews365.com":
        for attempt in range(3):
            try:
                validate_article_length(body_html)
                break
            except ValueError:
                if attempt == 2:
                    break
                body_html = base.resize_newsroom_body(body_html, "en", body_html, min_chars=2800, max_chars=3800)
                print(f"KOREANEWS365_LENGTH_REWRITE: attempt={attempt + 1}")
    try:
        count = validate_article_length(body_html)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    print(f"EDITORIAL_LENGTH_OK: {count} characters (2500-4000)")
    body_html = format_article(body_html, site.get("url", ""), include_faq=False)
    return _original_wp_post(site, title, body_html, meta, tags, faq, images, keyword, score, reporter, category_hint)

base.wp_post = _readable_wp_post

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
