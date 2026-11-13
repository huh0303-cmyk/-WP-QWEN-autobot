#!/usr/bin/env python3
"""Read-only audit of ALL published WordPress posts: missing and duplicate featured media.
Usage: WP_SITE_URL=https://k-trip365.com python scripts/audit_ktrip_images.py
Optional credentials WP_USER and WP_APP_PASSWORD for private REST access.
Outputs artifacts/ktrip_image_audit.json. No posts are changed.
"""
import collections
import json
import os
from pathlib import Path
import requests

site = os.environ.get("WP_SITE_URL", "https://k-trip365.com").rstrip("/")
auth = (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"]) if os.getenv("WP_USER") and os.getenv("WP_APP_PASSWORD") else None
session = requests.Session()
posts = []
page = 1
while True:
    response = session.get(site + "/wp-json/wp/v2/posts", params={
        "status": "publish", "per_page": 100, "page": page,
        "_fields": "id,link,title,featured_media,date",
    }, auth=auth, timeout=30)
    if response.status_code == 400 and page > 1:
        break
    response.raise_for_status()
    batch = response.json()
    if not batch:
        break
    posts.extend(batch)
    if len(batch) < 100:
        break
    page += 1

groups = collections.defaultdict(list)
missing = []
for post in posts:
    mid = int(post.get("featured_media") or 0)
    record = {"id": post["id"], "url": post.get("link"), "title": post.get("title", {}).get("rendered", "")}
    if not mid:
        missing.append(record)
    else:
        groups[mid].append(record)

duplicates = {str(mid): records for mid, records in groups.items() if len(records) > 1}
report = {"site": site, "posts_scanned": len(posts), "missing_featured_count": len(missing),
          "duplicate_featured_groups": len(duplicates),
          "duplicate_affected_posts": sum(len(v) for v in duplicates.values()),
          "missing_featured": missing, "duplicate_featured": duplicates,
          "note": "Media ID duplicates only. Different IDs with identical pixels require hash/perceptual audit."}
out = Path("artifacts/ktrip_image_audit.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k:v for k,v in report.items() if k not in ("missing_featured", "duplicate_featured")}, ensure_ascii=False))
print("Audit report:", out)
