#!/usr/bin/env python3
"""Repair the live K-Trip article language shell and complete SEO description."""
from __future__ import annotations

import json
import os
import re

import requests

SITE = "https://k-trip365.com"
SLUG = "busan-weekend-smart-savings-big-memories"
WP_USER = "huh0303@gmail.com"
DESCRIPTION = (
    "Plan an affordable Busan weekend with practical tips for budget stays, "
    "local food, public transport, and smart savings."
)
EXCERPT = (
    "Plan a memorable Busan weekend on a sensible budget with practical advice "
    "for accommodation, markets, local food, and public transport."
)


def main() -> int:
    password = os.environ.get("WP_APP_PASSWORD", "").strip()
    if not password:
        raise SystemExit("WP_APP_PASSWORD is required")
    auth = (WP_USER, password)

    settings = requests.post(
        f"{SITE}/wp-json/wp/v2/settings",
        auth=auth,
        json={"language": "en_US", "WPLANG": "en_US"},
        timeout=30,
    )
    if settings.status_code not in {200, 201}:
        raise RuntimeError(f"site language update failed: HTTP {settings.status_code}: {settings.text[:300]}")

    lookup = requests.get(
        f"{SITE}/wp-json/wp/v2/posts",
        auth=auth,
        params={"slug": SLUG, "context": "edit", "_fields": "id,slug,status,title,meta"},
        timeout=30,
    )
    lookup.raise_for_status()
    posts = lookup.json()
    if len(posts) != 1:
        raise RuntimeError(f"expected one K-Trip post for {SLUG}, found {len(posts)}")

    post_id = posts[0]["id"]
    updated = requests.post(
        f"{SITE}/wp-json/wp/v2/posts/{post_id}",
        auth=auth,
        json={
            "excerpt": EXCERPT,
            "meta": {"rank_math_description": DESCRIPTION},
        },
        timeout=30,
    )
    if updated.status_code not in {200, 201}:
        raise RuntimeError(f"post SEO update failed: HTTP {updated.status_code}: {updated.text[:300]}")

    public = requests.get(f"{SITE}/{SLUG}/", timeout=30)
    public.raise_for_status()
    match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)', public.text, re.I)
    live_description = match.group(1) if match else ""
    if live_description != DESCRIPTION:
        raise RuntimeError(f"live meta description mismatch: {live_description!r}")
    if not 100 <= len(live_description) <= 119:
        raise RuntimeError(f"live meta description length is {len(live_description)}, expected 100-119")

    payload = {
        "ok": True,
        "site": SITE,
        "post_id": post_id,
        "slug": SLUG,
        "site_language": "en_US",
        "search_description": live_description,
        "search_description_length": len(live_description),
        "public_url": f"{SITE}/{SLUG}/",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
