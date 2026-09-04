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
from automation_hub.content_identity import active_duplicate, is_same_content, is_similar_content
from automation_hub.draft_notifier import notify_blogger_draft
from automation_hub.interactive_adapters import InteractiveEditorPublisher
from automation_hub.publishing import PublishJob
from gsheets_direct import get_sheets_service
from sync_automation_hub_to_sheets import ACCOUNTS_TAB, QUEUE_TAB


def _records(values: list[list[str]]) -> list[dict[str, str]]:
    if not values:
        return []
    header = values[0]
    return [dict(zip(header, [*row, *([""] * (len(header) - len(row)))])) for row in values[1:] if row]


def _account_indexes(records: list[dict[str, str]]) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    enabled = [r for r in records if r.get("enabled", "ON").upper() in {"ON", "TRUE", "1"}]
    by_site = {r["site_id"]: r for r in enabled}
    by_destination = {r.get("destination_id", ""): r for r in enabled if r.get("destination_id", "")}
    return by_site, by_destination


def _access_token(auth_profile: str) -> str:
    # Blogger writes must use the dedicated OAuth client/token. Falling back to
    # the general Sheets/Drive token can mint a valid access token without the
    # Blogger write scope and then fail late with 403 scope insufficient.
    prefix = auth_profile.strip().upper().replace("-", "_")
    if prefix in {"", "DEFAULT"}:
        prefix = "BLOGGER"
    refresh_token = os.environ.get(f"{prefix}_GOOGLE_REFRESH_TOKEN", "")
    client_id = os.environ.get(f"{prefix}_GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get(f"{prefix}_GOOGLE_CLIENT_SECRET", "")
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
    platform_filter = os.environ.get("PLATFORM_FILTER", "").strip().lower()
    fail_on_empty = os.environ.get("FAIL_ON_EMPTY", "false").strip().lower() in {"1", "true", "yes", "on"}
    if platform_filter in {"all", "*"}:
        platform_filter = ""
    if not spreadsheet_id:
        raise SystemExit("SHEET_ID is required")

    service = get_sheets_service()
    account_values = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=f"'{ACCOUNTS_TAB}'!A1:I").execute().get("values", [])
    queue_values = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=f"'{QUEUE_TAB}'!A1:N").execute().get("values", [])
    # New queue rows use the canonical site_id, while legacy Blogger rows may
    # contain the numeric Blogger blog ID. Resolve both to the same account so
    # an already quality-approved row can be retried without regeneration.
    accounts, accounts_by_destination = _account_indexes(_records(account_values))
    queue = _records(queue_values)
    processed = 0
    failed = 0

    for index, row in enumerate(queue, start=2):
        if row.get("status", "").strip().lower() not in {"ready", "대기"}:
            continue
        if selected_job and row.get("job_id") != selected_job:
            continue
        account = accounts.get(row.get("site_id", "")) or accounts_by_destination.get(row.get("site_id", ""))
        if not account:
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=f"'{QUEUE_TAB}'!D{index}", valueInputOption="RAW",
                body={"values": [["account_missing"]]},
            ).execute()
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=f"'{QUEUE_TAB}'!L{index}:N{index}", valueInputOption="RAW",
                body={"values": [["ACCOUNT_MISSING", "enabled platform account not found", ""]]},
            ).execute()
            print(json.dumps({"job_id": row.get("job_id"), "status": "skipped", "error": "enabled account not found"}, ensure_ascii=False))
            continue
        platform = account.get("platform", "").lower()
        if platform_filter and platform != platform_filter:
            continue
        if platform in {"blogger", "tistory"}:
            completed_duplicate = active_duplicate(
                [candidate for candidate in queue if candidate is not row and candidate.get("status", "").strip().lower() in {"processing", "drafted", "published"}],
                site_id=row.get("site_id", ""), source_id=row.get("source_keyword", ""),
            )
            earlier_ready = any(
                candidate_index < index
                and candidate.get("status", "").strip().lower() in {"ready", "대기"}
                and is_same_content(candidate, site_id=row.get("site_id", ""), source_id=row.get("source_keyword", ""))
                for candidate_index, candidate in enumerate(queue, start=2)
            )
            similar = next((candidate for candidate in queue if candidate is not row
                            and candidate.get("status", "").strip().lower() in {"ready", "대기", "processing", "drafted", "published", "review_ready"}
                            and is_similar_content(candidate, site_id=row.get("site_id", ""),
                                                   title=row.get("title", ""), content_html=row.get("content_html", ""))), None)
            if completed_duplicate or earlier_ready or similar:
                reason = "same target/source already owned by " + (
                    completed_duplicate.get("job_id", "another job") if completed_duplicate else
                    ("an earlier ready row" if earlier_ready else similar.get("job_id", "similar content"))
                )
                service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id, range=f"'{QUEUE_TAB}'!D{index}", valueInputOption="RAW",
                    body={"values": [["duplicate_blocked"]]},
                ).execute()
                service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id, range=f"'{QUEUE_TAB}'!L{index}:N{index}", valueInputOption="RAW",
                    body={"values": [["DUPLICATE_CONTENT", reason, ""]]},
                ).execute()
                print(json.dumps({"job_id": row.get("job_id"), "status": "duplicate_blocked", "reason": reason}, ensure_ascii=False))
                continue
        message = row.get("message", "")
        search_description = message.split("meta_description=", 1)[1].strip() if "meta_description=" in message else ""
        job = PublishJob(
            job_id=row.get("job_id", ""), site_id=row.get("site_id", ""), title=row.get("title", ""),
            content_html=row.get("content_html", ""), labels=[x.strip() for x in row.get("labels", "").split(",") if x.strip()],
            publish_now=row.get("publish_now", "").strip().upper() == "TRUE",
            source_keyword=row.get("source_keyword", ""), search_description=search_description,
        )
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
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=f"'{QUEUE_TAB}'!D{index}", valueInputOption="RAW",
                body={"values": [["unsupported_platform"]]},
            ).execute()
            print(json.dumps({"job_id": job.job_id, "status": "skipped", "error": f"unsupported platform {platform}"}, ensure_ascii=False))
            continue
        # Claim before the external API call. A crash leaves a reviewable
        # `processing` row instead of retrying blindly and creating two drafts.
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=f"'{QUEUE_TAB}'!D{index}", valueInputOption="RAW",
            body={"values": [["processing"]]},
        ).execute()
        result = publisher.publish(job)
        if platform == "blogger" and result.ok and result.status == "drafted":
            notify_blogger_draft(
                site_id=job.site_id, title=job.title, review_url=result.public_url,
                search_description=job.search_description, quality_note=row.get("message", ""),
            )
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
        if not result.ok:
            failed += 1
        if processed >= max_jobs:
            break
    print(f"Processed {processed} queue job(s)")
    if fail_on_empty and processed == 0:
        raise SystemExit("No eligible queue job was processed")
    if failed:
        raise SystemExit(f"{failed} of {processed} processed queue job(s) failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
