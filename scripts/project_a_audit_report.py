#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation_hub.youtube_registry import load_channels
from control_center.audit_engine import verify_web_publication


def db_path() -> Path:
    return Path(os.environ.get("CONTROL_OPERATIONS_DB", ROOT / "data" / "control-operations.sqlite3"))


def audit_web(since: float) -> list[dict[str, Any]]:
    path = db_path()
    if not path.is_file():
        return [{"platform": "web", "state": "NEEDS_ATTENTION", "reason": f"operation DB missing: {path}"}]
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    rows = db.execute(
        "SELECT id,site_id,phase,payload,created,updated FROM jobs WHERE created>=? ORDER BY created DESC",
        (since,),
    ).fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        payload = json.loads(row["payload"])
        platform = str(payload.get("platform", ""))
        if platform not in {"wordpress", "news", "blogger", "tistory"}:
            continue
        base = {
            "job_id": row["id"],
            "platform": platform,
            "site_id": row["site_id"],
            "reported_phase": row["phase"],
            "title": payload.get("title", ""),
            "updated": row["updated"],
        }
        public_url = str(payload.get("public_url", ""))
        site_url = str(payload.get("site_url", ""))
        if row["phase"] != "published":
            base.update(state="RUNNING" if row["phase"] not in {"failed", "stopped", "attention"} else
                        "FAILED" if row["phase"] == "failed" else "NEEDS_ATTENTION",
                        reason=payload.get("detail", ""), public_url=public_url)
            results.append(base)
            continue
        result = verify_web_publication(public_url, site_url, expected_title=str(payload.get("title", "")))
        base.update(result.to_dict())
        results.append(base)
    return results


def _youtube_service(profile: str):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    suffix = profile.upper().strip()
    def value(name: str) -> str:
        return (os.environ.get(f"YOUTUBE_OAUTH_{name}_{suffix}", "") or
                os.environ.get(f"YOUTUBE_OAUTH_{name}", "")).strip()

    client_id = value("CLIENT_ID")
    client_secret = value("CLIENT_SECRET")
    refresh_token = value("REFRESH_TOKEN")
    if not all((client_id, client_secret, refresh_token)):
        raise RuntimeError(f"YouTube OAuth credentials missing for profile {suffix}")
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=None,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def _video_id(url: str) -> str:
    for pattern in (r"studio\.youtube\.com/video/([A-Za-z0-9_-]{11})", r"[?&]v=([A-Za-z0-9_-]{11})", r"youtu\.be/([A-Za-z0-9_-]{11})"):
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""


def audit_youtube(since: float) -> list[dict[str, Any]]:
    if not os.environ.get("SHEET_ID"):
        return [{"platform": "youtube", "state": "NEEDS_ATTENTION", "reason": "SHEET_ID missing; YouTube execution ledger cannot be audited"}]
    try:
        from gsheets_direct import get_sheets_service
        service = get_sheets_service()
        values = service.spreadsheets().values().get(
            spreadsheetId=os.environ["SHEET_ID"], range="'자동화_유튜브실행'!A:I"
        ).execute().get("values", [])
    except Exception as exc:
        return [{"platform": "youtube", "state": "NEEDS_ATTENTION", "reason": f"YouTube execution ledger read failed: {str(exc)[:300]}"}]

    channels = {c.channel_key: c for c in load_channels()}
    results: list[dict[str, Any]] = []
    for cells in values[1:] if values else []:
        cells = cells + [""] * (9 - len(cells))
        stamp, channel_key, title, workflow, reported_status, run_url, _, url, error = cells[:9]
        try:
            parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
        except Exception:
            parsed = 0
        if parsed and parsed < since:
            continue
        row: dict[str, Any] = {
            "platform": "youtube",
            "channel_key": channel_key,
            "title": title,
            "workflow": workflow,
            "reported_status": reported_status,
            "run_url": run_url,
            "url": url,
            "error": error,
            "timestamp": stamp,
        }
        channel = channels.get(channel_key)
        vid = _video_id(url)
        if reported_status not in {"비공개 업로드", "공개", "published", "public"}:
            row.update(state="FAILED" if reported_status == "실패" else "NEEDS_ATTENTION",
                       reason=error or f"not an upload-complete state: {reported_status}")
            results.append(row)
            continue
        if not channel:
            row.update(state="NEEDS_ATTENTION", reason="channel is absent from registry")
            results.append(row)
            continue
        if not vid:
            row.update(state="NEEDS_ATTENTION", reason="validated YouTube URL/video id missing")
            results.append(row)
            continue
        try:
            youtube = _youtube_service(channel.secret_profile)
            response = youtube.videos().list(part="snippet,status", id=vid).execute()
            items = response.get("items", [])
            if not items:
                raise RuntimeError("YouTube API returned no matching video")
            item = items[0]
            actual_channel = item.get("snippet", {}).get("channelId", "")
            privacy = item.get("status", {}).get("privacyStatus", "")
            row.update(video_id=vid, actual_channel_id=actual_channel, expected_channel_id=channel.channel_id,
                       privacy_status=privacy)
            if actual_channel != channel.channel_id:
                row.update(state="NEEDS_ATTENTION", reason="video exists but belongs to the wrong channel")
            elif privacy == "private":
                row.update(state="VERIFIED_PRIVATE", reason="YouTube API verified private upload")
            elif privacy == "public":
                row.update(state="VERIFIED_COMPLETE", public_url=f"https://www.youtube.com/watch?v={vid}",
                           reason="YouTube API verified public upload")
            else:
                row.update(state="READY_FOR_AUDIT", reason=f"YouTube API verified video with privacy={privacy}")
        except Exception as exc:
            row.update(state="NEEDS_ATTENTION", video_id=vid, reason=f"YouTube API verification failed: {str(exc)[:300]}")
        results.append(row)
    return results


def summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for item in items:
        state = str(item.get("state", "UNKNOWN"))
        counts[state] = counts.get(state, 0) + 1
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project": "Project A",
        "counts": counts,
        "verified_complete": counts.get("VERIFIED_COMPLETE", 0),
        "verified_private": counts.get("VERIFIED_PRIVATE", 0),
        "needs_attention": counts.get("NEEDS_ATTENTION", 0),
        "failed": counts.get("FAILED", 0),
        "items": items,
    }


def markdown(report: dict[str, Any]) -> str:
    c = report["counts"]
    lines = [
        "# Project A Audit Report",
        "",
        f"Generated: {report['generated_at']}",
        "",
        f"- VERIFIED COMPLETE: {c.get('VERIFIED_COMPLETE', 0)}",
        f"- VERIFIED PRIVATE: {c.get('VERIFIED_PRIVATE', 0)}",
        f"- NEEDS ATTENTION: {c.get('NEEDS_ATTENTION', 0)}",
        f"- FAILED: {c.get('FAILED', 0)}",
        f"- RUNNING: {c.get('RUNNING', 0)}",
        "",
        "## Exceptions / action required",
    ]
    problems = [i for i in report["items"] if i.get("state") in {"NEEDS_ATTENTION", "FAILED", "BLOCKED"}]
    if not problems:
        lines.append("- None detected in this audit window.")
    for item in problems:
        target = item.get("site_id") or item.get("channel_key") or item.get("target") or "unknown"
        lines.append(f"- {item.get('state')}: {item.get('platform')} / {target} — {item.get('reason', '')}")
    lines.extend(["", "## Verified receipts"])
    verified = [i for i in report["items"] if i.get("state") in {"VERIFIED_COMPLETE", "VERIFIED_PRIVATE"}]
    if not verified:
        lines.append("- No verified receipts in this audit window.")
    for item in verified:
        target = item.get("site_id") or item.get("channel_key") or item.get("target") or "unknown"
        url = item.get("public_url") or item.get("url") or item.get("evidence", {}).get("public_url", "")
        lines.append(f"- {item.get('state')}: {item.get('platform')} / {target} {url}".rstrip())
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since-hours", type=float, default=24.0)
    parser.add_argument("--output-dir", default=str(ROOT / "data"))
    args = parser.parse_args()
    since = time.time() - max(0.1, args.since_hours) * 3600
    items = audit_web(since) + audit_youtube(since)
    report = summary(items)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "project_a_audit_report.json"
    md_path = out / "project_a_audit_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(md_path.read_text(encoding="utf-8"))
    return 2 if report["needs_attention"] or report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
