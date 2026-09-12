#!/usr/bin/env python3
"""Find the same image URL reused across multiple posts published today (or the
last N days) across all WP sites. Triggered by a user spotting the same stock
passport photo on multiple koreataxnlaw.com articles today. Read-only."""
import json
import re
import socket
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import requests

_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_only

sys.path.insert(0, "scripts")
from site_registry import ACTIVE_SITES

DAYS_BACK = 3
IMG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']')
cutoff = (datetime.utcnow() - timedelta(days=DAYS_BACK)).isoformat()


def extract_images(html):
    return [u for u in IMG_RE.findall(html or '') if u.startswith('http')]


def recent_posts(site_url):
    posts = []
    page = 1
    while True:
        r = None
        for attempt in range(4):
            try:
                r = requests.get(f"{site_url}/wp-json/wp/v2/posts", timeout=40,
                                  params={"per_page": 30, "page": page, "status": "publish",
                                          "after": cutoff + "Z", "orderby": "date", "order": "desc",
                                          "_fields": "id,title,content,link,date"})
                break
            except Exception as exc:
                print(f"  connection error on {site_url} page{page} attempt{attempt}: {type(exc).__name__}: {str(exc)[:150]}")
                time.sleep(3 * (attempt + 1))
        if r is None or r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        posts.extend(batch)
        if len(batch) < 30:
            break
        page += 1
    return posts


def scan_site(site_url):
    rows = []
    try:
        for p in recent_posts(site_url):
            title = re.sub('<[^<]+?>', '', p.get("title", {}).get("rendered", ""))
            for img in extract_images(p.get("content", {}).get("rendered", "")):
                rows.append({"site": site_url.replace("https://", ""), "post_id": p["id"],
                             "title": title[:150], "link": p.get("link", ""),
                             "date": p.get("date", ""), "image_url": img})
    except Exception as exc:
        print(f"error scanning {site_url}: {exc}")
    return rows


def main():
    all_rows = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(scan_site, site): site for site, _, _ in ACTIVE_SITES}
        for future in as_completed(futures):
            rows = future.result()
            all_rows.extend(rows)
            print("scanned:", futures[future], "images:", len(rows))

    by_image = defaultdict(list)
    for row in all_rows:
        by_image[row["image_url"]].append(row)

    dupes = {url: rows for url, rows in by_image.items() if len(rows) > 1}
    print(f"\ntotal recent image refs: {len(all_rows)}, unique urls: {len(by_image)}, reused urls: {len(dupes)}")

    import os
    os.makedirs("artifacts", exist_ok=True)
    with open("artifacts/duplicate-images-recent.json", "w", encoding="utf-8") as f:
        json.dump(dupes, f, ensure_ascii=False, indent=2)
    with open("artifacts/duplicate-images-raw.json", "w", encoding="utf-8") as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=2)

    # sort by how many times reused, print top offenders
    ranked = sorted(dupes.items(), key=lambda kv: -len(kv[1]))
    for url, rows in ranked[:30]:
        sites = sorted(set(r["site"] for r in rows))
        print(f"\n[{len(rows)}x, {len(sites)} sites] {url}")
        for r in rows[:6]:
            print(f"   {r['site']} #{r['post_id']} ({r['date'][:10]}): {r['title']}")


if __name__ == "__main__":
    main()
