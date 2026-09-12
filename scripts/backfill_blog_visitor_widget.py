#!/usr/bin/env python3
"""Backfill the daily+total visitor-counter widget onto EXISTING live posts
across the Blogger network. Idempotent (skips posts that already carry the
widget's MARK) and additive-only (appends to content, never replaces it, so
the original article body is preserved). Counting only starts from the
moment the widget goes live on a post — no historical/backfilled numbers are
displayed or claimed.

koreamedicaltour1.blogspot.com is a documented duplicate test blog
(HIDDEN_BLOGGER_URLS in control_center/app.py; production destination is
koreamedicaltour365.blogspot.com) and is excluded on purpose, not by
oversight.

Usage:
  python backfill_blog_visitor_widget.py --only kstudy365     # pilot: one blog
  python backfill_blog_visitor_widget.py --only kstudy365 --max-posts 1   # pilot: one post
  python backfill_blog_visitor_widget.py                       # full run, all eligible blogs
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

import requests
import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from automation_hub.blog_visitor_widget import visitor_counter_html, MARK

OUT = ROOT / "artifacts/blog-visitor-widget-backfill.json"
EXCLUDED = {
    "koreamedicaltour1": "documented duplicate test blog (HIDDEN_BLOGGER_URLS) — production blog is 'medicaltour' (koreamedicaltour365.blogspot.com)",
}


def access_token():
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
            "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def all_live_posts(endpoint, headers, max_posts=None):
    page_token = None
    seen = 0
    while True:
        params = {"status": "live", "view": "ADMIN", "fetchBodies": "true", "maxResults": 500}
        if page_token:
            params["pageToken"] = page_token
        for attempt in range(4):
            response = requests.get(endpoint, headers=headers, params=params, timeout=30)
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2 ** attempt * 3)
                continue
            response.raise_for_status()
            break
        payload = response.json()
        for item in payload.get("items", []):
            yield item
            seen += 1
            if max_posts and seen >= max_posts:
                return
        page_token = payload.get("nextPageToken")
        if not page_token:
            break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="", help="single site_key for a pilot run")
    parser.add_argument("--max-posts", type=int, default=0, help="cap posts per blog (0 = no cap)")
    args = parser.parse_args()

    profiles = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    auth = {"Authorization": f"Bearer {access_token()}"}

    rows = []
    for p in profiles:
        site_key = p["site_key"]
        blog = p.get("blogspot") or {}
        url = blog.get("url", "")
        if args.only and site_key != args.only:
            continue
        if site_key in EXCLUDED:
            rows.append({"site": site_key, "url": url, "status": "excluded", "reason": EXCLUDED[site_key]})
            continue
        blog_id = str(blog.get("destination_id", ""))
        if not blog_id:
            rows.append({"site": site_key, "url": url, "status": "excluded", "reason": "no destination_id on record"})
            continue
        language = p.get("language", "en")
        widget = visitor_counter_html(site_key, language=language)
        endpoint = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts"
        site_rows = []
        try:
            for post in all_live_posts(endpoint, auth, max_posts=args.max_posts or None):
                content = post.get("content", "")
                entry = {"post_id": str(post["id"]), "post_url": post.get("url", ""), "status": "skipped_already_has_widget"}
                if MARK not in content:
                    new_content = content + widget
                    for attempt in range(4):
                        patch = requests.patch(
                            f"{endpoint}/{post['id']}", headers=auth,
                            params={"revert": "false"}, json={"content": new_content}, timeout=30,
                        )
                        if patch.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                            time.sleep(2 ** attempt * 3)
                            continue
                        patch.raise_for_status()
                        break
                    entry["status"] = "patched"
                site_rows.append(entry)
                time.sleep(0.3)
            patched = sum(1 for r in site_rows if r["status"] == "patched")
            skipped = sum(1 for r in site_rows if r["status"] == "skipped_already_has_widget")
            rows.append({"site": site_key, "url": url, "status": "done", "posts_seen": len(site_rows),
                         "patched": patched, "already_had_widget": skipped, "detail": site_rows})
        except Exception as exc:
            rows.append({"site": site_key, "url": url, "status": "failed", "error": str(exc)[:400]})
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
