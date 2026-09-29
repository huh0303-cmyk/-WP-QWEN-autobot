from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
RECEIPTS = ROOT / "data" / "social_publication_receipts.json"
KST = timezone(timedelta(hours=9))
GRAPH = "https://graph.facebook.com/v21.0"


def api(method: str, endpoint: str, token: str, **fields) -> dict:
    response = requests.request(
        method,
        endpoint,
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
        **({"params": fields} if method == "GET" else {"data": fields}),
    )
    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError(f"Meta API returned invalid JSON (HTTP {response.status_code})") from None
    if not response.ok or payload.get("error"):
        error = payload.get("error") or {}
        raise RuntimeError(
            f"Meta API failed (HTTP {response.status_code}, code={error.get('code')}, "
            f"subcode={error.get('error_subcode')})"
        )
    return payload


def publish_instagram(spec: dict) -> dict:
    token = os.environ.get("IG_ACCESS_TOKEN", "")
    user_id = os.environ.get("IG_USER_ID", "")
    if not token or not user_id:
        raise RuntimeError("Instagram API credentials are not configured")
    recent = api(
        "GET",
        f"{GRAPH}/{user_id}/media",
        token,
        fields="id,caption,permalink,timestamp",
        limit="25",
    )
    existing = next(
        (row for row in recent.get("data", []) if row.get("caption") == spec["instagram"]["caption"]),
        None,
    )
    if existing:
        return {
            "platform": "Instagram",
            "role": spec["role"],
            "handle": spec["instagram"]["handle"],
            "post_id": existing["id"],
            "url": existing.get("permalink", ""),
            "reconciled": True,
        }
    container = api(
        "POST",
        f"{GRAPH}/{user_id}/media",
        token,
        image_url=spec["image_url"],
        caption=spec["instagram"]["caption"],
    )["id"]
    for _ in range(30):
        status = api("GET", f"{GRAPH}/{container}", token, fields="status_code").get("status_code")
        if status == "FINISHED":
            break
        if status not in {"IN_PROGRESS", "PUBLISHED"}:
            raise RuntimeError(f"Instagram container stopped with status {status}")
        time.sleep(5)
    else:
        raise RuntimeError("Instagram container did not finish in time")
    media_id = api("POST", f"{GRAPH}/{user_id}/media_publish", token, creation_id=container)["id"]
    permalink = api("GET", f"{GRAPH}/{media_id}", token, fields="permalink").get("permalink", "")
    return {
        "platform": "Instagram",
        "role": spec["role"],
        "handle": spec["instagram"]["handle"],
        "post_id": media_id,
        "url": permalink,
    }


def publish_facebook(spec: dict) -> dict:
    token = os.environ.get("FB_PAGE_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("Facebook Page API credential is not configured")
    page = api("GET", f"{GRAPH}/me", token, fields="id,name")
    recent = api(
        "GET",
        f"{GRAPH}/{page['id']}/feed",
        token,
        fields="id,message,permalink_url,created_time",
        limit="25",
    )
    existing = next(
        (row for row in recent.get("data", []) if row.get("message") == spec["facebook"]["caption"]),
        None,
    )
    if existing:
        return {
            "platform": "Facebook",
            "role": spec["role"],
            "handle": "",
            "account_id": page["id"],
            "account_name": page.get("name", ""),
            "post_id": existing["id"],
            "url": existing.get("permalink_url", ""),
            "reconciled": True,
        }
    result = api(
        "POST",
        f"{GRAPH}/{page['id']}/photos",
        token,
        url=spec["image_url"],
        caption=spec["facebook"]["caption"],
        published="true",
    )
    post_id = result.get("post_id") or result.get("id")
    details = api("GET", f"{GRAPH}/{post_id}", token, fields="permalink_url")
    return {
        "platform": "Facebook",
        "role": spec["role"],
        "handle": "",
        "account_id": page["id"],
        "account_name": page.get("name", ""),
        "post_id": post_id,
        "url": details.get("permalink_url", ""),
    }


def save_receipts(content_id: str, rows: list[dict]) -> None:
    try:
        payload = json.loads(RECEIPTS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = {"publications": []}
    now = datetime.now(KST).isoformat()
    publications = payload.setdefault("publications", [])
    for row in rows:
        row["content_id"] = content_id
        row["published_at"] = now
        publications[:] = [
            old for old in publications
            if not (old.get("content_id") == content_id and old.get("platform") == row.get("platform"))
        ]
        publications.append(row)
    payload["updated_at"] = now
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    RECEIPTS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec")
    args = parser.parse_args()
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    rows = []
    for publisher in (publish_instagram, publish_facebook):
        rows.append(publisher(spec))
        save_receipts(spec["content_id"], rows)
    print(json.dumps({"published": rows}, ensure_ascii=False))


if __name__ == "__main__":
    main()
