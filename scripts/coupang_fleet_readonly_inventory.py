#!/usr/bin/env python3
"""Read-only visitor-ranked WordPress inventory for the Coupang rollout.

Never writes to WordPress. Produces a sanitized JSON manifest for review.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.site_registry import SITES  # noqa: E402

EXCLUDED_NEWS = {"https://koreanews365.com", "https://theseouljournal.com"}
WP_USER = os.getenv("WP_USER", "huh0303@gmail.com").strip()
OUT = Path(os.getenv("REPORT_PATH", "artifacts/coupang_fleet_readonly_manifest.json"))
TIMEOUT = 20
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "LondonProject-CoupangFleetAudit/1.0"})


def parse_yesterday(payload):
    """Return a confirmed previous-day visitor integer; never coerce missing to zero."""
    if not isinstance(payload, dict):
        return None
    keys = (
        "yesterday", "yesterday_count", "yesterday_visitors", "visitors_yesterday",
        "previous_day", "previous_day_visitors", "visitors_previous_day",
    )
    for key in keys:
        value = payload.get(key)
        if isinstance(value, dict):
            for nested in ("visitors", "count", "value"):
                if nested in value:
                    value = value[nested]
                    break
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return int(value)
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
    return None


def safe_get(url, auth=None, params=None):
    response = SESSION.get(url, auth=auth, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    targets = [(url.rstrip("/"), env_name, status) for url, env_name, status in SITES
               if url.rstrip("/") not in EXCLUDED_NEWS]
    sites = []
    for index, (site_url, secret_name, registry_status) in enumerate(targets, start=1):
        result = {
            "site_url": site_url,
            "registry_secret_name": secret_name,
            "registry_status": registry_status,
            "visitor_status": "NOT_CHECKED",
            "yesterday_visitors": None,
            "post_inventory_status": "NOT_CHECKED",
            "published_posts_found": 0,
            "posts": [],
            "errors": [],
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        password = os.getenv(secret_name, "")
        if not password:
            result["visitor_status"] = "BLOCKED_MISSING_CREDENTIAL"
            result["post_inventory_status"] = "BLOCKED_MISSING_CREDENTIAL"
            result["errors"].append("Required site credential secret is not available to this workflow.")
            sites.append(result)
            continue
        auth = (WP_USER, password)
        try:
            metrics = safe_get(
                f"{site_url}/wp-json/site-stats/v1/visitors", auth=auth
            ).json()
            value = parse_yesterday(metrics)
            if value is None:
                result["visitor_status"] = "BLOCKED_UNRECOGNIZED_METRIC"
                result["errors"].append("Visitor endpoint returned no recognized previous-day count; raw values are not treated as zero.")
            else:
                result["yesterday_visitors"] = value
                result["visitor_status"] = "VERIFIED"
        except Exception as exc:
            result["visitor_status"] = "FAILED"
            result["errors"].append(f"Visitor endpoint: {type(exc).__name__}: {str(exc)[:220]}")
        try:
            response = safe_get(
                f"{site_url}/wp-json/wp/v2/posts",
                auth=auth,
                params={
                    "per_page": 100,
                    "page": 1,
                    "status": "publish",
                    "orderby": "date",
                    "order": "desc",
                    "_fields": "id,date,modified,link,slug,title",
                },
            )
            posts = response.json()
            if not isinstance(posts, list):
                raise ValueError("WordPress posts endpoint did not return a list")
            result["posts"] = [
                {
                    "id": post.get("id"),
                    "date": post.get("date"),
                    "modified": post.get("modified"),
                    "title": (post.get("title") or {}).get("rendered", ""),
                    "slug": post.get("slug", ""),
                    "permalink": post.get("link", ""),
                    "planned_action": "REVIEW_PRODUCT_MATCH_ONLY",
                }
                for post in posts
            ]
            result["published_posts_found"] = len(posts)
            result["post_inventory_status"] = "VERIFIED"
        except Exception as exc:
            result["post_inventory_status"] = "FAILED"
            result["errors"].append(f"Posts endpoint: {type(exc).__name__}: {str(exc)[:220]}")
        sites.append(result)
        # Low request rate; a failure on one destination never stops the rest.
        time.sleep(0.25)

    ranked = sorted(
        [s for s in sites if s["visitor_status"] == "VERIFIED"],
        key=lambda s: s["yesterday_visitors"],
        reverse=True,
    )
    for rank, site in enumerate(ranked, start=1):
        site["visitor_rank"] = rank
    ranked_urls = {s["site_url"] for s in ranked}
    for site in sites:
        if site["site_url"] not in ranked_urls:
            site["visitor_rank"] = None
    manifest = {
        "mode": "READ_ONLY_NO_WORDPRESS_WRITES",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "timezone_for_rank": "Asia/Seoul",
        "ranking_metric": "verified previous-KST-day visitor count descending",
        "target_site_count": len(targets),
        "verified_visitor_count": len(ranked),
        "sites_with_verified_post_inventory": sum(s["post_inventory_status"] == "VERIFIED" for s in sites),
        "total_published_posts_inventoried": sum(s["published_posts_found"] for s in sites),
        "write_enabled": False,
        "sites": sorted(sites, key=lambda s: (s["visitor_rank"] is None, s["visitor_rank"] or 9999, s["site_url"])),
    }
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "mode": manifest["mode"],
        "report_path": str(OUT),
        "target_site_count": manifest["target_site_count"],
        "verified_visitor_count": manifest["verified_visitor_count"],
        "sites_with_verified_post_inventory": manifest["sites_with_verified_post_inventory"],
        "total_published_posts_inventoried": manifest["total_published_posts_inventoried"],
        "write_enabled": False,
    }, ensure_ascii=False))
    # Partial inventory is still useful and should be published as an artifact.
    # Do not fail the whole fleet because one site is misconfigured.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
