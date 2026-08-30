#!/usr/bin/env python3
"""Restore WordPress private posts only when Google URL Inspection confirms indexing.

Safety rules:
- scans status=private with authenticated WordPress REST API
- checks each private post with Search Console URL Inspection
- republishes only when verdict == PASS
- API errors, quota errors, missing GSC properties, and non-PASS results stay private
- never deletes content
- writes a detailed resumable receipt to restore_indexed_private_result.json
"""

import json
import os
import socket
import sys
import time
from datetime import datetime, timezone

import requests

# Hostinger sites can fail over IPv6 from GitHub runners; force IPv4 as in the existing pruner.
_original_getaddrinfo = socket.getaddrinfo

def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

socket.getaddrinfo = _ipv4_getaddrinfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_registry import ACTIVE_SITES  # noqa: E402
from daily_site_traffic import get_gsc_token, gsc_get  # noqa: E402

WP_USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
RESULT_PATH = "restore_indexed_private_result.json"
UA = {"User-Agent": "Mozilla/5.0 (GitHubActions; WP-Indexed-Private-Restore/1.0)"}


def save(data):
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def property_for(domain, site_url, accessible):
    candidates = (
        site_url.rstrip("/") + "/",
        site_url.rstrip("/"),
        f"sc-domain:{domain}",
    )
    for p in candidates:
        if p in accessible:
            return p
    return None


def fetch_private_posts(site_url, password):
    posts = []
    page = 1
    while True:
        r = requests.get(
            f"{site_url}/wp-json/wp/v2/posts",
            auth=(WP_USER, password),
            params={
                "status": "private",
                "context": "edit",
                "per_page": 100,
                "page": page,
                "orderby": "date",
                "order": "asc",
                "_fields": "id,link,slug,title,status,date,date_gmt",
            },
            headers=UA,
            timeout=35,
        )
        if r.status_code == 400 and "rest_post_invalid_page_number" in r.text:
            break
        if r.status_code != 200:
            raise RuntimeError(f"private list HTTP {r.status_code}: {r.text[:220]}")
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


def inspect_url(token, prop, url, retries=4):
    for attempt in range(retries):
        r = requests.post(
            "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"inspectionUrl": url, "siteUrl": prop},
            timeout=30,
        )
        if r.status_code == 200:
            s = r.json().get("inspectionResult", {}).get("indexStatusResult", {})
            return {
                "ok": True,
                "verdict": s.get("verdict"),
                "coverageState": s.get("coverageState"),
                "indexingState": s.get("indexingState"),
                "robotsTxtState": s.get("robotsTxtState"),
                "pageFetchState": s.get("pageFetchState"),
                "lastCrawlTime": s.get("lastCrawlTime"),
                "googleCanonical": s.get("googleCanonical"),
                "userCanonical": s.get("userCanonical"),
            }
        if r.status_code == 429:
            time.sleep(8 * (attempt + 1))
            continue
        return {"ok": False, "http": r.status_code, "error": r.text[:220]}
    return {"ok": False, "http": 429, "error": "quota retry exhausted"}


def publish(site_url, password, post_id):
    r = requests.post(
        f"{site_url}/wp-json/wp/v2/posts/{post_id}",
        auth=(WP_USER, password),
        json={"status": "publish"},
        headers=UA,
        timeout=35,
    )
    return r.status_code in (200, 201), r.status_code, r.text[:220]


def title_of(post):
    t = post.get("title") or ""
    return t.get("rendered", "") if isinstance(t, dict) else str(t)


