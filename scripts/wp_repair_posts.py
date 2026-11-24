#!/usr/bin/env python3
"""Rewrite existing WordPress posts from a reviewed manifest and give each a fresh stock photo.

Manifest directory (under data/repairs/): manifest.json + one HTML file per post.
Every post must pass validate_post() first -- the same SEO basics the publishers should meet
(search-result-sized title, meta description length, focus keyword in the title, official sources,
a "checked on" date). The photo is chosen by stock_image_provider, so it goes through the normal
duplicate-photo guard (TARGET_SITE_URL) and is never the photo the post already has.

  python scripts/wp_repair_posts.py --check data/repairs/<dir>      # validate only, no network
  DRY_RUN=false WP_USER=... WP_APP_PASSWORD=... python scripts/wp_repair_posts.py data/repairs/<dir>

DRY_RUN defaults to true and changes nothing (it does not pick or host a photo either).
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def validate_post(post: dict, html: str) -> list[str]:
    problems = []
    title, meta = post.get("title", ""), post.get("meta_description", "")
    if not 20 <= len(title) <= 65:
        problems.append(f"title must be 20-65 characters, is {len(title)}")
    if not 120 <= len(meta) <= 160:
        problems.append(f"meta description must be 120-160 characters, is {len(meta)}")
    keyword = post.get("focus_keyword", "").casefold()
    if not keyword or keyword not in title.casefold():
        problems.append("focus keyword must appear in the title")
    if keyword and keyword not in html.casefold():
        problems.append("focus keyword must appear in the body")
    hosts = {urlparse(u).hostname or "" for u in re.findall(r'href="(https?://[^"]+)"', html)}
    if len({h for h in hosts if h.endswith(".go.kr")}) < 1 or len([u for u in re.findall(r'href="(https?://[^"]*go\.kr[^"]*)"', html)]) < 2:
        problems.append("at least two links to official (go.kr) sources are required")
    if not re.search(r"checked on \d{1,2} \w+ \d{4}", html, re.I):
        problems.append('the body needs a "checked on <date>" line')
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+){1,12}$", post.get("slug", "")):
        problems.append("slug must be 2-13 lowercase words joined by hyphens")
    if not 3 <= len(post.get("tags", [])) <= 8:
        problems.append("3-8 tags are required")
    if "\t" in title or "unlock" in title.casefold():
        problems.append("title contains a tab or a banned word")
    if not isinstance(post.get("id"), int):
        problems.append("post id must be an integer")
    return problems


def load_manifest(directory: Path) -> tuple[dict, list[tuple[dict, str]]]:
    directory = directory.resolve()
    if (ROOT / "data" / "repairs").resolve() not in directory.parents:
        raise SystemExit("manifest directory must be under data/repairs/")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    items = []
    for post in manifest["posts"]:
        html = (directory / post["content_file"]).read_text(encoding="utf-8")
        problems = validate_post(post, html)
        if problems:
            raise SystemExit(f"post {post.get('id')}: " + "; ".join(problems))
        items.append((post, html))
    return manifest, items


def tag_ids(site: str, auth, names: list[str]) -> list[int]:
    ids = []
    for name in names:
        r = requests.post(f"{site}/wp-json/wp/v2/tags", auth=auth, json={"name": name}, timeout=20)
        if r.status_code in (200, 201):
            ids.append(r.json()["id"])
        elif r.status_code == 400 and isinstance(r.json().get("data"), dict) and r.json()["data"].get("term_id"):
            ids.append(int(r.json()["data"]["term_id"]))
        else:
            r.raise_for_status()
    return ids


def pick_photo(subject: str) -> str | None:
    from stock_image_provider import find_stock_image
    for provider in random.sample(("pexels", "pixabay"), 2):
        url = find_stock_image(subject, force=True, selected_provider=provider)
        if url:
            return url
    return None


def upload_photo(site: str, auth, image_url: str, alt: str) -> int:
    image = requests.get(image_url, timeout=30)
    image.raise_for_status()
    mime = image.headers.get("Content-Type", "image/jpeg").split(";")[0]
    ext = ".png" if "png" in mime else ".webp" if "webp" in mime else ".jpg"
    filename = "news-" + hashlib.md5(image_url.encode()).hexdigest()[:12] + ext
    r = requests.post(f"{site}/wp-json/wp/v2/media", auth=auth, data=image.content, timeout=60,
                      headers={"Content-Disposition": f'attachment; filename="{filename}"', "Content-Type": mime})
    r.raise_for_status()
    media_id = r.json()["id"]
    requests.post(f"{site}/wp-json/wp/v2/media/{media_id}", auth=auth,
                  json={"alt_text": alt, "title": alt}, timeout=30).raise_for_status()
    return media_id


def main(argv: list[str]) -> int:
    check_only = "--check" in argv
    args = [a for a in argv if not a.startswith("--")]
    manifest, items = load_manifest(Path(args[0]))
    print(f"manifest valid: {len(items)} post(s)")
    if check_only:
        return 0
    site = manifest["site_url"].rstrip("/")
    os.environ["TARGET_SITE_URL"] = site  # enables the duplicate-photo guard
    apply_changes = os.getenv("DRY_RUN", "true").strip().lower() == "false"
    auth = (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])
    failures = 0
    for post, html in items:
        endpoint = f"{site}/wp-json/wp/v2/posts/{post['id']}"
        before = requests.get(endpoint, params={"context": "edit"}, auth=auth, timeout=30)
        before.raise_for_status()
        old = before.json()
        print(f"[{post['id']}] {old['title']['raw'][:70]!r} -> {post['title']!r}")
        if not apply_changes:
            print("   dry run: nothing changed")
            continue
        payload = {"title": post["title"], "slug": post["slug"], "content": html,
                   "excerpt": post["meta_description"], "tags": tag_ids(site, auth, post["tags"]),
                   "meta": {"rank_math_focus_keyword": post["focus_keyword"],
                            "rank_math_description": post["meta_description"]}}
        photo = pick_photo(post["image_subject"])
        if photo:
            payload["featured_media"] = upload_photo(site, auth, photo, post["image_alt"])
        else:
            print("   WARNING: no new non-duplicate photo found; the current featured image is kept")
        done = requests.post(endpoint, auth=auth, json=payload, timeout=60)
        done.raise_for_status()
        new = done.json()
        page = requests.get(new["link"], timeout=30)
        og = re.search(r'property="og:image" content="([^"]+)"', page.text)
        redirect = requests.get(old["link"], timeout=30, allow_redirects=True) if old["link"] != new["link"] else None
        ok = (page.status_code == 200 and new["slug"] == post["slug"] and new["status"] == "publish"
              and (redirect is None or redirect.url.rstrip("/") == new["link"].rstrip("/")))
        print(f"   {'OK' if ok else 'CHECK FAILED'}: {new['link']} status={new['status']} "
              f"page={page.status_code} og_image={og.group(1).rsplit('/', 1)[-1] if og else None} "
              f"old_url_redirects={'n/a' if redirect is None else redirect.url == new['link']}")
        failures += 0 if ok else 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
