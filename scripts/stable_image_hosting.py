"""Re-host an ephemeral (e.g. Replicate) image URL as a permanent repo asset.

Replicate's own delivery URLs expire, which silently breaks any draft that
sits in a review queue for more than a few hours. This downloads the image
once and commits it to the repo, returning a stable raw.githubusercontent.com
URL that never expires. Shared by any writer script that embeds a
generated image directly into draft HTML (see repair_blogger_images.py for
the equivalent after-the-fact repair path used by Blogger).
"""
from __future__ import annotations

import base64
import hashlib
import os
import time
from urllib.parse import urlparse

import requests


def is_temporary(url: str) -> bool:
    return urlparse(url).netloc.lower().endswith(("replicate.delivery", "replicateusercontent.com"))


def _image_ok(url: str) -> tuple[bool, dict]:
    try:
        response = requests.get(url, timeout=25, allow_redirects=True)
        content_type = response.headers.get("content-type", "").lower()
        ok = response.status_code == 200 and content_type.startswith("image/") and len(response.content) > 500
        return ok, {"http": response.status_code, "content_type": content_type, "bytes": len(response.content)}
    except requests.RequestException as exc:
        return False, {"error": str(exc)[:300]}


def host_permanently(url: str, *, asset_key: str) -> str:
    """Download `url` and commit it under assets/tistory_images/, returning a stable URL.

    Raises RuntimeError if the source image or the freshly hosted copy is not
    verifiably a real image; callers must not embed an unverified URL.
    """
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GH_ASSET_TOKEN"]
    ok, evidence = _image_ok(url)
    if not ok:
        raise RuntimeError(f"source image failed verification: {evidence}")
    download = requests.get(url, timeout=30)
    download.raise_for_status()
    data = download.content
    content_type = download.headers.get("content-type", "")
    ext = ".png" if "png" in content_type else ".jpg" if "jpeg" in content_type else ".webp"
    digest = hashlib.sha256(data).hexdigest()[:16]
    path = f"assets/tistory_images/{asset_key}-{digest}{ext}"
    api = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    existing = requests.get(api, headers=headers, params={"ref": "main"}, timeout=30)
    stable_url = f"https://raw.githubusercontent.com/{repo}/main/{path}"
    if existing.status_code != 200:
        response = requests.put(api, headers=headers, json={
            "message": f"fix: host Tistory image {asset_key} [skip ci]",
            "content": base64.b64encode(data).decode(),
            "branch": "main",
        }, timeout=60)
        response.raise_for_status()
    for attempt in range(5):
        ok, evidence = _image_ok(stable_url)
        if ok:
            return stable_url
        time.sleep(2 ** attempt)
    raise RuntimeError(f"stable asset did not verify after upload: {evidence}")
