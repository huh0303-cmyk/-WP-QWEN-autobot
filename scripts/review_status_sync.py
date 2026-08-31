#!/usr/bin/env python3
"""Keep the mobile review sheet split into pending, approved and rejected views."""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests

from scripts.gsheets_direct import ensure_tab, get_sheets_service
from scripts.review_sheet import HEADER, TAB_NAME
from scripts.site_registry import SITES

KST = timezone(timedelta(hours=9))
WP_USER = "huh0303@gmail.com"
VIEW_TABS = {
    "승인대기": "검토대기",
    "승인완료": "승인완료",
    "반려": "반려",
}


def approval_state(wp_status: str) -> tuple[str, str]:
    """Return the human-facing post status and approval decision."""
    return {
        "publish": ("공개", "승인완료"),
        "future": ("예약공개", "승인완료"),
        "trash": ("휴지통", "반려"),
        "draft": ("비공개 초안", "검토대기"),
        "pending": ("승인대기 초안", "검토대기"),
        "private": ("비공개", "검토대기"),
    }.get(wp_status, (wp_status or "확인불가", "검토대기"))


def parse_review_url(value: str) -> tuple[str, int] | None:
    parsed = urlparse(value or "")
    match = re.search(r"(?:^|[?&])post=(\d+)", parsed.query)
    if not parsed.netloc or not match:
        return None
    return f"{parsed.scheme or 'https'}://{parsed.netloc}", int(match.group(1))


def _credential_map() -> dict[str, str]:
    return {urlparse(url).netloc: os.getenv(secret, "").strip() for url, secret, _ in SITES}


def _wp_status(site_url: str, post_id: int, password: str) -> tuple[str, str]:
    if not password:
        return "", ""
    response = requests.get(
        f"{site_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}",
        auth=(WP_USER, password),
        params={"context": "edit", "_fields": "status,modified_gmt"},
        timeout=20,
    )
    if response.status_code == 404:
        # A 404 can also mean that REST access/authentication is unavailable.
        # Never turn an access failure into a false user rejection.
        return "", ""
    response.raise_for_status()
    payload = response.json()
    return str(payload.get("status", "")), str(payload.get("modified_gmt", ""))


def _format_dashboard(service, sheet_id: str, tab_id: int, row_count: int) -> None:
    end_row = max(row_count, 2)
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id, range=f"'{TAB_NAME}'!K1:L5", valueInputOption="USER_ENTERED",
        body={"values": [
            ["승인 현황", "개수"],
            ["승인 대기", f'=COUNTIF(G2:G,"검토대기")'],
            ["승인 완료", f'=COUNTIF(G2:G,"승인완료")'],
            ["반려", f'=COUNTIF(G2:G,"반려")'],
            ["전체", "=COUNTA(D2:D)"],
        ]},
    ).execute()
    metadata = service.spreadsheets().get(
        spreadsheetId=sheet_id,
        fields="sheets(properties(sheetId),conditionalFormats)",
    ).execute()
    old_rule_count = 0
    for sheet in metadata.get("sheets", []):
        if sheet.get("properties", {}).get("sheetId") == tab_id:
            old_rule_count = len(sheet.get("conditionalFormats", []))
            break
    requests_batch = [
        *({"deleteConditionalFormatRule": {"sheetId": tab_id, "index": 0}} for _ in range(old_rule_count)),
        {"updateSheetProperties": {"properties": {"sheetId": tab_id, "gridProperties": {"frozenRowCount": 1}}, "fields": "gridProperties.frozenRowCount"}},
        {"setBasicFilter": {"filter": {"range": {"sheetId": tab_id, "startRowIndex": 0, "endRowIndex": end_row, "startColumnIndex": 0, "endColumnIndex": 9}}}},
        {"repeatCell": {"range": {"sheetId": tab_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 9}, "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.10, "green": 0.22, "blue": 0.36}, "textFormat": {"foregroundColor": {"red": 1, "green": 1, "blue": 1}, "bold": True}}}, "fields": "userEnteredFormat"}},
        {"setDataValidation": {"range": {"sheetId": tab_id, "startRowIndex": 1, "endRowIndex": end_row, "startColumnIndex": 6, "endColumnIndex": 7}, "rule": {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": "검토대기"}, {"userEnteredValue": "승인완료"}, {"userEnteredValue": "반려"}]}, "showCustomUi": True, "strict": True}}},
    ]
    colors = {
        "검토대기": {"red": 1.0, "green": 0.91, "blue": 0.55},
        "승인완료": {"red": 0.72, "green": 0.92, "blue": 0.78},
        "반려": {"red": 0.96, "green": 0.72, "blue": 0.72},
    }
    for label, color in colors.items():
        requests_batch.append({"addConditionalFormatRule": {"index": 0, "rule": {"ranges": [{"sheetId": tab_id, "startRowIndex": 1, "endRowIndex": end_row, "startColumnIndex": 6, "endColumnIndex": 7}], "booleanRule": {"condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": label}]}, "format": {"backgroundColor": color, "textFormat": {"bold": True}}}}}})
    service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": requests_batch}).execute()


def _build_view_tabs(service, sheet_id: str) -> None:
    for tab_name, decision in VIEW_TABS.items():
        tab_id = ensure_tab(service, sheet_id, tab_name, HEADER)
        service.spreadsheets().values().clear(spreadsheetId=sheet_id, range=f"'{tab_name}'!A1:I").execute()
        formula = f'=QUERY(\'{TAB_NAME}\'!A:I,"select * where G = \'{decision}\'",1)'
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id, range=f"'{tab_name}'!A1", valueInputOption="USER_ENTERED",
            body={"values": [[formula]]},
        ).execute()
        service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": [
            {"updateSheetProperties": {"properties": {"sheetId": tab_id, "gridProperties": {"frozenRowCount": 1}}, "fields": "gridProperties.frozenRowCount"}},
        ]}).execute()


def sync() -> dict[str, int]:
    sheet_id = os.environ["SHEET_ID"]
    service = get_sheets_service()
    tab_id = ensure_tab(service, sheet_id, TAB_NAME, HEADER)
    values = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{TAB_NAME}'!A1:I5000"
    ).execute().get("values", [])
    credentials = _credential_map()
    counts = {"검토대기": 0, "승인완료": 0, "반려": 0, "확인불가": 0}
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")
    for index, raw in enumerate(values[1:], start=2):
        row = raw + [""] * (9 - len(raw))
        parsed = parse_review_url(row[4])
        if row[1] != "WordPress" or not parsed:
            counts[row[6] if row[6] in counts else "확인불가"] += 1
            continue
        site_url, post_id = parsed
        try:
            wp_status, modified = _wp_status(site_url, post_id, credentials.get(urlparse(site_url).netloc, ""))
            if not wp_status:
                counts["확인불가"] += 1
                continue
            display, decision = approval_state(wp_status)
            note = row[8]
            if decision != row[6]:
                note = f"{decision} 자동확인: {now}" + (f" (WP 수정: {modified})" if modified else "")
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id, range=f"'{TAB_NAME}'!F{index}:I{index}", valueInputOption="RAW",
                body={"values": [[display, decision, row[7], note]]},
            ).execute()
            counts[decision] += 1
        except Exception as exc:
            print(f"row {index} sync skipped: {exc}")
            counts["확인불가"] += 1
    _format_dashboard(service, sheet_id, tab_id, len(values))
    _build_view_tabs(service, sheet_id)
    print(counts)
    return counts


if __name__ == "__main__":
    sync()
