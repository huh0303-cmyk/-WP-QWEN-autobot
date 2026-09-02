#!/usr/bin/env python3
"""Submit and verify the canonical k-health365.com sitemap in Google Search Console."""
import json
import os
import time
from urllib.parse import quote

import jwt
import requests


PROPERTY = "sc-domain:k-health365.com"
SITEMAP = "https://k-health365.com/sitemap_index.xml"


def access_token(key: dict) -> str:
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
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def main() -> int:
    raw = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise SystemExit("GSC_SERVICE_ACCOUNT_JSON is missing")
    token = access_token(json.loads(raw))
    headers = {"Authorization": f"Bearer {token}"}
    base = "https://www.googleapis.com/webmasters/v3"
    site = quote(PROPERTY, safe="")
    feed = quote(SITEMAP, safe="")

    submitted = requests.put(
        f"{base}/sites/{site}/sitemaps/{feed}", headers=headers, timeout=30
    )
    if submitted.status_code not in (200, 204):
        raise SystemExit(f"submit failed: HTTP {submitted.status_code} {submitted.text[:500]}")

    verified = requests.get(
        f"{base}/sites/{site}/sitemaps/{feed}", headers=headers, timeout=30
    verified.raise_for_status()
    data = verified.json()
    print(json.dumps({
        "property": PROPERTY,
        "sitemap": SITEMAP,
        "submitted": True,
        "isPending": data.get("isPending"),
        "isSitemapsIndex": data.get("isSitemapsIndex"),
        "lastSubmitted": data.get("lastSubmitted"),
        "lastDownloaded": data.get("lastDownloaded"),
        "errors": data.get("errors"),
        "warnings": data.get("warnings"),
        "contents": data.get("contents", []),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
