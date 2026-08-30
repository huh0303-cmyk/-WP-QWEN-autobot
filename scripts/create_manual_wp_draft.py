#!/usr/bin/env python3
"""Create one WordPress draft from a manually-written Gemini Gem article.

Bridges the manual Gem workflow (Gem writes title/HTML/image in a Gemini
chat, human pastes it here) into the existing draft-review pipeline: this
script only creates the WordPress draft; `publishing_completion_notify.py`
(already built, unchanged) then emails + Kakao-notifies a real wp-admin
edit link with native Publish/Schedule buttons. Never publishes directly —
status is always "draft".
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.site_registry import SITES

WP_USER = "huh0303@gmail.com"
RESULT_FILE = "newsroom_publish_result.json"


def _wp_pass_env_for(site_url: str) -> str:
    normalized = site_url.rstrip("/").lower()
    for url, secret_name, _tier in SITES:
        if url.rstrip("/").lower() == normalized:
            return secret_name
    return ""


def ensure_featured_media(site_url: str, wp_pass: str, image_url: str, title: str) -> int:
    """Mirrors scripts/autopost_mega.py's ensure_featured_media."""
    if not image_url:
        return 0
    try:
        image = requests.get(image_url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
        image.raise_for_status()
        mime = image.headers.get("Content-Type", "image/jpeg").split(";", 1)[0]
        extension = ".png" if "png" in mime else ".webp" if "webp" in mime else ".jpg"
        filename = "gem-" + hashlib.md5(image_url.encode()).hexdigest()[:12] + extension
        uploaded = requests.post(
            f"{site_url}/wp-json/wp/v2/media", auth=(WP_USER, wp_pass),
            headers={"Content-Disposition": f'attachment; filename="{filename}"', "Content-Type": mime},
            data=image.content, timeout=35,
        )
        uploaded.raise_for_status()
        media_id = uploaded.json().get("id", 0)
    except Exception as exc:
        print(f"featured image upload skipped: {exc}")
        return 0
    if media_id:
        try:
            requests.post(
                f"{site_url}/wp-json/wp/v2/media/{media_id}", auth=(WP_USER, wp_pass),
                json={"alt_text": title}, timeout=15,
            )
        except Exception:
            pass
    return media_id


def resolve_category_id(site_url: str, wp_pass: str, category_name: str) -> int:
    if not category_name:
        return 0
    try:
        response = requests.get(
            f"{site_url}/wp-json/wp/v2/categories", auth=(WP_USER, wp_pass),
            params={"search": category_name, "per_page": 1}, timeout=15,
        )
        if response.status_code == 200 and response.json():
            return response.json()[0]["id"]
    except Exception:
        pass
    return 0


def resolve_tag_ids(site_url: str, wp_pass: str, tags: list[str]) -> list[int]:
    tag_ids = []
    for tag in tags:
        tag = tag.strip()
        if not tag:
            continue
        try:
            created = requests.post(
                f"{site_url}/wp-json/wp/v2/tags", auth=(WP_USER, wp_pass),
                json={"name": tag}, timeout=15,
            )
            if created.status_code in (200, 201):
                tag_ids.append(created.json()["id"])
            elif created.status_code == 400:
                found = requests.get(
                    f"{site_url}/wp-json/wp/v2/tags", auth=(WP_USER, wp_pass),
                    params={"search": tag, "per_page": 1}, timeout=15,
                )
                if found.status_code == 200 and found.json():
                    tag_ids.append(found.json()[0]["id"])
        except Exception:
            continue
    return tag_ids


def main() -> int:
    site_url = os.environ.get("SITE_URL", "").rstrip("/")
    title = os.environ.get("DRAFT_TITLE", "").strip()
    content_html = os.environ.get("DRAFT_CONTENT_HTML", "")
    image_url = os.environ.get("DRAFT_IMAGE_URL", "").strip()
    meta_description = os.environ.get("DRAFT_META_DESCRIPTION", "").strip()
    category_name = os.environ.get("DRAFT_CATEGORY", "").strip()
    tags = [t for t in os.environ.get("DRAFT_TAGS", "").split(",") if t.strip()]

    if not all((site_url, title, content_html)):
        raise SystemExit("SITE_URL, DRAFT_TITLE and DRAFT_CONTENT_HTML are required")
    wp_pass_env = _wp_pass_env_for(site_url)
    if not wp_pass_env:
        raise SystemExit(f"{site_url} is not in scripts/site_registry.py SITES — add it there first")
    wp_pass = os.environ.get(wp_pass_env, "")
    if not wp_pass:
        raise SystemExit(f"No WordPress application password found in env var {wp_pass_env}")

    data = {
        "title": title,
        "content": content_html,
        "status": "draft",  # hard-locked: this script never publishes
        "comment_status": "closed",
        "ping_status": "closed",
    }
    category_id = resolve_category_id(site_url, wp_pass, category_name)
    if category_id:
        data["categories"] = [category_id]
    tag_ids = resolve_tag_ids(site_url, wp_pass, tags)
    if tag_ids:
        data["tags"] = tag_ids
    if meta_description:
        data["meta"] = {"rank_math_description": meta_description}

    featured_media_id = ensure_featured_media(site_url, wp_pass, image_url, title)
    if featured_media_id:
        data["featured_media"] = featured_media_id

    response = requests.post(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, wp_pass), json=data, timeout=30)
    if response.status_code not in (200, 201):
        raise SystemExit(f"WordPress draft creation failed: HTTP {response.status_code}: {response.text[:400]}")
    payload = response.json()
    post_id = payload.get("id")
    post_url = payload.get("link", "")
    wp_status = payload.get("status", "")
    if wp_status != "draft":
        raise SystemExit(f"WordPress returned unexpected status {wp_status!r}; expected 'draft' (post_id={post_id})")

    record = {"status": "draft", "url": post_url, "title": title, "post_id": post_id}
    existing = {"records": []}
    if Path(RESULT_FILE).exists():
        try:
            existing = json.loads(Path(RESULT_FILE).read_text(encoding="utf-8"))
        except Exception:
            existing = {"records": []}
    existing.setdefault("records", []).append(record)
    Path(RESULT_FILE).write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"ok": True, "post_id": post_id, "url": post_url, "status": "draft"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
