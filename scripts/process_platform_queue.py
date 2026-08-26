#!/usr/bin/env python3
"""Process one or more queued non-WordPress publishing jobs from Google Sheets."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from automation_hub.blogger_adapter import BloggerPublisher
from automation_hub.interactive_adapters import InteractiveEditorPublisher
from automation_hub.publishing import PublishJob
from gsheets_direct import get_sheets_service
from sync_automation_hub_to_sheets import ACCOUNTS_TAB, QUEUE_TAB


def _records(values: list[list[str]]) -> list[dict[str, str]]:
    if not values:
        return []
    header = values[0]
    return [dict(zip(header, [*row, *([""] * (len(header) - len(row)))])) for row in values[1:] if row]


def _access_token(auth_profile: str) -> str:
    prefix = auth_profile.strip().upper().replace("-", "_")
    refresh_token = os.environ.get(f"{prefix}_GOOGLE_REFRESH_TOKEN", "") or os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "")
    client_id = os.environ.get(f"{prefix}_GOOGLE_CLIENT_ID", "") or os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get(f"{prefix}_GOOGLE_CLIENT_SECRET", "") or os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
    if not all((refresh_token, client_id, client_secret)):
        return ""
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={"client_id": client_id, "client_secret": client_secret, "refresh_token": refresh_token, "grant_type": "refresh_token"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def main() -> int:
    spreadsheet_id = os.environ.get("SHEET_ID", "").strip()
    selected_job = os.environ.get("JOB_ID", "").strip()
    max_jobs = max(1, int(os.environ.get("MAX_JOBS", "1")))
    if not spreadsheet_id:
        raise SystemExit("SHEET_ID is required")

    service = get_sheets_service()
    account_values = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=f"'{ACCOUNTS_TAB}'!A1:I").execute().get("values", [])
    queue_values = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=f"'{QUEUE_TAB}'!A1:N").execute().get("values", [])
    accounts = {record["site_id"]: record for record in _records(account_values) if record.get("enabled", "ON").upper() in {"ON", "TRUE", "1"}}
    queue = _records(queue_values)
    processed = 0

    for index, row in enumerate(queue, start=2):
        if row.get("status", "").strip().lower() not in {"ready", "대기"}:
            continue
        if selected_job and row.get("job_id") != selected_job:
            continue
        account = accounts.get(row.get("site_id", ""))
        if not account:
            print(json.dumps({"job_id": row.get("job_id"), "status": "skipped", "error": "enabled account not found"}, ensure_ascii=False))
            continue
        job = PublishJob(
            job_id=row.get("job_id", ""), site_id=row.get("site_id", ""), title=row.get("title", ""),
            content_html=row.get("content_html", ""), labels=[x.strip() for x in row.get("labels", "").split(",") if x.strip()],
            publish_now=row.get("publish_now", "TRUE").upper() in {"TRUE", "ON", "1", "YES"}, source_keyword=row.get("source_keyword", ""),
        )
        platform = account.get("platform", "").lower()
        if platform == "blogger":
            try:
                token = _access_token(account.get("auth_profile", ""))
            except requests.RequestException as exc:
                token = ""
                print(f"OAuth refresh failed for {job.job_id}: {str(exc)[:200]}")
            publisher = BloggerPublisher(job.site_id, account.get("destination_id", ""), token, site_url=account.get("editor_url", ""))
        elif platform in {"naver", "tistory"}:
            publisher = InteractiveEditorPublisher(platform, job.site_id, account.get("editor_url", ""))
        else:
            print(json.dumps({"job_id": job.job_id, "status": "skipped", "error": f"unsupported platform {platform}"}, ensure_ascii=False))
            continue
        result = publisher.publish(job)
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=f"'{QUEUE_TAB}'!D{index}", valueInputOption="RAW",
            body={"values": [[result.status]]},
        ).execute()
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=f"'{QUEUE_TAB}'!J{index}:N{index}", valueInputOption="RAW",
            body={"values": [[result.public_url, result.remote_id, result.error_code, result.message, result.completed_at]]},
        ).execute()
        print(json.dumps(result.to_dict(), ensure_ascii=False))
        processed += 1
        if processed >= max_jobs:
            break
    print(f"Processed {processed} queue job(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
