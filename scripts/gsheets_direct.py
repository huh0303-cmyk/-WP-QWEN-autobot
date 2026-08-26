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
import json
from pathlib import Path

GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REFRESH_TOKEN = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "")


def has_credentials():
    return bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET and GOOGLE_OAUTH_REFRESH_TOKEN) or _local_credentials_path().exists()


def _local_credentials_path():
    configured = os.environ.get("GOOGLE_LOCAL_OAUTH_FILE", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / ".local" / "google_sheets_oauth.json"


def _credential_values():
    if GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET and GOOGLE_OAUTH_REFRESH_TOKEN:
        return GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REFRESH_TOKEN
    path = _local_credentials_path()
    if not path.exists():
        return "", "", ""
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("client_id", ""), data.get("client_secret", ""), data.get("refresh_token", "")


def get_sheets_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    client_id, client_secret, refresh_token = _credential_values()
    if not all((client_id, client_secret, refresh_token)):
        raise RuntimeError("Google Sheets OAuth가 없습니다. scripts/setup_google_sheets_local.py를 먼저 실행하세요.")
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
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
            spreadsheetId=spreadsheet_id, range=f"'{tab_name}'!A1:AZ1",
        ).execute().get("values", [[]])
        existing_header = existing[0] if existing else []
        if existing_header == header:
            return tab_id
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id, range=f"'{tab_name}'!A1:AZ",
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


def append_or_update_tab_row(spreadsheet_id, tab_name, header, row, key_col_idx=0):
    """append_tab_row와 같지만, 마지막 행의 key_col_idx 값이 이번 row의 같은
    값과 일치하면(=같은 날짜에 워크플로가 여러 번 실행됨) 새로 추가하지 않고
    그 행을 덮어쓴다. 수동 재실행/재시도로 같은 날짜 행이 중복 쌓이는 것을 막는다."""
    service = get_sheets_service()
    ensure_tab(service, spreadsheet_id, tab_name, header)

    existing = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=f"'{tab_name}'!A1:Z",
    ).execute().get("values", [])

    key = row[key_col_idx]
    if len(existing) > 1:
        last_row = existing[-1]
        last_key = last_row[key_col_idx] if len(last_row) > key_col_idx else None
        if last_key == key:
            last_row_num = len(existing)
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{tab_name}'!A{last_row_num}",
                valueInputOption="RAW",
                body={"values": [row]},
            ).execute()
            return

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
        row1_vals = row1[0] if row1 else []
        existing_width = len(row1_vals)

        # 마지막 날짜 블록 라벨이 이번 date_label과 같으면(워크플로가 같은 날
        # 여러 번 실행됨) 새 컬럼을 추가하지 않고 그 블록을 그대로 덮어쓴다.
        last_label_col = None
        for idx in range(len(row1_vals) - 1, -1, -1):
            if row1_vals[idx]:
                last_label_col = idx
                break
        if last_label_col is not None and row1_vals[last_label_col] == date_label:
            start_col = last_label_col
        else:
            start_col = max(existing_width, 1)

    end_col = start_col + n_metrics - 1
    start_letter = _col_letter(start_col)

    # ★ 2026-08-09: mergeCells가 기존에 남아있던 다른 병합범위와 "부분적으로만"
    #   겹치면 400 에러를 던지는데, 이게 배치 요청 안에서 터지면 뒤에 있는 실제
    #   값 쓰기까지 통째로 실행이 안 돼서 그날 데이터가 시트에 한 줄도 안
    #   들어가는 사고로 이어졌다(27개사이트_트래픽 탭에서 실제 발생).
    #   그래서 병합은 맨 마지막으로 옮기고, 실패해도 실제 값 쓰기는 이미
    #   끝난 뒤라 영향이 없도록 try/except로 감싼다.
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

    if n_metrics > 1:
        try:
            meta = service.spreadsheets().get(
                spreadsheetId=spreadsheet_id, ranges=[f"'{tab_name}'!1:1"],
                fields="sheets(merges)",
            ).execute()
            merges = meta.get("sheets", [{}])[0].get("merges", [])
            unmerge_requests = []
            for m in merges:
                if m.get("startRowIndex", 0) == 0 and m.get("endRowIndex", 1) == 1:
                    if m.get("startColumnIndex", 0) < end_col + 1 and m.get("endColumnIndex", 0) > start_col:
                        unmerge_requests.append({"unmergeCells": {"range": m}})
            requests_batch = unmerge_requests + [{
                "mergeCells": {
                    "range": {"sheetId": tab_id, "startRowIndex": 0, "endRowIndex": 1,
                              "startColumnIndex": start_col, "endColumnIndex": end_col + 1},
                    "mergeType": "MERGE_ALL",
                },
            }]
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body={"requests": requests_batch},
            ).execute()
        except Exception:
            pass
