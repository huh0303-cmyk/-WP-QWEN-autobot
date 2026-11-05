#!/usr/bin/env python3
"""Verify Blogger OAuth against every enabled destination in the 33-site registry."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from process_platform_queue import _access_token

REGISTRY_FILE = ROOT / "config" / "automation_hub_sites.json"
REPORT_FILE = ROOT / "blogger_connection_report.json"


def main():
    profile = os.environ.get("AUTH_PROFILE", "")
    token = _access_token(profile)
    if not token:
        raise SystemExit("Blogger OAuth 자격증명이 없습니다.")
    expected_client_id = os.environ.get("EXPECTED_GOOGLE_OAUTH_CLIENT_ID", "").strip()
    active_client_id = os.environ.get("BLOGGER_GOOGLE_CLIENT_ID", "").strip()
    if expected_client_id:
        matches = active_client_id == expected_client_id
        print("OAuth client matches downloaded desktop client: " + ("YES" if matches else "NO"))
        if not matches:
            raise SystemExit("OAuth client ID mismatch; do not replace GOOGLE_OAUTH_REFRESH_TOKEN.")
    # Print granted scope names only; never log access or refresh token values.
    scope_resp = requests.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"access_token": token}, timeout=20,
    )
    if scope_resp.status_code == 200:
        granted_scopes = set(scope_resp.json().get("scope", "").split())
        print("OAuth scope names: " + ", ".join(sorted(granted_scopes)))
        print("Blogger write scope: " + ("YES" if "https://www.googleapis.com/auth/blogger" in granted_scopes else "NO"))
    else:
        print(f"OAuth scope introspection unavailable: HTTP {scope_resp.status_code}")
    response = requests.get(
        "https://www.googleapis.com/blogger/v3/users/self/blogs",
        headers={"Authorization": f"Bearer {token}"}, timeout=30,
    )
    if response.status_code != 200:
        raise SystemExit(f"Blogger OAuth 확인 실패 HTTP {response.status_code}: {response.text[:500]}")
    blogs = [{"id": str(item.get("id", "")), "name": item.get("name", ""), "url": item.get("url", "")} for item in response.json().get("items", [])]
    owned = {row["id"]: row for row in blogs if row["id"]}
    configured = [row for row in json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))["sites"]
                  if row.get("platform") == "blogger" and row.get("enabled", True)]
    missing = [
        {"site_id": row["site_id"], "destination_id": str(row.get("destination_id", "")), "url": row["url"]}
        for row in configured if str(row.get("destination_id", "")) not in owned
    ]
    mismatched = [
        {"site_id": row["site_id"], "configured_url": row["url"],
         "oauth_url": owned[str(row["destination_id"])].get("url", "")}
        for row in configured if str(row.get("destination_id", "")) in owned
        and owned[str(row["destination_id"])].get("url", "").rstrip("/").lower()
        != row["url"].rstrip("/").lower()
    ]
    report = {
        "ok": len(configured) == 33 and not missing and not mismatched,
        "configured_count": len(configured), "oauth_visible_count": len(blogs),
        "matched_count": len(configured) - len(missing),
        "connected_count": len(configured) - len(missing),
        "missing": missing, "url_mismatches": mismatched,
        "matched_site_ids": [
            row["site_id"] for row in configured
            if str(row.get("destination_id", "")) in owned
        ],
    }
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ok"]:
        raise SystemExit("BLOGGER_33_OAUTH_VERIFY_FAILED")
    print("BLOGGER_33_OAUTH_VERIFY_SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
