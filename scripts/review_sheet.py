"""Write every generated review draft to the main Google Sheets review tab."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone


TAB_NAME = "오늘_글검수"
HEADER = ["작성시각(KST)", "플랫폼", "채널", "제목", "글 보기", "상태", "승인결정", "작업기록", "비고"]
KST = timezone(timedelta(hours=9))


def append_review_rows(rows: list[dict]) -> bool:
    sheet_id = os.environ.get("SHEET_ID", "").strip()
    if not sheet_id or not rows:
        return False
    try:
        from scripts.gsheets_direct import ensure_tab, get_sheets_service

        service = get_sheets_service()
        ensure_tab(service, sheet_id, TAB_NAME, HEADER)
        current = service.spreadsheets().values().get(
            spreadsheetId=sheet_id, range=f"'{TAB_NAME}'!A1:I500"
        ).execute().get("values", [])
        existing_links = {r[4] for r in current[1:] if len(r) > 4 and r[4]}
        values = []
        for row in rows:
            link = str(row.get("review_url") or "")
            if not link or link in existing_links:
                continue
            values.append([
                row.get("created_at") or datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S"),
                row.get("platform", ""), row.get("channel", ""), row.get("title", ""), link,
                row.get("status", "비공개 초안"), row.get("decision", "검토대기"),
                row.get("run_url", ""), row.get("note", ""),
            ])
        if not values:
            return True
        if len(current) == 2 and len(current[1]) > 3 and current[1][3] == "현재 시트 연결 이후 수집된 글 없음":
            service.spreadsheets().values().clear(
                spreadsheetId=sheet_id, range=f"'{TAB_NAME}'!A2:I2"
            ).execute()
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id, range=f"'{TAB_NAME}'!A1",
            valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
            body={"values": values},
        ).execute()
        return True
    except Exception as exc:
        print(f"review sheet sync skipped without affecting drafts: {exc}")
        return False
