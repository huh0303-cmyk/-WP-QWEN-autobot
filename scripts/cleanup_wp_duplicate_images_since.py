"""Remove only duplicate WordPress featured photos for posts dated 2026-11-06 onward.
Preserve content, metadata, and unique images. Older images anchor the comparison.
"""
import os, json, time
from datetime import datetime
from urllib.parse import urlparse
import requests
from fix_duplicate_hero_images_v2 import SITES, WP_USER
from editorial_image_guard import image_fingerprint, same_photo

SINCE = os.getenv("SINCE_DATE", "2026-11-06")
DRY = os.getenv("DRY_RUN", "true").lower() != "false"
EXCLUDED = {"k-health365.com", "ki-korea.com", "sis-korea.com", "theseouljournal.com"}
FILTER = {x.strip().lower() for x in os.getenv("SITE_FILTER", "").split(",") if x.strip()}

def run_site(site):
    domain = urlparse(site["url"]).netloc.lower()
    if domain in EXCLUDED or (FILTER and domain not in FILTER):
        return {"site": domain, "status": "excluded"}
    pw = os.getenv(site["wp_pass_env"])
    if not pw:
        return {"site": domain, "status": "missing_credentials"}
    base = site["url"].rstrip("/") + "/wp-json/wp/v2"
    auth = (os.getenv("WP_USER") or WP_USER, pw)
    posts = []
    try:
        for page in range(1, 101):
            r = requests.get(base + "/posts", auth=auth, params={
                "page": page, "per_page": 100, "status": "publish",
                "orderby": "date", "order": "asc",
                "_fields": "id,date,link,featured_media"}, timeout=35)
            if r.status_code == 400 and page > 1: break
            r.raise_for_status()
            batch = r.json()
            posts.extend(batch)
            if len(batch) < 100: break
        else:
            raise RuntimeError("post pagination exceeded limit")
        fingerprints = []
        media_cache = {}
        report = {"site": domain, "status": "ok", "scanned": 0, "duplicates": 0,
                  "removed": 0, "errors": [], "posts": []}
        for post in posts:
            mid = post.get("featured_media") or 0
            if not mid: continue
            if mid not in media_cache:
                media = requests.get(base + f"/media/{mid}", auth=auth, timeout=25)
                media.raise_for_status()
                media_cache[mid] = media.json().get("source_url")
            url = media_cache[mid]
            if not url: raise RuntimeError(f"missing media source for {mid}")
            fp = image_fingerprint(url)
            prior = next((x for x in fingerprints if same_photo(fp, x["fp"])), None)
            eligible = post["date"][:10] >= SINCE
            if eligible: report["scanned"] += 1
            if prior and eligible:
                report["duplicates"] += 1
                item = {"post_id": post["id"], "url": post.get("link"), "duplicate_of": prior["post_id"]}
                if not DRY:
                    patch = requests.post(base + f"/posts/{post['id']}", auth=auth,
                        json={"featured_media": 0}, timeout=35)
                    patch.raise_for_status()
                    if patch.json().get("featured_media") != 0:
                        raise RuntimeError("featured_media removal not confirmed")
                    report["removed"] += 1
                report["posts"].append(item)
            elif not prior:
                fingerprints.append({"post_id": post["id"], "fp": fp})
        return report
    except Exception as exc:
        return {"site": domain, "status": "error", "error": f"{type(exc).__name__}: {str(exc)[:180]}"}

def main():
    results = []
    for site in SITES:
        result = run_site(site)
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    with open("wp_duplicate_cleanup_report.json", "w", encoding="utf-8") as f:
        json.dump({"dry_run": DRY, "since": SINCE, "results": results}, f, ensure_ascii=False, indent=2)
    if any(x["status"] == "error" for x in results):
        raise SystemExit("One or more sites could not be fully audited")

if __name__ == "__main__":
    main()
