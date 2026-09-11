#!/usr/bin/env python3
"""One-off, user-approved: backfill the visitor-counter badge (added for all
FUTURE posts in PR #91) onto every EXISTING live post across all 33 Blogger
blogs, so the counter is visible immediately instead of only on new posts.
Uses the same page_id convention ("blogger_<site_key>") as the future-post
code so counts accumulate together per blog."""
from __future__ import annotations
import json, os, re, sys, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/blogger-visitor-counter-backfill.json"
BADGE_MARK = "visitor-badge.laobi.icu"


def visitor_counter_html(page_id: str) -> str:
    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "-", page_id)
    return (
        '<p style="text-align:center;margin-top:24px;">'
        f'<img src="https://visitor-badge.laobi.icu/badge?page_id={safe_id}" '
        'alt="visitor count" loading="lazy" /></p>'
    )


def access_token():
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
            "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def all_live_posts(endpoint, headers):
    page_token = None
    while True:
        params = {"status": "live", "view": "ADMIN", "fetchBodies": "true", "maxResults": 500}
        if page_token:
            params["pageToken"] = page_token
        for attempt in range(4):
            response = requests.get(endpoint, headers=headers, params=params, timeout=30)
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2 ** attempt * 3)
                continue
            response.raise_for_status()
            break
        payload = response.json()
        yield from payload.get("items", [])
        page_token = payload.get("nextPageToken")
        if not page_token:
            break


def main():
    profiles = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    auth = {"Authorization": f"Bearer {access_token()}"}
    rows = []
    for p in profiles:
        blog = p.get("blogspot") or {}
        if not blog.get("ready_for_automation"):
            continue
        site_key = p["site_key"]
        page_id = f"blogger_{site_key}"
        badge = visitor_counter_html(page_id)
        blog_id = str(blog["destination_id"])
        endpoint = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts"
        try:
            for post in all_live_posts(endpoint, auth):
                content = post.get("content", "")
                row = {"site": site_key, "blog_id": blog_id, "post_id": str(post["id"]),
                       "url": post.get("url", ""), "status": "skipped_already_has_badge"}
                if BADGE_MARK not in content:
                    new_content = content + badge
                    for attempt in range(4):
                        patch = requests.patch(
                            f"{endpoint}/{post['id']}", headers=auth,
                            params={"revert": "false"}, json={"content": new_content}, timeout=30,
                        )
                        if patch.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                            time.sleep(2 ** attempt * 3)
                            continue
                        patch.raise_for_status()
                        break
                    row["status"] = "patched"
                rows.append(row)
                OUT.parent.mkdir(parents=True, exist_ok=True)
                OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
                time.sleep(0.3)
        except Exception as e:
            rows.append({"site": site_key, "blog_id": blog_id, "status": "failed", "error": str(e)[:400]})
            OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
            continue

    patched = sum(1 for r in rows if r["status"] == "patched")
    skipped = sum(1 for r in rows if r["status"] == "skipped_already_has_badge")
    failed_sites = sorted({r["site"] for r in rows if r["status"] == "failed"})
    print(json.dumps({"total_rows": len(rows), "patched": patched, "already_had_badge": skipped,
                       "failed_sites": failed_sites}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
