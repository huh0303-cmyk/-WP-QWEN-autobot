#!/usr/bin/env python3
"""Synchronize WordPress post visibility to current GSC URL Inspection verdicts.

Exactly three sites are excluded: the AdSense-approved k-health365 site and the
two newspaper sites.  PASS posts are published, confirmed non-PASS posts are
made private, and API/permission/quota failures never change WordPress state.
"""
import json, os, socket, sys, time
from pathlib import Path

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_registry import ACTIVE_SITES  # noqa: E402

WP_USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
SITE_FILTER = os.getenv("SITE_FILTER", "").strip().lower()
PUBLISH_ONLY = os.getenv("PUBLISH_ONLY", "").strip() == "1"
OUT = Path(f"sync_gsc_publish_{SITE_FILTER}.json" if SITE_FILTER else
           "sync_24_sites_gsc_index_visibility_result.json")
EXCLUDED = {"k-health365.com", "koreanews365.com", "theseouljournal.com"}

_getaddrinfo = socket.getaddrinfo
socket.getaddrinfo = lambda host, port, family=0, type=0, proto=0, flags=0: _getaddrinfo(
    host, port, socket.AF_INET, type, proto, flags
)


def google_token():
    data = {
        "client_id": os.environ["GOOGLE_METRICS_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_METRICS_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_METRICS_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }
    r = requests.post("https://oauth2.googleapis.com/token", data=data, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def gsc_properties(token):
    r = requests.get("https://www.googleapis.com/webmasters/v3/sites",
        headers={"Authorization": f"Bearer {token}"}, timeout=30)
    r.raise_for_status()
    return {x["siteUrl"] for x in r.json().get("siteEntry", [])}


def property_for(site, properties):
    domain = site.removeprefix("https://").rstrip("/")
    for candidate in (f"sc-domain:{domain}", site.rstrip("/") + "/", site.rstrip("/")):
        if candidate in properties:
            return candidate


def all_posts(site, password):
    rows, page = [], 1
    while True:
        r = requests.get(f"{site}/wp-json/wp/v2/posts",
            auth=(WP_USER, password), params={"context":"edit", "status":"publish,private",
            "per_page":100, "page":page, "orderby":"id", "order":"asc",
            "_fields":"id,link,status,title"}, timeout=40)
        if r.status_code == 400 and "rest_post_invalid_page_number" in r.text:
            break
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return rows


def inspect(token, prop, url):
    for attempt in range(3):
        r = requests.post("https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
            headers={"Authorization":f"Bearer {token}", "Content-Type":"application/json"},
            json={"inspectionUrl":url, "siteUrl":prop}, timeout=35)
        if r.status_code == 200:
            x = r.json().get("inspectionResult", {}).get("indexStatusResult", {})
            return {"ok":True, "verdict":x.get("verdict"),
                "coverageState":x.get("coverageState"), "lastCrawlTime":x.get("lastCrawlTime")}
        if r.status_code == 429:
            time.sleep(8 * (attempt + 1)); continue
        return {"ok":False, "error":f"HTTP {r.status_code}: {r.text[:160]}"}
    return {"ok":False, "error":"quota retries exhausted"}


def set_status(site, password, post_id, status):
    r = requests.post(f"{site}/wp-json/wp/v2/posts/{post_id}", auth=(WP_USER,password),
        json={"status":status}, timeout=40)
    return r.status_code in (200,201), r.status_code, r.text[:160]


def save(payload):
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    if os.getenv("CONFIRM") != "SYNC-24-INDEXED-ONLY":
        raise SystemExit("exact CONFIRM=SYNC-24-INDEXED-ONLY required")
    token = google_token(); properties = gsc_properties(token)
    targets = [x for x in ACTIVE_SITES if x[0].removeprefix("https://").rstrip("/") not in EXCLUDED]
    if len(targets) != 24:
        raise SystemExit(f"scope guard failed: expected 24, got {len(targets)}")
    if SITE_FILTER:
        targets = [x for x in targets if x[0].removeprefix("https://").rstrip("/") == SITE_FILTER]
        if len(targets) != 1:
            raise SystemExit(f"site filter not in 24-site scope: {SITE_FILTER}")
    result = {"excluded":sorted(EXCLUDED), "sites":{}}
    for site, secret_name, _ in targets:
        site = site.rstrip("/"); domain = site.removeprefix("https://")
        password = os.getenv(secret_name, "").strip(); prop = property_for(site, properties)
        summary = {"property":prop, "published":0, "privated":0, "kept":0,
                   "uncertain":0, "failed":0, "items":[]}
        result["sites"][domain] = summary; save(result)
        if not password or not prop:
            summary["error"] = "missing WordPress secret" if not password else "missing GSC property"
            save(result); continue
        try:
            posts = all_posts(site, password)
        except Exception as exc:
            summary["error"] = f"inventory failed: {exc}"; save(result); continue
        summary["posts_checked"] = len(posts)
        for post in posts:
            evidence = inspect(token, prop, post["link"])
            desired = "publish" if evidence.get("ok") and evidence.get("verdict") == "PASS" else (
                post["status"] if evidence.get("ok") and PUBLISH_ONLY else
                ("private" if evidence.get("ok") else None))
            item = {"id":post["id"], "url":post["link"], "before":post["status"],
                    "desired":desired, "inspection":evidence}
            if desired is None:
                summary["uncertain"] += 1
            elif desired == post["status"]:
                summary["kept"] += 1
            else:
                ok, code, detail = set_status(site, password, post["id"], desired)
                if ok:
                    summary["published" if desired == "publish" else "privated"] += 1
                else:
                    summary["failed"] += 1; item.update({"http":code,"error":detail})
            summary["items"].append(item); save(result); time.sleep(1.05)
    result["totals"] = {k:sum(s.get(k,0) for s in result["sites"].values())
        for k in ("published","privated","kept","uncertain","failed")}
    save(result); print(json.dumps(result["totals"], ensure_ascii=False))


if __name__ == "__main__":
    main()
