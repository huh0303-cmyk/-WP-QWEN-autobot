#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
youtube_channels_daily.py
─────────────────────────────────────────────────────────────
21개 유튜브 채널의 구독자수/조회수/영상(콘텐츠)수를 한 번의 API 호출로
전부 조회해서 "21개유튜브채널현황" 탭에 날짜별 컬럼으로 누적 기록한다.
매일 한국시간(KST) 오전 7시 실행 예정(스케줄 작업으로 등록).

기존 탭 구조(A열=채널명 고정, 날짜마다 오른쪽에 새 컬럼 블록 추가)를 그대로
따른다 — append_dated_metric_columns가 그 로직을 담당한다.
"""
import os
import sys
from datetime import datetime, timezone, timedelta

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_env():
    d = {}
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            d[k] = v
    return d


_env = load_env()
for k, v in _env.items():
    os.environ.setdefault(k, v)

sys.path.insert(0, os.path.dirname(__file__))
from situation_room_daily import YOUTUBE_CHANNELS  # noqa: E402
from gsheets_direct import append_dated_metric_columns, get_sheets_service, _col_letter  # noqa: E402

SPREADSHEET_ID = "12l1w6g-DF4YvVpkEx8YCEsIMTf7TXkUzANm3ldauYiI"
TAB_NAME = "21개유튜브채널현황"
KST = timezone(timedelta(hours=9))


def log(msg):
    print(msg, flush=True)


def fetch_all_stats():
    ids = [cid for _, cid in YOUTUBE_CHANNELS]
    oauth_token_env = None
    for env_name in os.environ:
        if env_name.startswith("YOUTUBE_OAUTH_REFRESH_TOKEN_") and env_name.endswith("_BROAD"):
            oauth_token_env = env_name
            break
    if not oauth_token_env:
        raise RuntimeError("broad-scope YOUTUBE_OAUTH_REFRESH_TOKEN_*_BROAD 없음")

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=os.environ[oauth_token_env],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube"],
    )
    youtube = build("youtube", "v3", credentials=creds)

    items = {}
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        resp = youtube.channels().list(part="statistics", id=",".join(chunk)).execute()
        for it in resp.get("items", []):
            items[it["id"]] = it
    return items


def _leading_int(cell):
    """'5750 (+2)' 같은 셀에서 앞의 숫자만 뽑아 int로 반환. 빈칸/파싱 불가면 None."""
    if not cell:
        return None
    head = str(cell).split(" ")[0].replace(",", "")
    try:
        return int(head)
    except ValueError:
        return None


def fetch_previous_block(domains):
    """마지막으로 기록된 날짜 블록의 구독자수/조회수/영상수 값을 읽어와
    {채널명: (구독자수, 조회수, 영상수)} 형태로 돌려준다 — 오늘 값과 비교해
    "(증감)" 표기를 직접 계산하기 위함(시트 수식이 아니라 파이썬에서 계산해
    고정값으로 기록). 각 셀은 '5750 (+2)' 형식이라 앞 숫자만 파싱한다."""
    service = get_sheets_service()
    row1 = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"'{TAB_NAME}'!1:1",
    ).execute().get("values", [[]])
    row1_vals = row1[0] if row1 else []
    last_label_col = None
    for idx in range(len(row1_vals) - 1, -1, -1):
        if row1_vals[idx]:
            last_label_col = idx
            break
    if last_label_col is None:
        return {}

    start_letter = _col_letter(last_label_col)
    end_letter = _col_letter(last_label_col + 2)
    resp = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{TAB_NAME}'!{start_letter}3:{end_letter}30",
    ).execute().get("values", [])

    domain_col = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"'{TAB_NAME}'!B3:B30",
    ).execute().get("values", [])

    result = {}
    for i, row in enumerate(resp):
        if i >= len(domain_col) or not domain_col[i]:
            continue
        label = domain_col[i][0]
        vals = [_leading_int(row[j]) if j < len(row) else None for j in range(3)]
        result[label] = tuple(vals)
    return result


def fetch_sheet_row_order():
    """B열(채널명)의 현재 실제 행 순서를 그대로 읽어온다 — 시트가 카테고리별로
    재정렬되어 있을 수 있어(YOUTUBE_CHANNELS 원본 순서와 다름), 데이터를 엉뚱한
    행에 쓰지 않으려면 반드시 시트에 있는 실제 순서를 기준으로 채워야 한다."""
    service = get_sheets_service()
    col = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"'{TAB_NAME}'!B3:B30",
    ).execute().get("values", [])
    return [row[0] for row in col if row]


def main():
    log("21개 채널 통계 조회 중...")
    items = fetch_all_stats()
    domains = fetch_sheet_row_order()
    if not domains:
        domains = [label for label, _ in YOUTUBE_CHANNELS]
    prev = fetch_previous_block(domains)

    def _fmt(value, prev_value):
        if value is None:
            return ""
        if prev_value is None:
            return f"{value} (0)"
        return f"{value} ({value - prev_value:+d})"

    values_by_domain = {}
    missing = []
    for label, cid in YOUTUBE_CHANNELS:
        it = items.get(cid)
        if not it:
            missing.append(label)
            values_by_domain[label] = ["", "", ""]
            continue
        stats = it["statistics"]
        sub = None if stats.get("hiddenSubscriberCount") else int(stats.get("subscriberCount", 0))
        views = int(stats.get("viewCount", 0))
        videos = int(stats.get("videoCount", 0))

        prev_sub, prev_views, prev_videos = prev.get(label, (None, None, None))
        values_by_domain[label] = [
            _fmt(sub, prev_sub),
            _fmt(views, prev_views),
            _fmt(videos, prev_videos),
        ]

    if missing:
        log(f"⚠️ 조회 실패: {missing}")

    now = datetime.now(KST)
    date_label = f"{now.year}-{now.month}-{now.day}-{'월화수목금토일'[now.weekday()]}"

    log(f"시트에 기록 중... ({date_label})")
    append_dated_metric_columns(
        SPREADSHEET_ID, TAB_NAME, domains, date_label,
        ["구독자수", "조회수", "영상수"],
        values_by_domain,
    )
    log("✅ 완료")


if __name__ == "__main__":
    main()
