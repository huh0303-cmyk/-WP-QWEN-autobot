#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gsheets_direct.py
─────────────────────────────────────────────────────────────
Google Sheets API로 직접 쓰는 공용 헬퍼. daily_site_traffic.py /
situation_room_daily.py가 기존에 의존하던 SHEETS_WEBHOOK(정체불명의
Apps Script 웹훅)이 site_traffic_daily/situation_room 타입을 실제로는
어느 탭에도 기록하지 않는 것으로 확인되어(수신은 HTTP 200으로 성공
응답하지만 대상 스프레드시트에 해당 탭이 전혀 생성되지 않음), 대신
이미 다른 스크립트(youtube_playlist_maker.py 등)에서 쓰고 있는
GOOGLE_OAUTH_* 자격증명으로 Sheets API에 바로 쓰도록 만든 모듈.

필요 환경변수:
    GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET / GOOGLE_OAUTH_REFRESH_TOKEN
    SHEET_ID - 대상 스프레드시트 ID
"""
import os

GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REFRESH_TOKEN = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "")


def has_credentials():
    return bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET and GOOGLE_OAUTH_REFRESH_TOKEN)


def get_sheets_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_OAUTH_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_OAUTH_CLIENT_ID,
        client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return build("sheets", "v4", credentials=creds)


def _get_tab_id(service, spreadsheet_id, tab_name):
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in meta.get("sheets", []):
        if sheet["properties"]["title"] == tab_name:
            return sheet["properties"]["sheetId"]
    return None


def ensure_tab(service, spreadsheet_id, tab_name, header):
    """탭이 없으면 새로 만들고 헤더 행을 써넣는다. 이미 있으면 아무것도 하지 않는다."""
    tab_id = _get_tab_id(service, spreadsheet_id, tab_name)
    if tab_id is not None:
        return tab_id
    resp = service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [{"addSheet": {"properties": {"title": tab_name}}}]},
    ).execute()
    new_tab_id = resp["replies"][0]["addSheet"]["properties"]["sheetId"]
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{tab_name}'!A1",
        valueInputOption="RAW",
        body={"values": [header]},
    ).execute()
    return new_tab_id


def replace_tab_rows(spreadsheet_id, tab_name, header, rows):
    """탭을 "현재 상태 스냅샷" 표로 유지 — 헤더 아래 데이터 전체를 매번
    지우고 새로 쓴다(계속 쌓이는 로그가 아니라 27개 사이트처럼 매일 같은
    행 수를 유지하는 현황판에 적합)."""
    service = get_sheets_service()
    ensure_tab(service, spreadsheet_id, tab_name, header)
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=f"'{tab_name}'!A2:Z",
    ).execute()
    if rows:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{tab_name}'!A2",
            valueInputOption="RAW",
            body={"values": rows},
        ).execute()


def append_tab_row(spreadsheet_id, tab_name, header, row):
    """탭을 계속 쌓이는 로그로 유지 — 종합상황실처럼 어제 대비 증감을
    비교해야 하는 일별 기록에 적합."""
    service = get_sheets_service()
    ensure_tab(service, spreadsheet_id, tab_name, header)
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"'{tab_name}'!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()
