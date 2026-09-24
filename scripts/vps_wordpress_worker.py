"""Single-flight WordPress publisher for the VPS.

Jobs are JSON files in a durable queue.  The worker never runs two jobs at
once, claims a file atomically, and leaves failed jobs with a retry timestamp.
Credentials are read from the root-only VPS file and are never logged.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from control_center.registry import load_wordpress_sites

QUEUE = Path(os.environ.get("VPS_WP_QUEUE", ROOT / "data/vps-wp-queue"))
CREDENTIALS = Path(os.environ.get("VPS_WP_CREDENTIALS", "/etc/korea365/wp-sites.json"))
MAX_RETRIES = int(os.environ.get("VPS_WP_MAX_RETRIES", "3"))
KST = timezone(timedelta(hours=9))
DAILY_FLOOR_STATE = ROOT / "data" / "vps-wp-daily-floor.json"
DAILY_FLOOR_MAX_ENQUEUE = max(1, int(os.environ.get("VPS_WP_DAILY_MAX_ENQUEUE", "2")))

# GitHub only hands off already-composed content_html; the "preferred
# production path" below used to publish that HTML verbatim, including
# whatever ephemeral image URL (Replicate/Pixabay/a signed R2 download)
# autopost_mega.py's writer had hotlinked into it. Those links expire
# within hours, which was the actual root cause of the network-wide
# broken-image backlog cleaned up on 2026-09-13. Re-host each one to this
# site's own WordPress media library before publishing, same as the
# featured-image handling autopost_mega.py already does for its own
# direct-publish path.
_TEMP_IMAGE_HOSTS = ("replicate.delivery", "replicateusercontent.com", "pixabay.com/get", "r2.cloudflarestorage.com")


def _is_temporary_image_url(url: str) -> bool:
    lowered = url.lower()
    return any(host in lowered for host in _TEMP_IMAGE_HOSTS) or "x-amz-signature=" in lowered


def _rehost_temp_images(content_html: str, site_url: str, auth: HTTPBasicAuth, job_id: str) -> tuple[str, int]:
    """Return (content_html with temp URLs replaced, featured media id or 0).

    Raises on any failure - callers must not publish with an unverified
    image link, matching the WordPress-specific policy already established
    for the direct-publish path (hold the whole post rather than let a
    broken image through).
    """
    candidates = [u for u in set(re.findall(r'src="(https?://[^"]+)"', content_html)) if _is_temporary_image_url(u)]
    featured_media_id = 0
    for index, temp_url in enumerate(candidates):
        image_response = requests.get(temp_url, timeout=45)
        image_response.raise_for_status()
        content_type = image_response.headers.get("content-type", "image/png")
        ext = "png" if "png" in content_type else "jpg" if "jpeg" in content_type else "webp"
        media = requests.post(
            f"{site_url}/wp-json/wp/v2/media", auth=auth,
            headers={"Content-Disposition": f'attachment; filename="{job_id}-{index}.{ext}"', "Content-Type": content_type},
            data=image_response.content, timeout=60,
        )
        media.raise_for_status()
        media_data = media.json()
        source_url = media_data.get("source_url", "")
        if not source_url.startswith(site_url.rstrip("/") + "/wp-content/uploads/"):
            raise RuntimeError(f"unexpected WordPress media location for {job_id}")
        content_html = content_html.replace(temp_url, source_url)
        if not featured_media_id:
            featured_media_id = int(media_data["id"])
    return content_html, featured_media_id


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
        target = path.with_name(path.name[:-len(".processing.json")] + ".failed.json")
        path.rename(target)
        target.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        return False
    credentials = json.loads(CREDENTIALS.read_text(encoding="utf-8"))
    password = credentials.get(secret_name, "")
    if not password:
        job.update(status="credential_required", error="credential is not provisioned", checked_at=_now())
        target = path.with_name(path.name[:-len(".processing.json")] + ".credential_required.json")
        path.rename(target)
        target.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        return False
    # Preferred production path: GitHub supplies an already reviewed article;
    # VPS performs only the authenticated, idempotent REST publication.
    if job.get("title") and job.get("content_html"):
        auth = HTTPBasicAuth("huh0303@gmail.com", password)
        api = site_url + "/wp-json/wp/v2/posts"
        try:
            # Final safety gate for the VPS publication path. Public article HTML
            # must never expose internal stock-provider/license provenance.
            from stock_image_provider import contains_public_photo_credit
            if contains_public_photo_credit(job["content_html"]):
                raise RuntimeError("PUBLIC_PHOTO_CREDIT_LEAK: blocked before WordPress REST write")
            existing = requests.get(api, params={"search": job["title"], "per_page": 10, "_fields": "id,title,link,status"}, auth=auth, timeout=25)
            existing.raise_for_status()
            for row in existing.json():
                if row.get("title", {}).get("rendered", "").strip() == job["title"].strip() and row.get("status") == "publish":
                    job.update(status="published", public_url=row.get("link", ""), remote_id=row.get("id"), checked_at=_now())
                    target = path.with_name(path.name[:-len(".processing.json")] + ".published.json")
                    path.rename(target); target.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
                    return True
            content_html, featured_media_id = _rehost_temp_images(job["content_html"], site_url, auth, job.get("job_id", ""))
            payload = {"title": job["title"], "content": content_html, "status": job.get("status_after_review", "publish")}
            if featured_media_id:
                payload["featured_media"] = featured_media_id
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


def _daily_floor_state(payload: dict) -> None:
    DAILY_FLOOR_STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = DAILY_FLOOR_STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, DAILY_FLOOR_STATE)


def _daily_floor_once() -> dict:
    """Queue a bounded number of missing regular-WP daily posts on the VPS.

    The check uses the same root-only application passwords as publication,
    so GitHub-runner bot blocking cannot make the network look empty.
    """
    now = datetime.now(KST)
    hour_key = now.strftime("%Y-%m-%dT%H")
    previous = {}
    try:
        previous = json.loads(DAILY_FLOOR_STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if previous.get("hour_key") == hour_key:
        return previous

    try:
        credentials = json.loads(CREDENTIALS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = {"hour_key": hour_key, "checked_at": _now(), "status": "credential_store_unavailable"}
        _daily_floor_state(payload)
        return payload

    regular = [site for site in load_wordpress_sites() if site.content_type == "blog"]
    if len(regular) != 25:
        payload = {"hour_key": hour_key, "checked_at": _now(), "status": "registry_count_error",
                   "regular_count": len(regular)}
        _daily_floor_state(payload)
        return payload

    # Stable hourly rotation prevents the same first sites from monopolizing
    # bounded slots while still avoiding simultaneous 25-site bursts.
    import hashlib
    regular.sort(key=lambda site: hashlib.sha256(
        f"{now.date().isoformat()}|{now.hour}|{site.site_id}".encode()
    ).hexdigest())

    rows, queued = [], 0
    for site in regular:
        password = credentials.get(site.secret_name, "")
        if not password:
            rows.append({"site_id": site.site_id, "status": "credential_required"})
            continue
        auth = HTTPBasicAuth("huh0303@gmail.com", password)
        try:
            response = requests.get(
                site.url + "/wp-json/wp/v2/posts",
                auth=auth,
                headers={"User-Agent": "Korea365-VPS/1.0"},
                params={"status": "publish", "per_page": 1, "orderby": "date",
                        "order": "desc", "_fields": "link,date_gmt,title"},
                timeout=20,
            )
            response.raise_for_status()
            posts = response.json()
            if not isinstance(posts, list):
                raise ValueError("invalid WordPress inventory")
        except Exception as exc:
            rows.append({"site_id": site.site_id, "status": "read_error",
                         "error_type": type(exc).__name__})
            continue

        latest = posts[0] if posts else {}
        raw = latest.get("date_gmt")
        published_today = False
        if raw:
            try:
                stamp = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=timezone.utc)
                published_today = stamp.astimezone(KST).date() == now.date()
            except ValueError:
                pass
        if published_today:
            rows.append({"site_id": site.site_id, "status": "published_today",
                         "public_url": latest.get("link", "")})
            continue

        job_id = f"daily-{now.date().isoformat()}-{site.site_id}"
        existing = next((p for suffix in ("queued","processing","published","failed","credential_required")
                         if (p := QUEUE / f"{job_id}.{suffix}.json").exists()), None)
        if existing:
            rows.append({"site_id": site.site_id, "status": "already_tracked"})
            continue
        if queued >= DAILY_FLOOR_MAX_ENQUEUE:
            rows.append({"site_id": site.site_id, "status": "due"})
            continue

        QUEUE.mkdir(parents=True, exist_ok=True)
        payload = {
            "job_id": job_id, "site_url": site.url, "secret_name": site.secret_name,
            "force_keyword": "", "status": "queued", "source": "vps-daily-floor",
            "day_kst": now.date().isoformat(), "received_at": _now(), "retries": 0,
        }
        tmp = QUEUE / f".{job_id}.tmp"
        target = QUEUE / f"{job_id}.queued.json"
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(tmp, 0o600)
        os.replace(tmp, target)
        queued += 1
        rows.append({"site_id": site.site_id, "status": "queued"})

    result = {"hour_key": hour_key, "checked_at": _now(), "status": "ok",
              "target": 25, "queued": queued, "sites": rows}
    _daily_floor_state(result)
    return result


def main() -> None:
    while True:
        try:
            _daily_floor_once()
        except Exception:
            # Daily-floor discovery failure must never kill the publisher.
            pass
        item = _claim()
        if item:
            run_one(*item)
            continue
        time.sleep(int(os.environ.get("VPS_WP_POLL_SECONDS", "15")))


if __name__ == "__main__":
    main()
