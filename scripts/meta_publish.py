"""Instagram Reels and Threads publishing with a resumable local receipt.

Keep META_PUBLISH_STATE_DIR on persistent storage across invocations. An uncertain
publish response is deliberately not retried automatically.
"""
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urlparse

import requests


def account(platform):
    brand = os.getenv("SOCIAL_BRAND", "TOPIK").upper()
    if brand not in {"TOPIK", "ENGLISH", "LANGUAGE"}:
        raise ValueError("Unknown SOCIAL_BRAND")
    suffix = "" if brand == "TOPIK" else "_" + brand
    prefix = "IG" if platform == "instagram" else "THREADS"
    token = os.getenv(prefix + "_ACCESS_TOKEN" + suffix, "")
    user = os.getenv(prefix + "_USER_ID" + suffix, "")
    if not token or not user:
        raise ValueError(f"Missing {prefix}_ACCESS_TOKEN{suffix}/{prefix}_USER_ID{suffix}")
    if not user.isdigit():
        raise ValueError(f"{prefix}_USER_ID must be a numeric API user ID")
    if platform == "instagram":
        login = os.getenv("IG_LOGIN_TYPE", "facebook")
        if login not in {"facebook", "instagram"}:
            raise ValueError("IG_LOGIN_TYPE must be facebook or instagram")
        version = os.getenv("META_GRAPH_VERSION", "v25.0")
        base = f"https://graph.{login}.com/{version}"
    else:
        base = "https://graph.threads.net/v1.0"
    return base, user, token


def api(method, url, token, **fields):
    # Tokens stay out of URLs and exception messages. No automatic POST retries.
    try:
        response = requests.request(method, url,
            headers={"Authorization": f"Bearer {token}"}, timeout=60,
            **({"params": fields} if method == "GET" else {"data": fields}))
        payload = response.json()
    except (requests.RequestException, ValueError):
        raise RuntimeError("Meta request failed or returned invalid JSON") from None
    if not response.ok or "error" in payload:
        error = payload.get("error") or {}
        raise RuntimeError(f"Meta API error: HTTP {response.status_code}, code={error.get('code')}, subcode={error.get('error_subcode')}")
    return payload


def publish(platform, meta, caption):
    if os.getenv("META_PUBLISH_ENABLED", "false").lower() != "true":
        return {"ok": False, "skipped": True, "prepared": True,
                "reason": "Meta publishing disabled; set META_PUBLISH_ENABLED=true to publish",
                "caption": caption, "video_url": meta.get("public_video_url")}
    base, user, token = account(platform)
    url = meta.get("public_video_url") or ""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("public_video_url must be a public HTTPS video URL")
    if not caption.strip():
        raise ValueError("Publication requires a nonempty caption")
    limit = 2200 if platform == "instagram" else 500
    if len(caption) > limit:
        raise ValueError(f"{platform} caption exceeds {limit} characters")
    key = hashlib.sha256(json.dumps([platform, base, user, url, caption]).encode()).hexdigest()
    folder = Path(os.getenv("META_PUBLISH_STATE_DIR", ".meta-publish-state"))
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (key + ".json")
    # Refuse corrupt receipts instead of silently forgetting a publication.
    receipt = json.loads(path.read_text()) if path.exists() else {}

    def save():
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(receipt), encoding="utf-8")
        temp.replace(path)

    if receipt.get("media_id"):
        return {"ok": True, "published": True, "duplicate": True,
                "media_id": receipt["media_id"], "note": "Already published"}
    if receipt.get("publishing"):
        raise RuntimeError("Previous publish outcome is uncertain; reconcile the saved container before retrying")
    create_edge = "media" if platform == "instagram" else "threads"
    publish_edge = "media_publish" if platform == "instagram" else "threads_publish"
    status_field = "status_code" if platform == "instagram" else "status"
    if not receipt.get("container_id"):
        fields = {"video_url": url, "media_type": "REELS" if platform == "instagram" else "VIDEO"}
        fields["caption" if platform == "instagram" else "text"] = caption
        receipt["container_id"] = api("POST", f"{base}/{user}/{create_edge}", token, **fields)["id"]
        save()
    container = receipt["container_id"]
    for attempt in range(30):
        status = api("GET", f"{base}/{container}", token, fields=status_field).get(status_field)
        if status == "FINISHED":
            break
        if status != "IN_PROGRESS":
            raise RuntimeError(f"Container {container} is {status}; requires reconciliation")
        if attempt == 29:
            raise TimeoutError(f"Container {container} still processing; retry resumes this container")
        time.sleep(10)
    receipt["publishing"] = True
    save()
    result = api("POST", f"{base}/{user}/{publish_edge}", token, creation_id=container)
    receipt["media_id"] = result["id"]
    receipt["publishing"] = False
    save()
    return {"ok": True, "published": True, "media_id": result["id"],
            "container_id": container, "note": f"{platform} published"}
