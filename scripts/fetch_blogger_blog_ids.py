#!/usr/bin/env python3
"""After a human manually creates a Blogspot blog in the Blogger UI (the one
step Blogger's API cannot do - Blogs is read-only), run this to pick up its
blog ID automatically instead of hunting for it by hand.

For every channel in config/blogger_portfolio.json not yet EXISTING/CREATED,
calls Blogger's blogs.getByUrl. If the blog now exists, records its id as
destination_id and flips status to EXISTING. Then regenerates
config/content_engine_profiles.json so automation picks the site up on the
next run - no manual JSON editing needed.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_PATH = ROOT / "config" / "blogger_portfolio.json"


def _access_token() -> str:
    refresh_token = os.environ.get("BLOGGER_GOOGLE_REFRESH_TOKEN", "")
    client_id = os.environ.get("BLOGGER_GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("BLOGGER_GOOGLE_CLIENT_SECRET", "")
    if not all((refresh_token, client_id, client_secret)):
        raise SystemExit("BLOGGER_GOOGLE_REFRESH_TOKEN / _CLIENT_ID / _CLIENT_SECRET are required")
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={"client_id": client_id, "client_secret": client_secret, "refresh_token": refresh_token, "grant_type": "refresh_token"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def main() -> int:
    token = _access_token()
    data = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
    found, still_missing = [], []
    for channel in data["channels"]:
        if channel["status"] in {"EXISTING", "CREATED"} and channel.get("destination_id"):
            continue
        if channel["status"] == "CONFLICT":
            still_missing.append((channel["order"], channel["title"], "CONFLICT - needs a different address, see docs"))
            continue
        response = requests.get(
            "https://www.googleapis.com/blogger/v3/blogs/byurl",
            params={"url": channel["blogspot"]},
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        if response.status_code == 200:
            blog_id = response.json()["id"]
            channel["destination_id"] = blog_id
            channel["status"] = "EXISTING"
            found.append((channel["order"], channel["title"], blog_id))
        else:
            still_missing.append((channel["order"], channel["title"], "not created yet"))

    PORTFOLIO_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if found:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_content_engine_profiles.py")], check=True)

    print(json.dumps({
        "newly_wired": [{"order": o, "title": t, "blog_id": b} for o, t, b in found],
        "still_missing": [{"order": o, "title": t, "reason": r} for o, t, r in still_missing],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
