"""Create a read-only, checksummed Blogger 33 recovery snapshot.

The Blogger v3 API exposes posts, pages and blog metadata but not the raw theme
template. This backup therefore protects all API-visible publishing content and
records that limitation explicitly in the manifest.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "blogger-33-backup"


def access_token() -> str:
    response = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def collect(url: str, headers: dict[str, str], params: dict | None = None) -> list[dict]:
    items, token = [], None
    while True:
        query = dict(params or {})
        if token:
            query["pageToken"] = token
        response = requests.get(url, headers=headers, params=query, timeout=60)
        response.raise_for_status()
        payload = response.json()
        items.extend(payload.get("items", []))
        token = payload.get("nextPageToken")
        if not token:
            return items


def main() -> int:
    profiles = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    sites = [p for p in profiles if p.get("blogspot", {}).get("ready_for_automation")]
    if len(sites) != 33:
        raise SystemExit(f"scope guard failed: expected 33 sites, got {len(sites)}")
    OUT.mkdir(parents=True, exist_ok=True)
    headers = {"Authorization": "Bearer " + access_token()}
    records = []
    for profile in sites:
        key = profile["site_key"]
        blog_id = str(profile["blogspot"]["destination_id"])
        base = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}"
        meta_response = requests.get(base, headers=headers, params={"view": "ADMIN"}, timeout=30)
        meta_response.raise_for_status()
        snapshot = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "site_key": key,
            "blog": meta_response.json(),
            "posts": collect(base + "/posts", headers, {
                "view": "ADMIN", "fetchBodies": "true", "fetchImages": "true", "maxResults": 500,
                "status": ["live", "draft", "scheduled"],
            }),
            "pages": collect(base + "/pages", headers, {
                "view": "ADMIN", "fetchBodies": "true", "maxResults": 50,
            }),
        }
        raw = (json.dumps(snapshot, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        filename = key + ".json.gz"
        path = OUT / filename
        with gzip.open(path, "wb", compresslevel=9) as handle:
            handle.write(raw)
        with gzip.open(path, "rb") as handle:
            restored = json.load(handle)
        if str(restored.get("blog", {}).get("id", "")) != blog_id:
            raise RuntimeError(f"restore rehearsal failed for {key}")
        records.append({
            "site_key": key, "blog_id": blog_id, "url": profile["blogspot"]["url"],
            "posts": len(snapshot["posts"]), "pages": len(snapshot["pages"]),
            "file": filename, "sha256_uncompressed": hashlib.sha256(raw).hexdigest(),
            "restore_rehearsal": "PASS",
        })
        print(f"backed up {key}: posts={len(snapshot['posts'])} pages={len(snapshot['pages'])}")
    manifest = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "configured_total": len(sites), "completed_total": len(records),
        "restore_rehearsal": "PASS" if len(records) == 33 else "FAIL",
        "coverage": "Blogger API-visible blog metadata, posts and pages",
        "known_limit": "Blogger v3 does not expose the raw theme template; theme export remains a separate Blogger UI operation.",
        "sites": records,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if len(records) != 33:
        raise SystemExit("incomplete Blogger backup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
