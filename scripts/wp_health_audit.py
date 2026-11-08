#!/usr/bin/env python3
"""Read-only WordPress editorial/technical health audit; never publishes or edits posts."""
import collections
import datetime as dt
import hashlib
import html
import json
import re
import urllib.parse
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "wp_health.json"
DASH = ROOT / "docs" / "dashboard.json"
HEADERS = {"User-Agent": "Korea365-ReadOnly-HealthAudit/1.0"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

def plain(s):
    return re.sub(r"\\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(s or "")))).strip()

def fetch(url, params=None):
    response = SESSION.get(url, params=params, timeout=16)
    response.raise_for_status()
    return response

def inspect(row):
    site = row["site"]
    base = row["url"].rstrip("/")
    result = {"site": site, "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(), "status": "unknown", "posts_checked": 0}
    try:
        home = fetch(base)
        result["http_status"] = home.status_code
        api = fetch(base + "/wp-json/wp/v2/posts", {"per_page": 50, "orderby": "date", "order": "desc", "_fields": "id,date,link,title,content,featured_media"})
        posts = api.json()
        if not isinstance(posts, list):
            raise ValueError("unexpected posts payload")
        result["posts_checked"] = len(posts)
        title_seen = collections.Counter()
        image_seen = collections.Counter()
        prefix_seen = collections.Counter()
        no_image = 0
        issues = []
        for p in posts:
            title = plain(p.get("title", {}).get("rendered", ""))
            key = re.sub(r"[^\\w]+", "", title.casefold())
            if key: title_seen[key] += 1
            first = " ".join(title.casefold().split()[:2])
            if first: prefix_seen[first] += 1
            media = p.get("featured_media") or 0
            if media: image_seen[str(media)] += 1
            else: no_image += 1
            body = plain(p.get("content", {}).get("rendered", ""))
            if len(body) < 450: issues.append("short_article")
            if re.search(r"\\[Image Prompt:|<3-6 word|as an ai language model", body, re.I): issues.append("template_leak")
        result["exact_duplicate_titles"] = sum(v - 1 for v in title_seen.values() if v > 1)
        result["reused_featured_media"] = sum(v - 1 for v in image_seen.values() if v > 1)
        result["missing_featured_media"] = no_image
        result["repeated_title_prefixes"] = sum(v - 2 for v in prefix_seen.values() if v > 2)
        result["content_flags"] = len(issues)
        result["latest_publish_date"] = (posts[0].get("date") or "")[:10] if posts else None
        result["rank_math"] = "not_authenticated"
        result["site_kit"] = "use_google_apis_not_public_plugin_scraping"
        severe = result["exact_duplicate_titles"] > 0 or result["content_flags"] > 0
        caution = result["reused_featured_media"] > 0 or result["repeated_title_prefixes"] > 0 or result["missing_featured_media"] > 0
        result["status"] = "red" if severe else "yellow" if caution else "green"
    except Exception as exc:
        result["status"] = "unknown"
        result["error"] = type(exc).__name__ + ": " + str(exc)[:150]
    return result

def main():
    data = json.loads(DASH.read_text(encoding="utf-8"))
    sites = {r["site"]: r for r in data.get("rows", []) if r.get("platform") == "wordpress" and r.get("url")}
    results = [inspect(row) for row in sites.values()]
    payload = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "method": "public_wordpress_rest_read_only", "sample": "latest_50_public_posts", "warning": "Editorial/technical heuristic, NOT Rank Math score or Site Kit analytics; unknown is never green", "sites": {r["site"]: r for r in results}}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sites": len(results), "statuses": dict(collections.Counter(r["status"] for r in results))}))

if __name__ == "__main__":
    main()
