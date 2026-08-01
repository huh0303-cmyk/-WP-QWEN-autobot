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
        # 이 리프레시 토큰은 원래 "drive" 스코프로만 발급됨(youtube_playlist_maker.py
        # 등 다른 스크립트와 공용) — 여기서 다른 스코프를 지정하면 리프레시 자체가
        # invalid_scope로 거부된다. Sheets API는 drive 스코프도 유효하게 인정한다.
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("sheets", "v4", credentials=creds)


def _get_tab_id(service, spreadsheet_id, tab_name):
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    for sheet in meta.get("sheets", []):
        if sheet["properties"]["title"] == tab_name:
            return sheet["properties"]["sheetId"]
    return None


def ensure_tab(service, spreadsheet_id, tab_name, header):
    """탭이 없으면 새로 만들고 헤더 행을 써넣는다. 이미 있는데 헤더 구성이
    바뀌었으면(컬럼 추가/삭제 등) 예전 데이터와 안 섞이게 탭을 통째로
    비우고 새 헤더로 다시 시작한다."""
    tab_id = _get_tab_id(service, spreadsheet_id, tab_name)
    if tab_id is not None:
        existing = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=f"'{tab_name}'!A1:Z1",
        ).execute().get("values", [[]])
        existing_header = existing[0] if existing else []
        if existing_header == header:
            return tab_id
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id, range=f"'{tab_name}'!A1:Z",
        ).execute()
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{tab_name}'!A1",
            valueInputOption="RAW",
            body={"values": [header]},
        ).execute()
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
    """탭을 "현재 상태 스냅샷" 표로 유지 — 헤더 포함 전체를 매번 지우고
    새로 쓴다(계속 쌓이는 로그가 아니라 27개 사이트처럼 매일 같은 행
    수를 유지하는 현황판에 적합). 헤더도 매번 다시 쓰므로 컬럼 구성이
    바뀌어도(예: 컬럼 축소) 예전 헤더/데이터가 옆에 남지 않는다."""
    service = get_sheets_service()
    ensure_tab(service, spreadsheet_id, tab_name, header)
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range=f"'{tab_name}'!A1:Z",
    ).execute()
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{tab_name}'!A1",
        valueInputOption="RAW",
        body={"values": [header] + rows},
    ).execute()


def append_tab_row(spreadsheet_id, tab_name, header, row):
    """탭을 계속 쌓이는 로그로 유지 — 종합상황실처럼 어제 대비 증감을
    비교해야 하는 일별 기록에 적합."""
    append_tab_rows(spreadsheet_id, tab_name, header, [row])


def append_tab_rows(spreadsheet_id, tab_name, header, rows):
    """append_tab_row의 여러 행 버전 — 27개 사이트처럼 하루에 여러 행을
    한 번에 쌓아서, 날짜별로 쭉 이어지는 기록으로 날짜 간 비교가
    가능하게 한다."""
    service = get_sheets_service()
    ensure_tab(service, spreadsheet_id, tab_name, header)
    if not rows:
        return
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"'{tab_name}'!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": rows},
    ).execute()


def _col_letter(idx0):
    """0-기준 컬럼 인덱스를 A1 표기 문자로 변환 (0->A, 1->B, 26->AA ...)."""
    s = ""
    idx = idx0 + 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        s = chr(65 + rem) + s
    return s


def append_dated_metric_columns(spreadsheet_id, tab_name, domains, date_label, metric_labels, values_by_domain):
    """기존 "Youtube-tiktok" 탭과 같은 구조 — A열에 항목(사이트 도메인)을
    세로로 한 번만 고정해두고, 새 날짜가 생길 때마다 오른쪽에 그 날짜용
    컬럼 묶음(metric_labels 개수만큼, 예: 일일방문자수/색인수)을 추가한다.
    1행=날짜(병합), 2행=지표 라벨, 3행부터=도메인별 값.

    values_by_domain: {도메인: [지표1값, 지표2값, ...]} — domains 순서와
    무관하게 딕셔너리로 넘기면 도메인 순서에 맞춰 정렬해서 채운다."""
    service = get_sheets_service()
    n_metrics = len(metric_labels)
    tab_id = _get_tab_id(service, spreadsheet_id, tab_name)

    if tab_id is not None:
        # 이전 구조(행 기반 로그 등)가 남아있으면 A1이 비어있지 않다 — 이 구조는
        # A1을 항상 비워두므로, A1에 값이 있으면 옛날 구조로 보고 통째로 다시 만든다.
        a1 = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=f"'{tab_name}'!A1",
        ).execute().get("values", [[]])
        if a1 and a1[0] and a1[0][0]:
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": [{"deleteSheet": {"sheetId": tab_id}}]},
            ).execute()
            tab_id = None

    if tab_id is None:
        resp = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": tab_name}}}]},
        ).execute()
        tab_id = resp["replies"][0]["addSheet"]["properties"]["sheetId"]
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{tab_name}'!A3",
            valueInputOption="RAW",
            body={"values": [[d] for d in domains]},
        ).execute()
        start_col = 1  # B열(0-기준 인덱스 1)부터 시작
    else:
        row1 = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=f"'{tab_name}'!1:1",
        ).execute().get("values", [[]])
        existing_width = len(row1[0]) if row1 else 0
        start_col = max(existing_width, 1)

    end_col = start_col + n_metrics - 1
    start_letter = _col_letter(start_col)

    if n_metrics > 1:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{
                "mergeCells": {
                    "range": {"sheetId": tab_id, "startRowIndex": 0, "endRowIndex": 1,
                              "startColumnIndex": start_col, "endColumnIndex": end_col + 1},
                    "mergeType": "MERGE_ALL",
                },
            }]},
        ).execute()

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id, range=f"'{tab_name}'!{start_letter}1",
        valueInputOption="RAW", body={"values": [[date_label]]},
    ).execute()
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id, range=f"'{tab_name}'!{start_letter}2",
        valueInputOption="RAW", body={"values": [metric_labels]},
    ).execute()

    data_rows = [values_by_domain.get(d, [""] * n_metrics) for d in domains]
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id, range=f"'{tab_name}'!{start_letter}3",
        valueInputOption="RAW", body={"values": data_rows},
    ).execute()
