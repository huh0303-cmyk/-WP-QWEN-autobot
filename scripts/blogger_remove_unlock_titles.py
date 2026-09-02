#!/usr/bin/env python3
"""Remove Unlock-family clichés from all Blogger titles without changing body/status."""
from __future__ import annotations
import html
import json
import os
import re
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(r"(?i)\bunlock(?:s|ed|ing)?\b")


def cleaned_title(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", "", value or ""))
    value = PATTERN.sub("", value)
    value = re.sub(r"\s+([:;,.!?])", r"\1", value)
    value = re.sub(r"^\s*[:;,.!?\-–—]+\s*", "", value)
    value = re.sub(r"\s{2,}", " ", value).strip(" -–—:;")
    return value


def token() -> str:
    response = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=25)
    response.raise_for_status()
    return response.json()["access_token"]


def main() -> int:
    apply_changes = os.environ.get("APPLY_CHANGES", "true").lower() == "true"
    registry = json.loads((ROOT / "config/automation_hub_sites.json").read_text(encoding="utf-8"))
    sites = [row for row in registry["sites"] if row.get("platform") == "blogger" and row.get("destination_id")]
    headers = {"Authorization": f"Bearer {token()}"}
    found = changed = 0
    results = []
    for site in sites:
        blog_id = str(site["destination_id"])
        page_token = None
        while True:
            params = {"maxResults": 500, "fetchBodies": "false", "view": "ADMIN"}
            if page_token:
                params["pageToken"] = page_token
            response = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts",
                                    headers=headers, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            for post in payload.get("items", []):
                old = post.get("title", "")
                if not PATTERN.search(old):
                    continue
                found += 1
                new = cleaned_title(old)
                if not new or PATTERN.search(new):
                    raise RuntimeError(f"unsafe replacement for {blog_id}/{post.get('id')}: {old!r}")
                if apply_changes:
                    patched = requests.patch(
                        f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{post['id']}",
                        headers={**headers, "Content-Type": "application/json"}, json={"title": new}, timeout=30)
                    patched.raise_for_status()
                    changed += 1
                results.append({"site_id": site["site_id"], "blog_id": blog_id, "post_id": post["id"],
                                "status": post.get("status"), "old_title": old, "new_title": new,
                                "changed": apply_changes})
            page_token = payload.get("nextPageToken")
            if not page_token:
                break
    print(json.dumps({"blogs_scanned": len(sites), "found": found, "changed": changed, "items": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
