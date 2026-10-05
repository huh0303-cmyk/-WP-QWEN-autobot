#!/usr/bin/env python3
"""Revert LIVE Blogger posts published on a given KST date to DRAFT (reversible, never deletes)."""
from __future__ import annotations
import json, os
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
DATE = os.environ.get("TARGET_DATE", "2026-09-21")
APPLY = os.environ.get("APPLY_CHANGES", "false").lower() == "true"


def token() -> str:
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=25)
    r.raise_for_status()
    return r.json()["access_token"]


def main() -> int:
    profiles = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))
    sites = [(row["site_key"], str(row["blogspot"]["destination_id"]))
             for row in profiles["profiles"] if row.get("blogspot", {}).get("destination_id")]
    h = {"Authorization": f"Bearer {token()}"}
    start, end = f"{DATE}T00:00:00+09:00", f"{DATE}T23:59:59+09:00"
    total = reverted = 0
    rows = []
    for key, blog_id in sites:
        page = None
        while True:
            params = {"maxResults": 500, "fetchBodies": "false", "status": "LIVE",
                      "startDate": start, "endDate": end}
            if page:
                params["pageToken"] = page
            r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts",
                             headers=h, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            for p in data.get("items", []):
                if not str(p.get("published", "")).startswith(DATE):
                    pass  # API window is authoritative; keep for logging
                total += 1
                ok = None
                if APPLY:
                    rv = requests.post(f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{p['id']}/revert",
                                       headers=h, timeout=30)
                    ok = rv.ok
                    reverted += int(ok)
                rows.append({"site": key, "post_id": p["id"], "published": p.get("published"),
                             "title": p.get("title"), "reverted": ok})
            page = data.get("nextPageToken")
            if not page:
                break
    print(json.dumps({"date": DATE, "apply": APPLY, "blogs": len(sites), "found": total,
                      "reverted": reverted, "items": rows}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
