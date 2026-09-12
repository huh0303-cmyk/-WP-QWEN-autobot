#!/usr/bin/env python3
"""Read-only re-check: scan all Blogger blogs for broken <img> URLs (404/expired/etc).
Follow-up to the 2026-09-12 broken-image audit, scoped to Blogspot only, after a
user report of a fresh broken image on kstudy365.blogspot.com."""
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

ROOT_CONFIG = "config/content_engine_profiles.json"
OUT = "artifacts/broken-image-audit-blogspot.json"
IMG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']')


def extract_images(html):
    return [u for u in IMG_RE.findall(html or '') if u.startswith('http')]


def access_token():
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


def scan_blog(site_key, blog_id, auth):
    refs = []
    try:
        for post in blogger_posts(blog_id, auth):
            title = re.sub('<[^<]+?>', '', post.get("title", ""))
            for img in extract_images(post.get("content", "")):
                refs.append((img, site_key, str(post["id"]), title[:150], post.get("url", "")))
    except Exception as exc:
        return [], {"site": site_key, "error": str(exc)[:200]}
    return refs, {"site": site_key, "posts_with_images": len({r[2] for r in refs}) if refs else 0}


def check_image(url, session):
    try:
        r = session.head(url, timeout=12, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code in (405, 403) or r.status_code >= 400:
            r = session.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"}, stream=True)
            r.close()
        return url, r.status_code, ""
    except requests.RequestException as exc:
        return url, None, f"{type(exc).__name__}"


def main():
    profiles = json.loads(open(ROOT_CONFIG, encoding="utf-8").read())["profiles"]
    auth = {"Authorization": f"Bearer {access_token()}"}
    targets = [(p["site_key"], str((p.get("blogspot") or {}).get("destination_id", "")))
               for p in profiles if (p.get("blogspot") or {}).get("ready_for_automation") and (p.get("blogspot") or {}).get("destination_id")]

    all_refs = []
    site_reports = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(scan_blog, key, blog_id, auth): key for key, blog_id in targets}
        for future in as_completed(futures):
            refs, report = future.result()
            all_refs.extend(refs)
            site_reports.append(report)
            print("scanned:", futures[future], "images:", len(refs))

    unique_urls = {}
    for img, site, pid, title, purl in all_refs:
        unique_urls.setdefault(img, []).append((site, pid, title, purl))
    print(f"total image refs: {len(all_refs)}, unique urls: {len(unique_urls)}")

    broken = []
    session = requests.Session()
    with ThreadPoolExecutor(max_workers=15) as pool:
        futures = {pool.submit(check_image, url, session): url for url in unique_urls}
        checked = 0
        for future in as_completed(futures):
            url, status, error = future.result()
            checked += 1
            if checked % 100 == 0:
                print(f"checked {checked}/{len(unique_urls)}")
            if status is None or status >= 400:
                for site, pid, title, purl in unique_urls[url]:
                    broken.append({"site": site, "post_id": pid, "post_title": title, "post_url": purl,
                                   "image_url": url, "status": status, "error": error})

    os.makedirs("artifacts", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"site_reports": site_reports, "broken_images": broken,
                   "total_unique_images": len(unique_urls)}, f, ensure_ascii=False, indent=2)
    print(json.dumps({"blogs_scanned": len(site_reports), "total_unique_images": len(unique_urls),
                       "broken_image_refs": len(broken),
                       "blogs_errored": [r["site"] for r in site_reports if r.get("error")]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
