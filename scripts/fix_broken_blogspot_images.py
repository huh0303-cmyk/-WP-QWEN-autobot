#!/usr/bin/env python3
"""Replace the 34 broken (expired Replicate/R2) images found in the 2026-09-12
Blogspot re-audit with a fresh, permanently-hosted stock photo.

Read-only root-cause fix belongs to Codex (autopost_mega.py / replicate_image_provider.py);
this only patches EXISTING broken posts so they stop showing a broken-image icon today.
Downloads a Pixabay photo and commits it to assets/blogger_images/ in this repo
(raw.githubusercontent.com URL never expires), then replaces the dead <img src="..."> in
the post's content with the new stable URL. Does not touch anything else in the post.
"""
import base64
import hashlib
import html
import json
import os
import re
import time

import requests

REPORT_PATH = "artifacts/broken-image-audit-blogspot.json"
OUT_PATH = "artifacts/blogspot-image-fix-results.json"
PIXABAY_KEY = os.environ.get("PIXABAY_KEY", "")
REPO = os.environ["GITHUB_REPOSITORY"]
GH_TOKEN = os.environ["GH_ASSET_TOKEN"]

STOP = set("a an the of in on at for and with your you how what who why when where guide "
           "practical korea 2026".split())


def blogger_access_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def query_from_title(title):
    words = re.findall(r"[a-zA-Z]+", title.lower())
    kept = [w for w in words if len(w) > 2 and w not in STOP]
    return " ".join(kept[:5]) or "Korea"


def find_pixabay_photo(query):
    r = requests.get("https://pixabay.com/api/", params={
        "key": PIXABAY_KEY, "q": query, "image_type": "photo",
        "orientation": "horizontal", "safesearch": "true", "min_width": 1000, "per_page": 10,
    }, timeout=15)
    r.raise_for_status()
    hits = r.json().get("hits", [])
    return hits[0] if hits else None


def host_permanently(url, asset_key):
    download = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    download.raise_for_status()
    data = download.content
    content_type = download.headers.get("content-type", "")
    ext = ".png" if "png" in content_type else ".webp" if "webp" in content_type else ".jpg"
    digest = hashlib.sha256(data).hexdigest()[:16]
    path = f"assets/blogger_images/{asset_key}-{digest}{ext}"
    api = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json"}
    response = requests.put(api, headers=headers, json={
        "message": f"fix: replace expired blogspot image {asset_key} [skip ci]",
        "content": base64.b64encode(data).decode(),
        "branch": "main",
    }, timeout=60)
    response.raise_for_status()
    return f"https://raw.githubusercontent.com/{REPO}/main/{path}"


def wait_until_live(url, attempts=6):
    for i in range(attempts):
        try:
            r = requests.head(url, timeout=15)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(2 ** i)
    return False


def main():
    report = json.loads(open(REPORT_PATH, encoding="utf-8").read())
    broken = report["broken_images"]
    profiles = json.loads(open("config/content_engine_profiles.json", encoding="utf-8").read())["profiles"]
    blog_id_by_key = {p["site_key"]: str((p.get("blogspot") or {}).get("destination_id", "")) for p in profiles}

    auth = {"Authorization": f"Bearer {blogger_access_token()}"}
    results = []

    for item in broken:
        site = item["site"]
        post_id = item["post_id"]
        old_url = item["image_url"]
        title = html.unescape(item["post_title"])
        blog_id = blog_id_by_key.get(site)
        entry = {"site": site, "post_id": post_id, "post_url": item["post_url"], "old_image_url": old_url}
        if not blog_id:
            entry["status"] = "failed"
            entry["error"] = "no destination_id"
            results.append(entry)
            continue
        try:
            query = query_from_title(title)
            photo = find_pixabay_photo(query)
            if not photo:
                query = "Korea"
                photo = find_pixabay_photo(query)
            if not photo:
                entry["status"] = "failed"
                entry["error"] = "no pixabay result even for fallback query"
                results.append(entry)
                continue
            asset_key = f"blogspot-fix-{site}-{post_id}"
            stable_url = host_permanently(photo["largeImageURL"], asset_key)
            if not wait_until_live(stable_url):
                entry["status"] = "failed"
                entry["error"] = "hosted asset did not verify live after commit"
                results.append(entry)
                continue

            endpoint = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{post_id}"
            get = requests.get(endpoint, headers=auth, params={"fetchBodies": "true"}, timeout=30)
            get.raise_for_status()
            content = get.json().get("content", "")
            if old_url not in content:
                entry["status"] = "failed"
                entry["error"] = "old image url no longer present in live content (already edited?)"
                results.append(entry)
                continue
            new_content = content.replace(old_url, stable_url)
            for attempt in range(4):
                patch = requests.patch(endpoint, headers=auth, params={"revert": "false"},
                                        json={"content": new_content}, timeout=30)
                if patch.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                    time.sleep(2 ** attempt * 3)
                    continue
                patch.raise_for_status()
                break
            entry["status"] = "fixed"
            entry["new_image_url"] = stable_url
            entry["pixabay_query"] = query
            entry["pixabay_source"] = photo.get("pageURL", "")
            results.append(entry)
            print(f"fixed: {site} #{post_id} -> {stable_url}")
        except Exception as exc:
            entry["status"] = "failed"
            entry["error"] = str(exc)[:400]
            results.append(entry)
            print(f"failed: {site} #{post_id}: {exc}")
        time.sleep(0.5)
        os.makedirs("artifacts", exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    fixed = sum(1 for r in results if r["status"] == "fixed")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(json.dumps({"total": len(results), "fixed": fixed, "failed": failed}, ensure_ascii=False))


if __name__ == "__main__":
    main()
