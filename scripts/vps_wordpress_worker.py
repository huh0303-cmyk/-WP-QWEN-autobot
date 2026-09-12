"""Single-flight WordPress publisher for the VPS.

Jobs are JSON files in a durable queue.  The worker never runs two jobs at
once, claims a file atomically, and leaves failed jobs with a retry timestamp.
Credentials are read from the root-only VPS file and are never logged.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth
if os.getenv("FORCE_SOURCE_IPV4", "false").strip().lower() in {"1", "true", "yes", "on"}:
    import socket
    _getaddrinfo = socket.getaddrinfo
    def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        return _getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    socket.getaddrinfo = _ipv4_only_getaddrinfo

ROOT = Path(__file__).resolve().parents[1]
QUEUE = Path(os.environ.get("VPS_WP_QUEUE", ROOT / "data/vps-wp-queue"))
CREDENTIALS = Path(os.environ.get("VPS_WP_CREDENTIALS", "/etc/korea365/wp-sites.json"))
MAX_RETRIES = int(os.environ.get("VPS_WP_MAX_RETRIES", "3"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _claim() -> tuple[Path, dict] | None:
    QUEUE.mkdir(parents=True, exist_ok=True)
    for path in sorted(QUEUE.glob("*.queued.json")):
        # Replace the state suffix instead of stacking suffixes on retries.
        processing = path.with_name(path.name[:-len(".queued.json")] + ".processing.json")
        try:
            path.rename(processing)
        except FileNotFoundError:
            continue
        try:
            return processing, json.loads(processing.read_text(encoding="utf-8"))
        except Exception:
            processing.rename(processing.with_name(processing.name[:-len(".processing.json")] + ".failed.json"))
    return None


def run_one(path: Path, job: dict) -> bool:
    site_url = str(job.get("site_url", "")).rstrip("/")
    secret_name = str(job.get("secret_name", "")).strip()
    if not site_url or not secret_name:
        job.update(status="failed", error="site_url and secret_name are required", checked_at=_now())
        path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        return False
    credentials = json.loads(CREDENTIALS.read_text(encoding="utf-8"))
    password = credentials.get(secret_name, "")
    if not password:
        job.update(status="credential_required", error="credential is not provisioned", checked_at=_now())
        path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        return False
    # Preferred production path: GitHub supplies an already reviewed article;
    # VPS performs only the authenticated, idempotent REST publication.
    if job.get("title") and job.get("content_html"):
        auth = HTTPBasicAuth("huh0303@gmail.com", password)
        api = site_url + "/wp-json/wp/v2/posts"
        try:
            existing = requests.get(api, params={"search": job["title"], "per_page": 10, "_fields": "id,title,link,status"}, auth=auth, timeout=25)
            existing.raise_for_status()
            for row in existing.json():
                if row.get("title", {}).get("rendered", "").strip() == job["title"].strip() and row.get("status") == "publish":
                    job.update(status="published", public_url=row.get("link", ""), remote_id=row.get("id"), checked_at=_now())
                    target = path.with_name(path.name[:-len(".processing.json")] + ".published.json")
                    path.rename(target); target.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
                    return True
            payload = {"title": job["title"], "content": job["content_html"], "status": job.get("status_after_review", "publish")}
            response = requests.post(api, json=payload, auth=auth, timeout=40)
            response.raise_for_status()
            row = response.json()
            if not row.get("id") or not row.get("link"):
                raise RuntimeError("REST response missing post id or public URL")
            job.update(status="published" if payload["status"] == "publish" else "drafted", public_url=row["link"], remote_id=row["id"], checked_at=_now())
            target = path.with_name(path.name[:-len(".processing.json")] + (".published.json" if job["status"] == "published" else ".drafted.json"))
            path.rename(target); target.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
            return True
        except Exception as exc:
            job.update(status="failed", retries=int(job.get("retries", 0)) + 1,
                       last_output=f"REST publish failed: {type(exc).__name__}: {exc}", checked_at=_now())
            target = path.with_name(path.name[:-len(".processing.json")] + ".failed.json")
            path.rename(target); target.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
            return False
    env = os.environ.copy()
    env[secret_name] = password
    env.update({
        "TARGET_SITE_URL": site_url,
        "SITE_FILTER_URL": site_url,
        "WP_AUTOPUBLISH_ENABLED": "true",
        "FORCE_SOURCE_IPV4": "true",
        "FORCE_KEYWORD": str(job.get("force_keyword", "")),
        "PYTHONUNBUFFERED": "1",
    })
    command = [str(ROOT / ".venv/bin/python"), str(ROOT / "scripts/autopost_mega.py")]
    job.update(status="publishing", started_at=_now(), checked_at=_now())
    path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=900)
    job["checked_at"] = _now()
    job["last_output"] = (result.stdout + "\n" + result.stderr)[-4000:]
    if result.returncode == 0 and "✅ 공개 발행" in result.stdout:
        job.update(status="published")
        target = path.with_name(path.name[:-len(".processing.json")] + ".published.json")
        path.rename(target)
        target.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    retries = int(job.get("retries", 0)) + 1
    job.update(status="failed" if retries >= MAX_RETRIES else "queued", retries=retries, next_retry_at=_now())
    state = ".failed.json" if retries >= MAX_RETRIES else ".queued.json"
    target = path.with_name(path.name[:-len(".processing.json")] + state)
    path.rename(target)
    target.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return False


def main() -> None:
    while True:
        item = _claim()
        if item:
            run_one(*item)
            continue
        time.sleep(int(os.environ.get("VPS_WP_POLL_SECONDS", "15")))


if __name__ == "__main__":
    main()