def main():
    result = {
        "schema": 1,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "rule": "restore only private posts whose current Google URL Inspection verdict is PASS",
        "sites": {},
    }

    token = get_gsc_token()
    resp = gsc_get(token, "/sites")
    if resp.status_code != 200:
        raise RuntimeError(f"GSC sites HTTP {resp.status_code}: {resp.text[:220]}")
    accessible = {x.get("siteUrl") for x in resp.json().get("siteEntry", []) if x.get("siteUrl")}

    print(f"Active registry targets: {len(ACTIVE_SITES)}")

    for site_url, env_key, lifecycle in ACTIVE_SITES:
        site_url = site_url.rstrip("/")
        domain = site_url.replace("https://", "")
        site_result = {
            "lifecycle": lifecycle,
            "secret": env_key,
            "status": "STARTED",
            "private_before": 0,
            "restored_indexed": 0,
            "kept_private_unindexed": 0,
            "kept_private_uncertain": 0,
            "publish_failed": 0,
            "items": [],
        }
        result["sites"][domain] = site_result
        save(result)

        password = os.getenv(env_key, "").strip()
        if not password:
            site_result["status"] = "SKIP_NO_SECRET"
            save(result)
            print(f"SKIP {domain}: missing {env_key}")
            continue

        prop = property_for(domain, site_url, accessible)
        site_result["gsc_property"] = prop
        if not prop:
            site_result["status"] = "SKIP_NO_GSC_PROPERTY"
            save(result)
            print(f"SKIP {domain}: no accessible GSC property")
            continue

        try:
            posts = fetch_private_posts(site_url, password)
        except Exception as e:
            site_result["status"] = "PRIVATE_FETCH_FAILED"
            site_result["error"] = str(e)
            save(result)
            print(f"FAIL {domain}: {e}")
            continue

        site_result["private_before"] = len(posts)
        print(f"\n=== {domain}: private {len(posts)} ===")

        for post in posts:
            url = post.get("link")
            item = {
                "id": post.get("id"),
                "url": url,
                "slug": post.get("slug"),
                "title": title_of(post),
                "decision": None,
            }

            if not url:
                item["decision"] = "KEEP_PRIVATE_UNCERTAIN_NO_URL"
                site_result["kept_private_uncertain"] += 1
                site_result["items"].append(item)
                save(result)
                continue

            inspection = inspect_url(token, prop, url)
            item["inspection"] = inspection

            if not inspection.get("ok"):
                item["decision"] = "KEEP_PRIVATE_UNCERTAIN"
                site_result["kept_private_uncertain"] += 1
                print(f"KEEP uncertain {domain} #{post['id']}: {inspection.get('error')}")
            elif inspection.get("verdict") == "PASS":
                ok, code, detail = publish(site_url, password, post["id"])
                if ok:
                    item["decision"] = "RESTORED_PUBLISH_INDEXED"
                    site_result["restored_indexed"] += 1
                    print(f"RESTORE indexed {domain} #{post['id']} {item['title'][:80]}")
                else:
                    item["decision"] = "RESTORE_FAILED"
                    item["publish_http"] = code
                    item["publish_error"] = detail
                    site_result["publish_failed"] += 1
                    print(f"RESTORE FAIL {domain} #{post['id']} HTTP {code}")
            else:
                item["decision"] = "KEEP_PRIVATE_UNINDEXED"
                site_result["kept_private_unindexed"] += 1

            site_result["items"].append(item)
            save(result)
            time.sleep(1.05)

        site_result["private_after_expected"] = max(
            site_result["private_before"] - site_result["restored_indexed"], 0
        )
        site_result["status"] = "OK"
        save(result)

    sites = list(result["sites"].values())
    result["totals"] = {
        "sites_total": len(sites),
        "sites_ok": sum(1 for x in sites if x.get("status") == "OK"),
        "sites_skipped_or_failed": sum(1 for x in sites if x.get("status") != "OK"),
        "private_before": sum(x.get("private_before", 0) for x in sites),
        "restored_indexed": sum(x.get("restored_indexed", 0) for x in sites),
        "kept_private_unindexed": sum(x.get("kept_private_unindexed", 0) for x in sites),
        "kept_private_uncertain": sum(x.get("kept_private_uncertain", 0) for x in sites),
        "publish_failed": sum(x.get("publish_failed", 0) for x in sites),
    }
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    save(result)
    print("\n=== TOTALS ===")
    print(json.dumps(result["totals"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
