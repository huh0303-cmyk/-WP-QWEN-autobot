#!/usr/bin/env python3
"""Unified GSC ranking evidence for WP25 + Blogspot33.

This is the canonical statistics source for the London Project blog ranking.
It intentionally excludes WordPress visitor widgets, custom visitor APIs,
Blogger Stats widgets, GA4 traffic, and platform counters from the unified
ranking. GSC Search Analytics data is requested with dataState=final, and
the latest returned confirmed date is used consistently per site.
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
            "scope": "https://www.googleapis.com/auth/webmasters.readonly",
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


def query_site(headers: dict[str, str], site: str, prop: str | None, end: dt.date) -> dict:
    result = {
        "site": site,
        "property": prop,
        "status": "ACCESS_UNAVAILABLE" if not prop else "NO_DATA",
        "date": None,
        "clicks": None,
        "delta": None,
        "impressions": None,
        "ctr": None,
        "position": None,
        "previous_date": None,
    }
    if not prop:
        return result

    start = end - dt.timedelta(days=30)
    endpoint = (
        "https://www.googleapis.com/webmasters/v3/sites/"
        + quote(prop, safe="")
        + "/searchAnalytics/query"
    )
    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": ["date"],
        "rowLimit": 100,
        "dataState": "final",
    }
    try:
        response = requests.post(endpoint, headers=headers, json=body, timeout=20)
        if response.status_code != 200:
            result["status"] = f"QUERY_ERROR_{response.status_code}"
            return result
        rows = sorted(response.json().get("rows", []), key=lambda row: row["keys"][0])
        if not rows:
            return result
        latest = rows[-1]
        previous = rows[-2] if len(rows) > 1 else None
        latest_clicks = latest.get("clicks", 0)
        previous_clicks = previous.get("clicks", 0) if previous else None
        result.update(
            status="OK",
            date=latest["keys"][0],
            clicks=latest_clicks,
            delta=(latest_clicks - previous_clicks) if previous_clicks is not None else None,
            impressions=latest.get("impressions", 0),
            ctr=round(latest.get("ctr", 0) * 100, 2),
            position=round(latest.get("position", 0), 1),
            previous_date=previous["keys"][0] if previous else None,
        )
    except Exception as exc:
        result["status"] = f"ERROR_{type(exc).__name__}"
    return result


def main() -> None:
    now = dt.datetime.now(dt.timezone.utc)
    end = now.astimezone(KST).date() - dt.timedelta(days=3)
    token = token_from_service_account()
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    entries = requests.get(
        "https://www.googleapis.com/webmasters/v3/sites",
        headers=headers,
        timeout=20,
    ).json().get("siteEntry", [])
    properties = {
        entry["siteUrl"]
        for entry in entries
        if entry.get("permissionLevel") != "siteUnverifiedUser"
    }

    portfolio = json.loads(
        (ROOT / "config" / "blogger_portfolio.json").read_text(encoding="utf-8")
    )
    blogspot33 = [channel["blogspot"].rstrip("/") for channel in portfolio["channels"]]
    targets = [("wordpress", site) for site in WP25] + [
        ("blogspot", site) for site in blogspot33
    ]

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
        "schema": 2,
        "metric": "gsc_clicks",
        "metric_label": "GSC 클릭수",
        "delta_label": "직전 확정 GSC 날짜 대비",
        "confirmed_date": end.isoformat(),
        "generated_at": now.isoformat(),
        "timezone": "Asia/Seoul",
        "policy": (
            "WP25 + Blogspot33 unified ranking uses only Google Search Console "
            "Search Analytics. Primary ranking metric is clicks. Impressions, "
            "CTR and average position are secondary. Visitor widgets, custom "
            "visitor APIs, GA4 and platform counters are excluded. "
            "ACCESS_UNAVAILABLE is never converted to zero."
        ),
        "counts": {
            "wordpress": len(WP25),
            "blogspot": len(blogspot33),
            "total": len(targets),
            "ok": sum(row["status"] == "OK" for row in results),
            "unavailable": sum(row["status"] != "OK" for row in results),
        },
        "records": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(OUT)
    print(
        f"GSC unified ranking: {len(results)} sites / "
        f"{payload['counts']['ok']} OK / {payload['counts']['unavailable']} unavailable / "
        f"confirmed {end.isoformat()}"
    )


if __name__ == "__main__":
    main()
