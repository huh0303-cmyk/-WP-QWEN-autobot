"""Dispatch YouTube work to GitHub Actions; never depend on a server-local queue."""
from __future__ import annotations

import os
import time
from urllib.parse import quote

import requests

REPOSITORY = "huh0303-cmyk/-WP-QWEN-autobot"
WORKFLOW = "youtube-github-worker.yml"


def dispatch_youtube_job(channel_key: str) -> dict:
    channel_key = str(channel_key or "").strip().lower()
    allowed = {
        "globalmusic", "healing", "starbucks", "mbb", "kpop",
        "nasa", "history", "invention", "silent_era", "retro_reels",
    }
    if channel_key not in allowed:
        raise RuntimeError(f"Unsupported YouTube channel: {channel_key or '(empty)'}")

    token = next((os.environ.get(name, "").strip() for name in (
        "GH_DISPATCH_TOKEN", "CONTROL_CENTER_GITHUB_TOKEN", "GITHUB_TOKEN"
    ) if os.environ.get(name, "").strip()), "")
    if not token:
        raise RuntimeError(
            "GitHub Actions dispatch token is not configured. Add an Actions-write token "
            "to the control-center environment; no local queue was created."
        )

    ref = os.environ.get("LONDON_PROJECT_GITHUB_REF", "main").strip() or "main"
    url = f"https://api.github.com/repos/{REPOSITORY}/actions/workflows/{quote(WORKFLOW, safe='')}/dispatches"
    response = requests.post(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={"ref": ref, "inputs": {"channel": channel_key, "confirm_publication": "true"}},
        timeout=30,
    )
    if response.status_code != 204:
        # Do not expose response headers or credential values in errors.
        detail = (response.text or "")[:300]
        raise RuntimeError(f"GitHub Actions dispatch failed (HTTP {response.status_code}): {detail}")
    return {
        "job_id": f"gh-dispatch-{channel_key}-{int(time.time())}",
        "channel_key": channel_key,
        "runner": "github-actions",
        "workflow": WORKFLOW,
        "run_url": f"https://github.com/{REPOSITORY}/actions/workflows/{WORKFLOW}",
        "status": "queued",
    }
