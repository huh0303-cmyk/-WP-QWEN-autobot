"""Read-only affiliate preflight for every enabled WordPress destination in the control-room registry.
No WordPress site is excluded by domain or prior protection status. This job never edits posts.
"""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / "config" / "automation_hub_sites.json").read_text(encoding="utf-8"))
WP_USER = os.getenv("WP_USER", "").strip()
# The registry is authoritative. Naver and Tistory are outside this affiliate workflow;
# every enabled WordPress destination, including previously protected sites, is included.
rows = [
    s for s in REGISTRY.get("sites", [])
    if s.get("platform") == "wordpress" and s.get("enabled", True)
]
report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "execution": "github_actions_cloud",
    "mode": "read_only_preflight",
    "scope_policy": "all_enabled_wordpress_sites_no_domain_exclusions",
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
                "affiliate_slots_target": "10",
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
blocked_sites = [
    {"site_id": s["site_id"], "url": s["url"], "reason": s.get("error", "wordpress_auth_failed"), "http_status": s.get("auth_http")}
    for s in report["sites"] if s.get("auth") != "ok"
]
summary = {
    **report["totals"],
    "target_sites": report["target_sites"],
    "status": "complete" if not blocked_sites else "partial_with_access_warnings",
    "blocked_sites": blocked_sites,
    "report": str(out),
    "writes_performed": 0,
}
print(json.dumps(summary, ensure_ascii=False))
# This is a read-only inventory: partial access is recorded as a warning in the
# artifact and console summary, not treated as a crashed workflow. Never hide it.
sys.exit(0)
