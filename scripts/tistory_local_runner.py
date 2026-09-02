#!/usr/bin/env python3
"""Durable, serial local registrar for the five Tistory properties.

Google Sheets remains the command source. Ready rows are first copied into a
local SQLite inbox, so shutting down the PC or losing Sheets connectivity does
not lose work.  ``job_id`` is unique: restart/retry cannot create a second post
after a verified private save. Sheet updates are an outbox and are retried on
the next run.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from automation_hub.tistory_local_adapter import TistoryLocalPublisher
from control_center.tistory import TistoryDraft
from gsheets_direct import get_sheets_service
from sync_automation_hub_to_sheets import ACCOUNTS_TAB, QUEUE_TAB


def records(values):
    if not values:
        return []
    header = values[0]
    return [(i, dict(zip(header, [*row, *([""] * (len(header) - len(row)))]))) for i, row in enumerate(values[1:], 2) if row]


def open_queue(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript("""
    CREATE TABLE IF NOT EXISTS jobs (
      job_id TEXT PRIMARY KEY, sheet_row INTEGER NOT NULL, site_id TEXT NOT NULL,
      payload TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
      edit_url TEXT NOT NULL DEFAULT '', remote_id TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS outbox (job_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
    """)
    db.execute("UPDATE jobs SET state='retry', error='recovered after interrupted local run', updated_at=CURRENT_TIMESTAMP WHERE state='running'")
    db.commit()
    return db


def _description(row):
    supplied = " ".join(str(row.get("search_description", "")).split())
    if supplied:
        return supplied
    text = html.unescape(re.sub(r"<[^>]+>", " ", row.get("content_html", "")))
    text = " ".join(text.split())
    return text[:147].rstrip(" ,.;:") + ("." if len(text) >= 70 else "")


def draft_from_row(row, site_url):
    labels = [x.strip() for x in row.get("labels", "").split(",") if x.strip()]
    return TistoryDraft(
        site_id=row["site_id"], site_url=site_url, title=row.get("title", ""),
        content_html=row.get("content_html", ""), category=row.get("category", "") or (labels[0] if labels else ""),
        search_description=_description(row), visibility="private",
    )


def sync_sheet_to_local(service, sheet_id, db, site_id=""):
    accounts = records(service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"'{ACCOUNTS_TAB}'!A1:I").execute().get("values", []))
    account_map = {r.get("site_id"): r for _, r in accounts if r.get("platform", "").lower() == "tistory" and r.get("enabled", "ON").upper() in {"ON", "TRUE", "1"}}
    queue = records(service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1:Q").execute().get("values", []))
    count = 0
    for row_no, row in queue:
        if row.get("site_id") not in account_map or (site_id and row.get("site_id") != site_id):
            continue
        if row.get("status", "").strip().lower() not in {"ready", "대기"}:
            continue
        payload = {**row, "site_url": account_map[row["site_id"]].get("editor_url", "")}
        cur = db.execute("INSERT OR IGNORE INTO jobs(job_id,sheet_row,site_id,payload) VALUES(?,?,?,?)", (row["job_id"], row_no, row["site_id"], json.dumps(payload, ensure_ascii=False)))
        count += cur.rowcount
    db.commit()
    return count


def queue_sheet_result(db, job_id, result):
    db.execute("INSERT OR REPLACE INTO outbox(job_id,payload) VALUES(?,?)", (job_id, json.dumps(result, ensure_ascii=False)))
    db.commit()


def flush_outbox(service, sheet_id, db):
    sent = 0
    for item in db.execute("SELECT job_id,payload FROM outbox ORDER BY job_id").fetchall():
        result = json.loads(item["payload"])
        row = db.execute("SELECT sheet_row FROM jobs WHERE job_id=?", (item["job_id"],)).fetchone()
        if not row:
            continue
        service.spreadsheets().values().batchUpdate(spreadsheetId=sheet_id, body={"valueInputOption": "RAW", "data": [
            {"range": f"'{QUEUE_TAB}'!D{row['sheet_row']}", "values": [[result["status"]]]},
            {"range": f"'{QUEUE_TAB}'!J{row['sheet_row']}:N{row['sheet_row']}", "values": [[result.get("edit_url", ""), result.get("post_id", ""), result.get("error_code", ""), result.get("message", ""), result.get("completed_at", "")]]},
        ]}).execute()
        db.execute("DELETE FROM outbox WHERE job_id=?", (item["job_id"],))
        sent += 1
    db.commit()
    return sent


def process_jobs(db, context, limit, gap_seconds):
    rows = db.execute("SELECT * FROM jobs WHERE state IN ('pending','retry') ORDER BY rowid LIMIT ?", (limit,)).fetchall()
    results = []
    for index, item in enumerate(rows):
        payload = json.loads(item["payload"])
        draft = draft_from_row(payload, payload["site_url"])
        db.execute("UPDATE jobs SET state='running',attempts=attempts+1,updated_at=CURRENT_TIMESTAMP WHERE job_id=?", (item["job_id"],)); db.commit()
        page = context.new_page()
        try:
            saved = TistoryLocalPublisher(draft).publish(page)
            result = {"status": "review_ready", "edit_url": saved.edit_url, "post_id": saved.post_id, "error_code": "", "message": "비공개 저장 및 재검증 완료", "completed_at": time.strftime("%Y-%m-%d %H:%M:%S")}
            db.execute("UPDATE jobs SET state='complete',edit_url=?,remote_id=?,error='',updated_at=CURRENT_TIMESTAMP WHERE job_id=?", (saved.edit_url, saved.post_id, item["job_id"]))
        except Exception as exc:
            result = {"status": "local_attention_required", "edit_url": "", "post_id": "", "error_code": "tistory_editor_error", "message": str(exc)[:500], "completed_at": time.strftime("%Y-%m-%d %H:%M:%S")}
            db.execute("UPDATE jobs SET state='retry',error=?,updated_at=CURRENT_TIMESTAMP WHERE job_id=?", (result["message"], item["job_id"]))
        finally:
            page.close(); db.commit()
        queue_sheet_result(db, item["job_id"], result)
        results.append({"job_id": item["job_id"], **result})
        if index + 1 < len(rows) and gap_seconds:
            time.sleep(gap_seconds)
    return results


def send_review_email(results):
    ready = [item for item in results if item.get("status") == "review_ready" and item.get("edit_url")]
    if not ready:
        return False
    try:
        from publishing_completion_notify import send_email
        body = "Tistory 비공개 초안 저장이 완료되었습니다.\n\n" + "\n\n".join(
            f"{item['job_id']}\n관리자 검토 링크: {item['edit_url']}" for item in ready
        )
        return send_email(f"[Tistory] 비공개 초안 {len(ready)}건 검토", body)
    except Exception as exc:
        print(f"검토 이메일 전송 대기: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["login", "run", "status"])
    parser.add_argument("--site-id", default="")
    parser.add_argument("--max-jobs", type=int, default=5)
    parser.add_argument("--gap-seconds", type=int, default=600)
    parser.add_argument("--queue-db", default=str(ROOT / ".local" / "tistory-queue.sqlite3"))
    parser.add_argument("--profile-root", default=str(ROOT / ".local" / "tistory-profile"))
    args = parser.parse_args()
    db = open_queue(Path(args.queue_db))
    if args.command == "status":
        print(json.dumps([dict(r) for r in db.execute("SELECT job_id,site_id,state,attempts,edit_url,error FROM jobs ORDER BY rowid")], ensure_ascii=False, indent=2)); return 0
    sheet_id = os.environ.get("SHEET_ID", "").strip()
    if not sheet_id:
        raise SystemExit("SHEET_ID가 필요합니다")
    service = get_sheets_service()
    sync_sheet_to_local(service, sheet_id, db, args.site_id)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(args.profile_root, headless=False, locale="ko-KR")
        if args.command == "login":
            page = context.pages[0] if context.pages else context.new_page(); page.goto("https://www.tistory.com/auth/login"); input("로그인을 마친 뒤 Enter: "); context.close(); return 0
        results = process_jobs(db, context, max(1, args.max_jobs), max(0, args.gap_seconds)); context.close()
    try:
        flush_outbox(service, sheet_id, db)
    except Exception as exc:
        print(f"Sheet 결과 동기화 대기(로컬 보존됨): {exc}")
    send_review_email(results)
    print(json.dumps(results, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
