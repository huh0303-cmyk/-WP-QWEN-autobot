#!/usr/bin/env python3
"""Verify Blogger OAuth against every enabled destination in the 27-site registry."""
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


def main():
    profile = os.environ.get("AUTH_PROFILE", "")
    token = _access_token(profile)
    if not token:
        raise SystemExit("Blogger OAuth 자격증명이 없습니다.")
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
        "ok": len(configured) == 27 and not missing and not mismatched,
        "configured_count": len(configured), "oauth_visible_count": len(blogs),
        "matched_count": len(configured) - len(missing) - len(mismatched),
        "missing": missing, "url_mismatches": mismatched,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ok"]:
        raise SystemExit("BLOGGER_27_OAUTH_VERIFY_FAILED")
    print("BLOGGER_27_OAUTH_VERIFY_SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
