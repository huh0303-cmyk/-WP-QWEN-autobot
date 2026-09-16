from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


@dataclass
class AuditResult:
    verified: bool
    state: str
    platform: str
    target: str
    evidence: dict[str, Any]
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _host_matches(url: str, site_url: str) -> bool:
    try:
        a = (urlparse(url).hostname or "").lower().removeprefix("www.")
        b = (urlparse(site_url).hostname or "").lower().removeprefix("www.")
        return bool(a and b and a == b)
    except ValueError:
        return False


def _looks_like_public_content(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    path = parsed.path.lower()
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and bool(path.strip("/")) and not any(
        x in path for x in ("wp-admin", "wp-login", "preview", "manage/", "dashboard")
    )


def verify_web_publication(public_url: str, site_url: str, *, expected_title: str = "", marker: str = "", timeout: int = 15) -> AuditResult:
    now = time.time()
    evidence: dict[str, Any] = {
        "public_url": public_url,
        "site_url": site_url,
        "checked_at": now,
        "host_match": _host_matches(public_url, site_url),
        "public_shape": _looks_like_public_content(public_url),
    }
    if not evidence["host_match"] or not evidence["public_shape"]:
        return AuditResult(False, "NEEDS_ATTENTION", "web", site_url, evidence, "URL is not a valid public URL for the target site")
    try:
        response = requests.get(public_url, timeout=timeout, allow_redirects=True, headers={"User-Agent": "Korea365-ProjectA-Auditor/1.0"})
    except requests.RequestException as exc:
        evidence["network_error"] = str(exc)[:300]
        return AuditResult(False, "NEEDS_ATTENTION", "web", site_url, evidence, "public page could not be fetched")
    evidence.update(http_status=response.status_code, final_url=response.url,
                    content_type=response.headers.get("content-type", ""), response_bytes=len(response.content))
    if response.status_code < 200 or response.status_code >= 400:
        return AuditResult(False, "NEEDS_ATTENTION", "web", site_url, evidence, f"HTTP {response.status_code}")
    if not _host_matches(response.url, site_url):
        return AuditResult(False, "NEEDS_ATTENTION", "web", site_url, evidence, "redirected outside target site")
    text = response.text[:1_500_000]
    lowered = re.sub(r"\s+", " ", text).lower()
    failure_markers = ("404 not found", "page not found", "페이지를 찾을 수", "로그인", "sign in to continue")
    suspicious = [item for item in failure_markers if item in lowered]
    evidence["failure_markers"] = suspicious
    if suspicious and len(text) < 250_000:
        return AuditResult(False, "NEEDS_ATTENTION", "web", site_url, evidence, "page resembles error/login content")
    if expected_title:
        evidence["title_match"] = expected_title.strip().lower() in lowered
    if marker:
        evidence["marker_match"] = marker in text
    if expected_title and marker and not evidence.get("title_match") and not evidence.get("marker_match"):
        return AuditResult(False, "NEEDS_ATTENTION", "web", site_url, evidence, "expected publication identity not found on page")
    return AuditResult(True, "VERIFIED_COMPLETE", "web", site_url, evidence, "public page verified")


def verify_youtube_receipt(receipt: dict[str, Any] | str | Path, *, expected_channel_id: str,
                           expected_channel_key: str = "", expected_privacy: str = "private") -> AuditResult:
    if isinstance(receipt, (str, Path)):
        path = Path(receipt)
        if not path.is_file():
            return AuditResult(False, "NEEDS_ATTENTION", "youtube", expected_channel_id, {"receipt": str(path)}, "upload receipt file missing")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return AuditResult(False, "NEEDS_ATTENTION", "youtube", expected_channel_id,
                               {"receipt": str(path), "error": str(exc)}, "invalid upload receipt")
    else:
        data = dict(receipt)
    video_id = str(data.get("video_id", ""))
    privacy = str(data.get("privacy_status", ""))
    channel_id = str(data.get("verified_channel_id", data.get("channel_id", "")))
    channel_key = str(data.get("channel_key", ""))
    evidence = {"video_id": video_id, "privacy_status": privacy, "verified_channel_id": channel_id,
                "channel_key": channel_key, "checked_at": time.time()}
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        return AuditResult(False, "NEEDS_ATTENTION", "youtube", expected_channel_id, evidence, "invalid YouTube video id")
    if channel_id != expected_channel_id:
        return AuditResult(False, "NEEDS_ATTENTION", "youtube", expected_channel_id, evidence, "YouTube channel identity mismatch")
    if expected_channel_key and channel_key != expected_channel_key:
        return AuditResult(False, "NEEDS_ATTENTION", "youtube", expected_channel_id, evidence, "YouTube channel key mismatch")
    if privacy != expected_privacy:
        return AuditResult(False, "NEEDS_ATTENTION", "youtube", expected_channel_id, evidence, "YouTube privacy state mismatch")
    if expected_privacy == "private":
        evidence["review_url"] = f"https://studio.youtube.com/video/{video_id}/edit"
        return AuditResult(True, "VERIFIED_PRIVATE", "youtube", expected_channel_id, evidence, "private upload receipt verified")
    if expected_privacy == "public":
        evidence["public_url"] = f"https://www.youtube.com/watch?v={video_id}"
        return AuditResult(True, "VERIFIED_COMPLETE", "youtube", expected_channel_id, evidence, "public upload receipt verified")
    return AuditResult(True, "READY_FOR_AUDIT", "youtube", expected_channel_id, evidence, "receipt verified; privacy state requires policy review")


def write_audit_receipt(path: str | Path, result: AuditResult, *, job_id: str = "") -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = result.to_dict()
    payload["job_id"] = job_id
    payload["written_at"] = time.time()
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(target)
