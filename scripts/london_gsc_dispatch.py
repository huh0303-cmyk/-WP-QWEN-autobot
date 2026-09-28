"""Queue a Search Console sitemap submission after a verified public post."""
from __future__ import annotations

from datetime import datetime, timezone
import os
import re
from urllib.parse import urlparse

import requests

REPO = "huh0303-cmyk/-WP-QWEN-autobot"
WORKFLOW = "london-gsc-submit.yml"
RUN_PATTERN = re.compile(r"lgpt-[0-9]{8}-[0-9]{6}-[a-f0-9]{6}\Z")


def queue_submission(state: dict, site_url: str) -> dict:
    """Dispatch once per published URL; leave failures visible for explicit retry."""
    run_id = str(state.get("run_id") or "")
    receipt = state.get("receipt") or {}
    public_url = str(receipt.get("url") or "")
    prior = state.get("indexing_submission") or {}
    if prior.get("url") == public_url and prior.get("status") in {"queued", "submitted"}:
        return prior
    result = {"status": "failed", "url": public_url, "at": datetime.now(timezone.utc).isoformat()}
    try:
        if not RUN_PATTERN.fullmatch(run_id):
            raise ValueError("invalid run ID")
        if receipt.get("status") not in {"published", "published_verified"}:
            raise ValueError("only verified public posts can be submitted")
        parsed, expected = urlparse(public_url), urlparse(site_url)
        if (parsed.scheme != "https" or parsed.hostname != expected.hostname or
                parsed.port not in (None, 443) or parsed.username or parsed.password or
                not parsed.path.strip("/")):
            raise ValueError("public URL does not belong to the selected site")
        token = os.environ.get("GH_TOKEN", "").strip()
        if not token:
            raise RuntimeError("GH_TOKEN is missing for GSC dispatch")
        response = requests.post(
            f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW}/dispatches",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            json={"ref": "main", "inputs": {"run_id": run_id, "site_id": state["site_id"], "public_url": public_url}},
            timeout=20,
        )
        if response.status_code != 204:
            raise RuntimeError(f"GitHub workflow dispatch HTTP {response.status_code}: {response.text[:180]}")
        result["status"] = "queued"
    except (ValueError, RuntimeError, requests.RequestException, KeyError) as exc:
        result["error"] = str(exc)[:300]
    state["indexing_submission"] = result
    return result
