#!/usr/bin/env python3
"""Unified GSC ranking evidence for WP25 + Blogspot33.

This is the canonical statistics source for the London Project blog ranking.
The only targets are WP25 + Blogspot33. Property access is derived from the
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

WP25 = [
    "https://k-health365.com",
    "https://koreamedicaltour.com",
    "https://koreainvest365.com",
    "https://ki-korea.com",
    "https://koreainsurance365.com",
    "https://kfinance365.com",
    "https://koreataxnlaw.com",
    "https://koreacrypto365.com",
    "https://krealestate365.com",
    "https://ktech365.com",
    "https://kskin365.com",
    "https://oliveyoungkorea.com",
    "https://kworld365.com",
    "https://k-trip365.com",
    "https://k-visa365.com",
    "https://koreawedding365.com",
    "https://kstudy365.com",
    "https://studyinkorea365.com",
    "https://kieca-korea.org",
    "https://ksa-korea.org",
    "https://sis-korea.com",
    "https://jobkorea365.com",
    "https://jobinkorea365.com",
    "https://jobkoreaglobal.com",
    "https://korea365.org",
]


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


def query_day(headers: dict[str, str], prop: str, day: dt.date) -> dict | None:
    endpoint = (
        "https://www.googleapis.com/webmasters/v3/sites/"
        + quote(prop, safe="")
        + "/searchAnalytics/query"
    )
    body = {
        "startDate": day.isoformat(),
        "endDate": day.isoformat(),
        "dimensions": ["date"],
        "rowLimit": 10,
        "dataState": "final",
    }
    response = requests.post(endpoint, headers=headers, json=body, timeout=20)
    if response.status_code != 200:
        raise requests.HTTPError(f"GSC HTTP {response.status_code}", response=response)
    rows = response.json().get("rows", [])
    return rows[0] if rows else None


def query_site(headers: dict[str, str], site: str, prop: str | None, end: dt.date) -> dict:
    result = {
        "site": site,
        "property": prop,
        "status": "PROPERTY_NOT_AVAILABLE" if not prop else "NO_DATA",
        "requested_date": end.isoformat(),
        "date": None,
        "clicks": None,
        "delta": None,
        "impressions": None,
        "ctr": None,
        "position": None,
        "previous_date": (end - dt.timedelta(days=1)).isoformat(),
    }
    if not prop:
        return result
    try:
        current = query_day(headers, prop, end)
        previous = query_day(headers, prop, end - dt.timedelta(days=1))
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
    portfolio = json.loads(
        (ROOT / "config" / "blogger_portfolio.json").read_text(encoding="utf-8")
    )
    blogspot33 = [channel["blogspot"].rstrip("/") for channel in portfolio["channels"]]
    targets = [("wordpress", site) for site in WP25] + [
        ("blogspot", site) for site in blogspot33
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
    for _, site in targets:
        if property_for(site, properties):
            continue
        candidate = site.rstrip("/") + "/"
        add_url = "https://www.googleapis.com/webmasters/v3/sites/" + quote(candidate, safe="")
        try:
            added = requests.put(add_url, headers=headers, timeout=20)
            if added.status_code in (200, 201, 204):
                properties.add(candidate)
                print("GSC_PROPERTY_ADDED=" + candidate)
            else:
                print(f"GSC_PROPERTY_ADD_FAILED={candidate} HTTP_{added.status_code}")
        except requests.RequestException as exc:
            print(f"GSC_PROPERTY_ADD_FAILED={candidate} {type(exc).__name__}")

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
        "metric_label": "GSC 클릭수",
        "delta_label": "직전 확정 GSC 날짜 대비",
        "confirmed_date": end.isoformat(),
        "requested_reporting_date": end.isoformat(),
        "property_source": "live Google Search Console sites.list only",
        "generated_at": now.isoformat(),
        "timezone": "Asia/Seoul",
        "policy": (
            "WP25 + Blogspot33 unified ranking uses only Google Search Console "
            "Search Analytics. Primary ranking metric is clicks. Impressions, "
            "CTR and average position are secondary. Visitor widgets, custom "
            "visitor APIs, GA4 and platform counters are excluded. "
            "Only live properties visible to the configured service account are used. "
            "All sites query the exact same reporting date and immediately prior calendar day. "
            "NO_DATA, missing properties and access errors remain null and are never converted to zero."
        ),
        "counts": {
            "wordpress": len(WP25),
            "blogspot": len(blogspot33),
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
