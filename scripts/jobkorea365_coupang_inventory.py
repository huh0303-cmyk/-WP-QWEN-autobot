#!/usr/bin/env python3
"""Public, read-only JobKorea365 post inventory for article-specific Coupang matching.

No WordPress credentials are required and no WordPress writes are performed.
"""
from __future__ import annotations
import re, json, html, sys, time
from pathlib import Path
from datetime import datetime, timezone
import requests

BASE = "https://jobkorea365.com"
S = requests.Session()
S.headers.update({"User-Agent": "LondonProject-JobKorea365-AffiliateInventory/1.0"})

def text_only(value: str) -> str:
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value or "")
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()

posts = []
page = 1
total = 0
while True:
    params = {
        "status": "publish", "per_page": 100, "page": page,
        "orderby": "date", "order": "desc",
        "_fields": "id,date,modified,link,slug,title,excerpt,content,categories,tags,featured_media"
    }
    r = S.get(BASE + "/wp-json/wp/v2/posts", params=params, timeout=40)
    r.raise_for_status()
    rows = r.json()
    total = max(total, int(r.headers.get("X-WP-Total", "0") or 0))
    if not rows:
        break
    for p in rows:
        title = text_only(p.get("title", {}).get("rendered") or "")
        excerpt = text_only(p.get("excerpt", {}).get("rendered") or "")
        body = text_only(p.get("content", {}).get("rendered") or "")
        posts.append({
            "id": p.get("id"),
            "date": p.get("date"),
            "modified": p.get("modified"),
            "url": p.get("link"),
            "slug": p.get("slug"),
            "title": title,
            "excerpt": excerpt[:700],
            "content_preview": body[:1200],
            "categories": p.get("categories") or [],
            "tags": p.get("tags") or [],
            "featured_media": p.get("featured_media") or 0,
            "missing_tags": not bool(p.get("tags")),
            "missing_featured_image": not bool(p.get("featured_media")),
            "affiliate_slots_target": "5-10",
            "affiliate_status": "not_inserted"
        })
    if len(rows) < 100:
        break
    page += 1
    time.sleep(0.15)

report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "site": BASE,
    "mode": "public_read_only",
    "writes_performed": 0,
    "reported_total_published": total,
    "posts_collected": len(posts),
    "missing_tags": sum(x["missing_tags"] for x in posts),
    "missing_featured_images": sum(x["missing_featured_image"] for x in posts),
    "posts": posts
}
out = Path("reports/jobkorea365-coupang-post-inventory-2026-10-31.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({k: report[k] for k in ("site","mode","writes_performed","reported_total_published","posts_collected","missing_tags","missing_featured_images")}, ensure_ascii=False))
if total and len(posts) != total:
    print(f"WARNING: collected {len(posts)} posts; API reported {total}", file=sys.stderr)
    sys.exit(2)
