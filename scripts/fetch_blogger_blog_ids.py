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
        return ""
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={"client_id": client_id, "client_secret": client_secret, "refresh_token": refresh_token, "grant_type": "refresh_token"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def _owned_blogs() -> dict[str, str]:
    """Return exact URL -> ID mappings for blogs owned by the OAuth account.

    A public blogs.getByUrl lookup is not sufficient: it can return a blog
    owned by someone else when a requested address is unavailable.  Wiring a
    draft destination therefore fails closed unless the address appears in
    users/self/blogs for the authenticated account.
    """
    token = _access_token()
    if not token:
        raise SystemExit("Blogger OAuth credential is required to verify blog ownership")
    response = requests.get(
        "https://www.googleapis.com/blogger/v3/users/self/blogs",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return {
        str(item.get("url", "")).rstrip("/").lower(): str(item.get("id", ""))
        for item in response.json().get("items", [])
        if item.get("url") and item.get("id")
    }


def main() -> int:
    owned = _owned_blogs()
    data = json.loads(PORTFOLIO_PATH.read_text(encoding="utf-8"))
    found, still_missing = [], []
    for channel in data["channels"]:
        if channel["status"] in {"EXISTING", "CREATED"} and channel.get("destination_id"):
            continue
        if channel["status"] == "CONFLICT":
            still_missing.append((channel["order"], channel["title"], "CONFLICT - needs a different address, see docs"))
            continue
        target_url = str(channel["blogspot"]).rstrip("/").lower()
        blog_id = owned.get(target_url)
        if blog_id:
            channel["destination_id"] = blog_id
            channel["status"] = "EXISTING"
            found.append((channel["order"], channel["title"], blog_id))
        else:
            still_missing.append((channel["order"], channel["title"], "not present in authenticated owner's blog list"))

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
