"""Remove dead hotlinked images (expired Replicate/Pixabay/R2-presigned URLs)
from already-published WordPress posts network-wide.

Root cause (images generated but never re-uploaded to permanent WordPress
media storage, so the post body kept pointing at a provider URL that later
expired) was fixed going forward in scripts/autopost_mega.py (commit 833e27ab,
2026-09-12): new posts now upload the image to /wp-content/uploads/ and
rewrite the body to that stable URL before publishing.

This script only cleans up the pre-fix backlog. It never tries to regenerate
a lost image - the original bytes are gone (404/expired signed URL) - it
only removes the now-broken <img> (and its wrapping <figure>, if any) so the
post stops showing a broken-image icon. Dry-run by default; set
APPLY_CHANGES=true to actually write. Concurrent-edit protection matches
scripts/repair_wp_duplicate_images.py: skip a post if it changed since we
fetched it, and verify the save before counting it as fixed.
"""
import json
import os
import socket
import time
from pathlib import Path

import urllib3.util.connection

urllib3.util.connection.allowed_gai_family = lambda: socket.AF_INET

import requests
from bs4 import BeautifulSoup

BROKEN_PATTERNS = (
    "replicate.delivery",
    "pixabay.com/get",
    ".r2.dev",
    "r2.cloudflarestorage.com",
)

APPLY_CHANGES = os.environ.get("APPLY_CHANGES", "false").strip().lower() == "true"
ONLY_SITES = [s.strip() for s in os.environ.get("REPAIR_SITES", "").split(",") if s.strip()]
AUTH_USER = "huh0303@gmail.com"

OUT_DIR = Path("artifacts/expired-image-repair")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def is_dead(url: str) -> bool:
    """Confirm the hotlinked image is actually unreachable before removing it.

    Pattern-matching the domain alone is not proof it's dead right now; this
    is the belt-and-suspenders check so a merely-slow provider isn't treated
    as broken.
    """
    try:
        r = requests.get(url, timeout=15, stream=True, headers={"User-Agent": "Mozilla/5.0"})
        r.close()
        return r.status_code >= 400
    except requests.RequestException:
        return True


def load_sites():
    registry = json.loads(Path("config/automation_hub_sites.json").read_text(encoding="utf-8"))["sites"]
    wp_sites = [s for s in registry if s.get("platform") == "wordpress"]
    if ONLY_SITES:
        wp_sites = [s for s in wp_sites if s["site_id"] in ONLY_SITES or s["url"].rstrip("/") in ONLY_SITES]
    return wp_sites


def fetch_all_posts(base_url: str, auth):
    posts = []
    page = 1
    while True:
        r = requests.get(
            f"{base_url}/wp-json/wp/v2/posts",
            auth=auth,
            params={"per_page": 100, "page": page, "context": "edit", "_fields": "id,link,modified_gmt,content,featured_media"},
            timeout=30,
        )
        if r.status_code == 400 and page > 1:
            break
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


def repair_site(site):
    base_url = site["url"].rstrip("/")
    secret = os.environ.get(site["secret_name"], "")
    if not secret:
        return {"site": base_url, "status": "skipped_no_secret"}
    auth = (AUTH_USER, secret)
    site_result = {"site": base_url, "posts_checked": 0, "posts_with_dead_images": 0, "images_removed": 0, "posts_fixed": 0, "errors": []}
    try:
        posts = fetch_all_posts(base_url, auth)
    except requests.RequestException as exc:
        site_result["errors"].append(f"list_posts_failed: {type(exc).__name__}: {str(exc)[:200]}")
        return site_result
    site_result["posts_checked"] = len(posts)

    for post in posts:
        raw = post.get("content", {}).get("raw") or post.get("content", {}).get("rendered", "")
        if not any(p in raw for p in BROKEN_PATTERNS):
            continue
        soup = BeautifulSoup(raw, "html.parser")
        dead_imgs = []
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src and any(p in src for p in BROKEN_PATTERNS) and is_dead(src):
                dead_imgs.append(img)
        if not dead_imgs:
            continue
        site_result["posts_with_dead_images"] += 1
        site_result["images_removed"] += len(dead_imgs)
        record = {"id": post["id"], "url": post["link"], "dead_image_count": len(dead_imgs), "status": "identified"}
        (OUT_DIR / "results.jsonl").open("a", encoding="utf-8").write(json.dumps(record, ensure_ascii=False) + "\n")
        if not APPLY_CHANGES:
            continue
        for img in dead_imgs:
            parent = img.find_parent("figure")
            (parent or img).decompose()
        try:
            fresh = requests.get(
                f"{base_url}/wp-json/wp/v2/posts/{post['id']}",
                auth=auth, params={"context": "edit"}, timeout=30,
            )
            fresh.raise_for_status()
            current = fresh.json()
            if current["modified_gmt"] != post["modified_gmt"]:
                record["status"] = "skipped_concurrent_edit"
                continue
            (OUT_DIR / f"{post['id']}-backup.json").write_text(json.dumps(current, ensure_ascii=False), encoding="utf-8")
            payload = {"content": str(soup)}
            r = requests.post(f"{base_url}/wp-json/wp/v2/posts/{post['id']}", auth=auth, json=payload, timeout=30)
            r.raise_for_status()
            verify = requests.get(f"{base_url}/wp-json/wp/v2/posts/{post['id']}", auth=auth, params={"context": "edit"}, timeout=30)
            verify.raise_for_status()
            if verify.json()["content"]["raw"] != payload["content"]:
                raise RuntimeError("Body save mismatch")
            record["status"] = "removed_verified"
            site_result["posts_fixed"] += 1
        except Exception as exc:
            record["status"] = f"failed:{type(exc).__name__}"
            site_result["errors"].append(f"post {post['id']}: {type(exc).__name__}: {str(exc)[:200]}")
        (OUT_DIR / "results.jsonl").open("a", encoding="utf-8").write(json.dumps(record, ensure_ascii=False) + "\n")
        time.sleep(0.5)
    return site_result


def main():
    sites = load_sites()
    summary = []
    for site in sites:
        result = repair_site(site)
        print(json.dumps(result, ensure_ascii=False))
        summary.append(result)
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    total_fixed = sum(s.get("posts_fixed", 0) for s in summary)
    total_found = sum(s.get("posts_with_dead_images", 0) for s in summary)
    print(f"\nTOTAL: {total_found} posts with dead images found, {total_fixed} fixed (APPLY_CHANGES={APPLY_CHANGES})")


if __name__ == "__main__":
    main()
