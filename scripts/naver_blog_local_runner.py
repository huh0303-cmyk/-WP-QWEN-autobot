#!/usr/bin/env python3
"""Local Naver Blog queue runner using a persistent Playwright login session."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from automation_hub.naver_local_adapter import NaverLocalPublisher
from automation_hub.publishing import PublishJob
from gsheets_direct import get_sheets_service
from sync_automation_hub_to_sheets import ACCOUNTS_TAB, QUEUE_TAB


def records(values):
    if not values:
        return []
    header = values[0]
    return [(index, dict(zip(header, [*row, *([""] * (len(header) - len(row)))]))) for index, row in enumerate(values[1:], 2) if row]


def update_result(service, sheet_id, row_index, result):
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id,
        body={"valueInputOption": "RAW", "data": [
            {"range": f"'{QUEUE_TAB}'!D{row_index}", "values": [[result.status]]},
            {"range": f"'{QUEUE_TAB}'!J{row_index}:N{row_index}", "values": [[
                result.public_url, result.remote_id, result.error_code, result.message, result.completed_at,
            ]]},
        ]},
    ).execute()


def select_jobs(service, sheet_id, site_id, selected_job, max_jobs):
    account_rows = records(service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{ACCOUNTS_TAB}'!A1:I"
    ).execute().get("values", []))
    accounts = {
        row.get("site_id"): row for _, row in account_rows
        if row.get("platform", "").lower() == "naver" and row.get("enabled", "ON").upper() in {"ON", "TRUE", "1"}
    }
    if site_id not in accounts:
        raise RuntimeError(f"활성 네이버 계정 행을 찾지 못했습니다: {site_id}")
    queue_rows = records(service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1:N"
    ).execute().get("values", []))
    selected = []
    for row_index, row in queue_rows:
        if row.get("site_id") != site_id or row.get("status", "").strip().lower() not in {"ready", "대기"}:
            continue
        if selected_job and row.get("job_id") != selected_job:
            continue
        selected.append((row_index, row))
        if len(selected) >= max_jobs:
            break
    return accounts[site_id], selected


def build_job(row):
    return PublishJob(
        job_id=row.get("job_id", ""), site_id=row.get("site_id", ""), title=row.get("title", ""),
        content_html=row.get("content_html", ""), labels=[x.strip() for x in row.get("labels", "").split(",") if x.strip()],
        publish_now=row.get("publish_now", "TRUE").upper() in {"TRUE", "ON", "1", "YES"},
        source_keyword=row.get("source_keyword", ""),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["login", "run"])
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--job-id", default="")
    parser.add_argument("--max-jobs", type=int, default=1)
    parser.add_argument("--profile-root", default=str(ROOT / ".local" / "naver-profiles"))
    args = parser.parse_args()
    sheet_id = os.environ.get("SHEET_ID", "").strip()
    if not sheet_id:
        raise SystemExit("SHEET_ID가 필요합니다.")
    service = get_sheets_service()
    account, jobs = select_jobs(service, sheet_id, args.site_id, args.job_id, max(1, args.max_jobs))
    profile_dir = Path(args.profile_root).resolve() / args.site_id
    profile_dir.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(str(profile_dir), headless=False, locale="ko-KR")
        page = context.pages[0] if context.pages else context.new_page()
        if args.command == "login":
            page.goto(account.get("editor_url") or "https://blog.naver.com/GoBlogWrite.naver")
            input("브라우저에서 네이버 로그인을 끝낸 뒤 Enter를 누르세요: ")
            context.close()
            return 0
        if not jobs:
            print("처리할 ready 네이버 글이 없습니다.")
            context.close()
            return 0
        publisher = NaverLocalPublisher(args.site_id, account.get("editor_url", ""), account.get("destination_id", ""))
        for row_index, row in jobs:
            result = publisher.publish(page, build_job(row))
            update_result(service, sheet_id, row_index, result)
            print(json.dumps(result.to_dict(), ensure_ascii=False))
            if not result.ok:
                break
        context.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
