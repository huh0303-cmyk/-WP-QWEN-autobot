"""Cloud-only, read-only preflight for the 24 general WordPress sites.
This job never edits posts. It creates a manifest for the affiliate placement stage.
"""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / "config" / "automation_hub_sites.json").read_text(encoding="utf-8"))
WP_USER = os.getenv("WP_USER", "").strip()
EXCLUDED = {"wp_khealth365", "wp_koreanews", "wp_seouljournal"}
rows = [s for s in REGISTRY.get("sites", []) if s.get("platform") == "wordpress" and s.get("site_id") not in EXCLUDED and s.get("enabled", True)]
report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "execution": "github_actions_cloud",
    "mode": "read_only_preflight",
    "target_sites": len(rows),
    "sites": [],
    "totals": {"authenticated": 0, "blocked": 0, "posts_seen": 0, "missing_tags": 0, "missing_featured_images": 0},
    "affiliate_placement": {"status": "BLOCKED_PENDING_VALIDATED_ACCOUNT_LINKS_AND_IMAGE_RIGHTS", "writes_performed": 0},
}
for site in rows:
    url = site["url"].rstrip("/")
    secret_name = site.get("secret_name", "")
    password = os.getenv(secret_name, "").strip()
    item = {"site_id": site["site_id"], "url": url, "auth": "blocked", "posts_seen": 0, "missing_tags": 0, "missing_featured_images": 0, "posts": []}
    if not WP_USER or not password:
        item["error"] = "missing_wp_user_or_site_secret"
        report["totals"]["blocked"] += 1
        report["sites"].append(item)
        continue
    try:
        auth = requests.get(url + "/wp-json/wp/v2/users/me", auth=(WP_USER, password), params={"context":"edit"}, timeout=20)
        item["auth_http"] = auth.status_code
        if auth.status_code != 200:
            item["error"] = "wordpress_auth_failed"
            report["totals"]["blocked"] += 1
            report["sites"].append(item)
            continue
        item["auth"] = "ok"
        report["totals"]["authenticated"] += 1
        response = requests.get(url + "/wp-json/wp/v2/posts", auth=(WP_USER, password),
            params={"per_page":100, "page":1, "status":"publish", "_fields":"id,date,link,slug,title,tags,featured_media"},
            timeout=30)
        response.raise_for_status()
        posts = response.json()
        item["posts_seen"] = len(posts)
        item["total_published"] = int(response.headers.get("X-WP-Total", len(posts)))
        for p in posts:
            missing_tags = not bool(p.get("tags"))
            missing_image = not bool(p.get("featured_media"))
            item["missing_tags"] += int(missing_tags)
            item["missing_featured_images"] += int(missing_image)
            item["posts"].append({
                "id": p.get("id"), "date": p.get("date"), "url": p.get("link"),
                "title": p.get("title", {}).get("rendered", ""),
                "tags_count": len(p.get("tags") or []),
                "featured_media": p.get("featured_media") or 0,
                "missing_tags": missing_tags, "missing_featured_image": missing_image,
                "affiliate_slots_target": "5-10",
                "affiliate_status": "not_inserted"
            })
        report["totals"]["posts_seen"] += item["posts_seen"]
        report["totals"]["missing_tags"] += item["missing_tags"]
        report["totals"]["missing_featured_images"] += item["missing_featured_images"]
    except Exception as exc:
        item["error"] = type(exc).__name__
        report["totals"]["blocked"] += 1
    report["sites"].append(item)

out = ROOT / "affiliate_cloud_preflight.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({**report["totals"], "target_sites": report["target_sites"], "report": str(out), "writes_performed": 0}, ensure_ascii=False))
sys.exit(0 if report["totals"]["blocked"] == 0 else 1)
