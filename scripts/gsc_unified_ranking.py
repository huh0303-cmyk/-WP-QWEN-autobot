#!/usr/bin/env python3
"""Unified GSC ranking evidence for WP23 + Blogspot31.

This is the canonical statistics source for the London Project blog ranking.
The only targets are WP23 + Blogspot31. Property access is derived from the
live Search Console sites.list response; saved inventory is never treated as
proof of access. Every site is queried for the same fixed KST reporting date.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
KST = dt.timezone(dt.timedelta(hours=9))
OUT = ROOT / "data" / "gsc_unified_ranking.json"

INACTIVE_BLOGSPOT_URLS = {
    "https://jobkorea365.blogspot.com",
    "https://k-health365-edu.blogspot.com",
}


def load_active_targets():
    registry = json.loads((ROOT / "config" / "automation_hub_sites.json").read_text(encoding="utf-8"))
    wordpress = [
        str(item.get("url") or "").rstrip("/")
        for item in registry.get("sites", [])
        if item.get("platform") == "wordpress"
        and item.get("enabled") is not False
        and item.get("retired") is not True
        and item.get("url")
    ]
    portfolio = json.loads((ROOT / "config" / "blogger_portfolio.json").read_text(encoding="utf-8"))
    blogspot = [
        str(item.get("blogspot") or "").rstrip("/")
        for item in portfolio.get("channels", [])
        if item.get("blogspot")
        and str(item.get("blogspot") or "").rstrip("/") not in INACTIVE_BLOGSPOT_URLS
    ]
    wordpress = list(dict.fromkeys(wordpress))
    blogspot = list(dict.fromkeys(blogspot))
    if len(wordpress) != 23:
        raise RuntimeError(f"Expected 23 active WordPress targets, found {len(wordpress)}")
    if len(blogspot) != 31:
        raise RuntimeError(f"Expected 31 active Blogspot targets, found {len(blogspot)}")
    return wordpress, blogspot


WP23, BLOGSPOT31 = load_active_targets()


def token_from_service_account() -> str:
    raw = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise RuntimeError("GSC_SERVICE_ACCOUNT_JSON is missing")
    import jwt
    key = json.loads(raw)
    now = int(time.time())
    assertion = jwt.encode(
        {
            "iss": key["client_email"],
            "scope": "https://www.googleapis.com/auth/webmasters",
            "aud": "https://oauth2.googleapis.com/token",
            "iat": now,
            "exp": now + 3600,
        },
        key["private_key"],
        algorithm="RS256",
    )
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def property_for(url: str, properties: set[str]) -> str | None:
    exact = url.rstrip("/") + "/"
    if exact in properties:
        return exact
    host = url.split("://", 1)[-1].split("/", 1)[0].lower()
    matches = [
        p for p in properties
        if p.startswith("sc-domain:")
        and (host == p[10:].lower() or host.endswith("." + p[10:].lower()))
    ]
    return max(matches, key=len) if matches else None


def query_range(headers: dict[str, str], prop: str, start: dt.date, end: dt.date) -> dict | None:
    endpoint = (
        "https://www.googleapis.com/webmasters/v3/sites/"
        + quote(prop, safe="")
        + "/searchAnalytics/query"
    )
    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "rowLimit": 1,
        "dataState": "final",
    }
    response = requests.post(endpoint, headers=headers, json=body, timeout=20)
    if response.status_code != 200:
        raise requests.HTTPError(f"GSC HTTP {response.status_code}", response=response)
    rows = response.json().get("rows", [])
    return rows[0] if rows else None


def sitemap_coverage(headers: dict[str, str], prop: str) -> dict:
    """Collect valid sitemap submission counts; GSC Page Indexing totals are UI-only.

    Search Console documents contents[].indexed as deprecated. Do not read it
    or present it as the Page Indexing report total. That aggregate is not
    exposed by the supported Search Console API.
    """
    base = "https://www.googleapis.com/webmasters/v3/sites/" + quote(prop, safe="")
    result = {
        "indexed": None,
        "submitted": None,
        "unindexed": None,
        "index_rate": None,
        "index_status": "PAGE_INDEXING_REPORT_UI_ONLY",
        "index_checked_at": dt.datetime.now(KST).isoformat(),
        "sitemap_count": 0,
    }
    try:
        response = requests.get(base + "/sitemaps", headers=headers, timeout=20)
        if response.status_code != 200:
            result["index_status"] = f"SITEMAPS_HTTP_{response.status_code}"
            return result
        sitemaps = response.json().get("sitemap", []) or []
        result["sitemap_count"] = len(sitemaps)
        if not sitemaps:
            result["index_status"] = "NO_SITEMAPS_SUBMITTED"
            return result
        submitted_total = 0
        found_submitted = False
        failed_details = 0
        seen = set()
        for sitemap in sitemaps:
            path = str(sitemap.get("path") or "").strip()
            if not path or path in seen:
                continue
            seen.add(path)
            detail = requests.get(
                base + "/sitemaps/" + quote(path, safe=""),
                headers=headers,
                timeout=20,
            )
            if detail.status_code != 200:
                failed_details += 1
                continue
            for content in detail.json().get("contents", []) or []:
                value = content.get("submitted")
                try:
                    submitted_total += int(str(value).replace(",", "").strip())
                    found_submitted = value is not None
                except (TypeError, ValueError):
                    pass
        result["submitted"] = submitted_total if found_submitted else None
        if failed_details:
            result["index_status"] = "PAGE_INDEXING_REPORT_UI_ONLY_PARTIAL_SITEMAPS"
        elif not found_submitted:
            result["index_status"] = "PAGE_INDEXING_REPORT_UI_ONLY"
        return result
    except (requests.RequestException, ValueError, TypeError) as exc:
        result["index_status"] = "SITEMAPS_API_ERROR_" + type(exc).__name__
        return result



def query_site(headers: dict[str, str], site: str, prop: str | None, end: dt.date) -> dict:
    start = end - dt.timedelta(days=6)
    previous_end = start - dt.timedelta(days=1)
    previous_start = previous_end - dt.timedelta(days=6)
    result = {
        "site": site,
        "property": prop,
        "status": "PROPERTY_NOT_AVAILABLE" if not prop else "NO_DATA",
        "indexed": None,
        "submitted": None,
        "unindexed": None,
        "index_rate": None,
        "index_status": "PROPERTY_NOT_AVAILABLE" if not prop else "NOT_CHECKED",
        "index_checked_at": None,
        "sitemap_count": 0,
        "requested_date": end.isoformat(),
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "previous_period_start": previous_start.isoformat(),
        "previous_period_end": previous_end.isoformat(),
        "date": None,
        "clicks": None,
        "delta": None,
        "impressions": None,
        "ctr": None,
        "position": None,
        "previous_date": previous_end.isoformat(),
    }
    if not prop:
        return result
    result.update(sitemap_coverage(headers, prop))
    try:
        current = query_range(headers, prop, start, end)
        previous = query_range(headers, prop, previous_start, previous_end)
        if current is None:
            result["status"] = "NO_DATA"
            return result
        clicks = current.get("clicks")
        previous_clicks = previous.get("clicks") if previous else None
        result.update(
            status="OK",
            date=end.isoformat(),
            clicks=clicks,
            delta=(clicks - previous_clicks) if clicks is not None and previous_clicks is not None else None,
            impressions=current.get("impressions"),
            ctr=round(current["ctr"] * 100, 2) if current.get("ctr") is not None else None,
            position=round(current["position"], 1) if current.get("position") is not None else None,
        )
    except requests.HTTPError as exc:
        result["status"] = f"QUERY_ERROR_{exc.response.status_code}" if exc.response is not None else "QUERY_ERROR"
    except Exception as exc:
        result["status"] = f"ERROR_{type(exc).__name__}"
    return result


def main() -> None:
    now = dt.datetime.now(dt.timezone.utc)
    end = now.astimezone(KST).date() - dt.timedelta(days=3)
    token = token_from_service_account()
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    targets = [("wordpress", site) for site in WP23] + [
        ("blogspot", site) for site in BLOGSPOT31
    ]

    # Use only properties visible to this same service account in live GSC.
    # The saved inventory can be stale or belong to another account; merging it
    # caused false property matches and 403s.
    site_list_response = requests.get(
        "https://www.googleapis.com/webmasters/v3/sites",
        headers=headers,
        timeout=20,
    )
    site_list_response.raise_for_status()
    entries = site_list_response.json().get("siteEntry", [])
    properties = {
        entry["siteUrl"]
        for entry in entries
        if entry.get("permissionLevel") != "siteUnverifiedUser"
    }
    print("GSC_SERVICE_ACCOUNT_EMAIL=" + json.loads(os.environ["GSC_SERVICE_ACCOUNT_JSON"])["client_email"])
    print(f"GSC_LIVE_PROPERTIES={len(properties)} TARGETS={len(targets)}")

    # Attempt to register target URL-prefix properties that are missing entirely.
    # GSC rejects properties the service account cannot verify; failures remain
    # visible and are not misrepresented as accessible.
    missing_targets = [
        (platform, site, site.rstrip("/") + "/")
        for platform, site in targets
        if not property_for(site, properties)
    ]

    def try_add_property(item):
        _, site, candidate = item
        add_url = "https://www.googleapis.com/webmasters/v3/sites/" + quote(candidate, safe="")
        try:
            added = requests.put(add_url, headers=headers, timeout=8)
            if added.status_code in (200, 201, 204):
                print("GSC_PROPERTY_ADDED=" + candidate)
                return candidate, "ADDED"
            print(f"GSC_PROPERTY_ADD_FAILED={candidate} HTTP_{added.status_code}")
            return candidate, f"HTTP_{added.status_code}"
        except requests.RequestException as exc:
            print(f"GSC_PROPERTY_ADD_FAILED={candidate} {type(exc).__name__}")
            return candidate, type(exc).__name__

    # Bound elapsed time by attempting registrations concurrently with short
    # timeouts rather than serially blocking on dozens of inaccessible sites.
    with ThreadPoolExecutor(max_workers=12) as add_pool:
        for candidate, status in add_pool.map(try_add_property, missing_targets):
            if status == "ADDED":
                properties.add(candidate)

    # Refresh live permissions after registration attempts.
    refreshed = requests.get(
        "https://www.googleapis.com/webmasters/v3/sites",
        headers=headers,
        timeout=20,
    )
    refreshed.raise_for_status()
    properties = {
        entry["siteUrl"]
        for entry in refreshed.json().get("siteEntry", [])
        if entry.get("permissionLevel") != "siteUnverifiedUser"
    }

    results = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {
            pool.submit(
                query_site,
                headers,
                site,
                property_for(site, properties),
                end,
            ): (platform, site)
            for platform, site in targets
        }
        for future in as_completed(futures):
            platform, _ = futures[future]
            row = future.result()
            row["platform"] = platform
            results.append(row)

    results.sort(
        key=lambda row: (
            row["clicks"] is None,
            -(row["clicks"] or 0),
            row["site"],
        )
    )
    payload = {
        "schema": 3,
        "metric": "gsc_clicks",
        "metric_label": "GSC 최근 7일 클릭수",
        "delta_label": "직전 7일 대비",
        "reporting_window_days": 7,
        "confirmed_date": end.isoformat(),
        "requested_reporting_date": end.isoformat(),
        "property_source": "live Google Search Console sites.list only",
        "generated_at": now.isoformat(),
        "timezone": "Asia/Seoul",
        "policy": (
            "WP23 + Blogspot31 unified ranking uses only Google Search Console "
            "Search Analytics. Primary ranking metric is clicks. Impressions, "
            "CTR and average position are secondary. Visitor widgets, custom "
            "visitor APIs, GA4 and platform counters are excluded. "
            "Only live properties visible to the configured service account are used. "
            "All sites query the same latest 7-day window and compare against the immediately preceding 7-day window. "
            "NO_DATA, missing properties and access errors remain null and are never converted to zero."
        ),
        "counts": {
            "wordpress": len(WP23),
            "blogspot": len(BLOGSPOT31),
            "total": len(targets),
            "ok": sum(row["status"] == "OK" for row in results),
            "unavailable": sum(row["status"] != "OK" for row in results),
            "property_not_available": sum(row["status"] == "PROPERTY_NOT_AVAILABLE" for row in results),
            "query_errors": sum(row["status"].startswith("QUERY_ERROR_") for row in results),
            "no_data": sum(row["status"] == "NO_DATA" for row in results),
        },
        "records": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(OUT)

    # Dedicated exact target-to-live-GSC-property audit; unrelated GSC properties
    # (subdomains, Naver, Tistory, feeds, etc.) are deliberately excluded.
    audit_path = ROOT / "data" / "gsc_target_property_audit.json"
    audit = {
        "schema": 1,
        "generated_at": dt.datetime.now(KST).isoformat(),
        "reporting_date": end.isoformat(),
        "source": "live Google Search Console sites.list after registration attempts",
        "counts": {
            "target_total": len(targets),
            "matched_property": sum(bool(row.get("property")) for row in results),
            "property_missing": sum(not row.get("property") for row in results),
            "query_ok": sum(row.get("status") == "OK" for row in results),
            "query_error": sum(str(row.get("status", "")).startswith("QUERY_ERROR_") for row in results),
        },
        "targets": [
            {
                "platform": row["platform"],
                "site": row["site"],
                "gsc_property": row.get("property"),
                "query_status": row.get("status"),
                "requested_date": row.get("requested_date"),
            }
            for row in results
        ],
    }
    audit_tmp = audit_path.with_suffix(".tmp")
    audit_tmp.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    audit_tmp.replace(audit_path)
    print(
        f"GSC unified ranking: {len(results)} sites / "
        f"{payload['counts']['ok']} OK / {payload['counts']['unavailable']} unavailable / "
        f"reporting date {end.isoformat()}"
    )


if __name__ == "__main__":
    main()
