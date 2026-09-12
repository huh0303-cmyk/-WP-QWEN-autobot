#!/usr/bin/env python3
"""Read-only content-quality scan across all 25 WP sites + 33 Blogger blogs.
Finds: mojibake/broken-encoding text, empty titles, very thin content, and
exact-duplicate titles within a site. Does not fix anything by itself except
via the separate fix_empty_titles.py companion script."""
import json
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from site_registry import ACTIVE_SITES

OUT = ROOT / "artifacts/full-content-audit.json"
THIN_CHARS = 800

MOJIBAKE_RE = re.compile(r'�|[-]')


def plain_text(html):
    text = re.sub(r'<[^>]+>', ' ', html or '')
    text = re.sub(r'&[a-zA-Z#0-9]+;', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def scan_one(site_label, platform, post_id, title, content_html, url):
    issues = []
    plain_title = plain_text(title)
    plain_body = plain_text(content_html)
    if MOJIBAKE_RE.search(title) or MOJIBAKE_RE.search(content_html or ''):
        issues.append('mojibake')
    if not plain_title:
        issues.append('empty_title')
    if len(plain_body) < THIN_CHARS:
        issues.append('thin_content')
    if not issues:
        return None
    return {"site": site_label, "platform": platform, "post_id": post_id, "title": plain_title[:200],
            "url": url, "issues": issues, "content_chars": len(plain_body)}


def wp_posts(site_url):
    page = 1
    while True:
        try:
            r = requests.get(f"{site_url}/wp-json/wp/v2/posts", timeout=20,
                              params={"per_page": 100, "page": page, "_fields": "id,title,content,link", "status": "publish"})
            if r.status_code != 200:
                break
            batch = r.json()
        except Exception:
            break
        if not isinstance(batch, list) or not batch:
            break
        for p in batch:
            yield p
        if len(batch) < 100:
            break
        page += 1


def scan_wp_site(site_url, env_name, _lifecycle):
    label = site_url.replace("https://", "")
    rows = []
    titles_seen = Counter()
    try:
        for p in wp_posts(site_url):
            title_raw = p.get("title", {}).get("rendered", "")
            content_raw = p.get("content", {}).get("rendered", "")
            row = scan_one(label, "wordpress", p["id"], title_raw, content_raw, p.get("link", ""))
            if row:
                rows.append(row)
            titles_seen[plain_text(title_raw).casefold()] += 1
    except Exception as exc:
        return {"site": label, "platform": "wordpress", "error": str(exc)[:200], "issues_found": []}
    dupes = [t for t, n in titles_seen.items() if n > 1 and t]
    return {"site": label, "platform": "wordpress", "issues_found": rows, "exact_duplicate_titles": dupes}


def blogger_access_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def blogger_posts(blog_id, auth):
    endpoint = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts"
    page_token = None
    while True:
        params = {"status": "live", "fetchBodies": "true", "maxResults": 500}
        if page_token:
            params["pageToken"] = page_token
        for attempt in range(4):
            r = requests.get(endpoint, headers=auth, params=params, timeout=30)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2 ** attempt * 3)
                continue
            r.raise_for_status()
            break
        payload = r.json()
        yield from payload.get("items", [])
        page_token = payload.get("nextPageToken")
        if not page_token:
            break


def scan_blogger_site(site_key, blog_id, auth):
    rows = []
    titles_seen = Counter()
    try:
        for post in blogger_posts(blog_id, auth):
            title_raw = post.get("title", "")
            content_raw = post.get("content", "")
            row = scan_one(site_key, "blogger", str(post["id"]), title_raw, content_raw, post.get("url", ""))
            if row:
                rows.append(row)
            titles_seen[plain_text(title_raw).casefold()] += 1
    except Exception as exc:
        return {"site": site_key, "platform": "blogger", "error": str(exc)[:200], "issues_found": []}
    dupes = [t for t, n in titles_seen.items() if n > 1 and t]
    return {"site": site_key, "platform": "blogger", "issues_found": rows, "exact_duplicate_titles": dupes}


def main():
    results = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(scan_wp_site, site, env, life): site for site, env, life in ACTIVE_SITES}
        for future in as_completed(futures):
            results.append(future.result())
            print("wp done:", futures[future])

    profiles = json.loads((ROOT / "config" / "content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    auth = {"Authorization": f"Bearer {blogger_access_token()}"}
    blogger_targets = [(p["site_key"], str((p.get("blogspot") or {}).get("destination_id", "")))
                       for p in profiles if (p.get("blogspot") or {}).get("ready_for_automation") and (p.get("blogspot") or {}).get("destination_id")]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(scan_blogger_site, key, blog_id, auth): key for key, blog_id in blogger_targets}
        for future in as_completed(futures):
            results.append(future.result())
            print("blogger done:", futures[future])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    total_issues = sum(len(r.get("issues_found", [])) for r in results)
    total_dupes = sum(len(r.get("exact_duplicate_titles", [])) for r in results)
    errors = [r["site"] for r in results if r.get("error")]
    print(json.dumps({"sites_scanned": len(results), "total_flagged_posts": total_issues,
                       "sites_with_duplicate_titles": total_dupes, "sites_errored": errors}, ensure_ascii=False))


if __name__ == "__main__":
    main()
