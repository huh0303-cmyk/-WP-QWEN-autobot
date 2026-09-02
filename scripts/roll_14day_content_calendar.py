#!/usr/bin/env python3
"""Keep the CEO content calendar continuously filled through KST today + 13 days."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

from gsheets_direct import get_sheets_service

SHEET_ID = os.getenv("SHEET_ID", "12l1w6g-DF4YvVpkEx8YCEsIMTf7TXkUzANm3ldauYiI")
TAB = "14일_콘텐츠운영캘린더"
KST = dt.timezone(dt.timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from automation_hub.youtube_calendar import channel_key
HEADERS = [
    "schedule_id", "planned_at_kst", "platform", "channel_site", "destination_url",
    "language", "golden_keyword_candidate", "planned_title_direction", "content_format",
    "source_asset_plan", "dependency", "quality_gate", "current_status",
    "review_or_output_url", "notes",
]
EN_ANGLES = [
    "2026 practical guide", "costs and eligibility", "step-by-step checklist",
    "common mistakes to avoid", "official requirements", "beginner questions answered",
    "options compared", "seasonal update", "application timeline",
    "trusted official resources", "budget planning", "expert checklist",
    "myths and facts", "what changed in 2026",
]
KO_ANGLES = [
    "2026 실용 가이드", "비용과 자격 조건", "단계별 체크리스트", "자주 하는 실수",
    "공식 기준 확인", "초보자 질문과 답변", "선택지 비교", "계절별 최신 정보",
    "신청 일정 정리", "신뢰할 수 있는 공식 자료", "예산 계획", "전문가 체크리스트",
    "오해와 사실", "2026년 달라진 점",
]
YT_TOPICS = {
    "Cafe_Romantic": ["Multilingual acoustic love songs", "Sweet cafe love songs for two", "Black-and-white romance photo playlist"],
    "플리-힐링": ["Tropical rain with no music", "Forest stream and morning birds", "Temple rain and distant bells"],
    "플리-카페음악": ["Ocean-view cafe jazz", "Paris cafe jazz with a warm drink", "Iced citrus drink and coastal jazz"],
    "플리-MBB": ["Mozart for a calm morning", "Romantic cello pieces", "Classical music for a rainy day"],
    "플리-K-pop": ["Current K-pop discovery mix", "Bright Korean pop for commuting", "K-pop dance energy playlist"],
    "NASA & Space Times": ["Apollo 13 rescue using real NASA footage", "Voyager Golden Record archival story", "Hubble discoveries through official footage"],
    "Invention Times": ["The invention of television", "How refrigeration changed American homes", "The assembly line and manufacturing"],
    "Silent Era Times": ["Charlie Chaplin and The Tramp", "Buster Keaton silent-era moments", "Public-domain silent comedy showcase"],
    "Retro Reels Times": ["1950s American diners and faces", "The American road trip", "Household objects Americans remember"],
}


def stable_int(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:12], 16)


def irregular_time(key: str, start_minute=0, span=1440) -> str:
    total = start_minute + stable_int(key) % span
    hour, minute = divmod(total, 60)
    if minute % 5 == 0:
        minute = (minute + 1) % 60
    return f"{hour:02d}:{minute:02d}"


def load_rows(service):
    meta = service.spreadsheets().get(spreadsheetId=SHEET_ID, fields="sheets.properties").execute()
    count = next(s["properties"]["gridProperties"]["rowCount"] for s in meta["sheets"]
                 if s["properties"]["title"] == TAB)
    values = []
    for start in range(1, count + 1, 1000):
        end = min(start + 999, count)
        chunk = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID, range=f"'{TAB}'!A{start}:O{end}"
        ).execute().get("values", [])
        values.extend(chunk + [[]] * (end - start + 1 - len(chunk)))
    while values and not values[-1]:
        values.pop()
    return values


def wp_blogger_rows(target_date: dt.date, existing_keys: set[str]):
    portfolio = json.loads((ROOT / "config" / "blogger_portfolio.json").read_text(encoding="utf-8"))
    rows = []
    angle_index = (target_date - dt.date(2026, 8, 31)).days % 14
    for item in portfolio["channels"]:
        wp = item["wp"].removeprefix("https://").rstrip("/")
        lang, topic = item["language"], item["topic"]
        angle = (KO_ANGLES if lang == "ko" else EN_ANGLES)[angle_index]
        keyword = f"{topic} {angle}" if lang == "ko" else f"{topic}: {angle}"
        sensitive = any(x in topic.lower() for x in ("insurance", "finance", "medical", "visa", "tax", "law", "crypto", "건강", "뉴스"))
        source = "정부·공식기관 원문 필수" if sensitive else "공식기관·신뢰 출처 우선"
        for platform in ("WordPress", "Blogger"):
            identity = wp if platform == "WordPress" else wp.rsplit(".", 1)[0]
            key = f"{target_date}|{platform}|{identity}"
            if key in existing_keys:
                continue
            if platform == "WordPress":
                time_text = irregular_time(key, 0, 720)
                destination, fmt = item["wp"], "GPT 원문 기사"
                dependency, gate, status, notes = (
                    "SEO·출처·중복 검수 후 WP 먼저", "SEO≥70·공식출처·중복방지",
                    "황금키워드 검증대기", "실행 48시간 전 신호 재검증",
                )
                channel = wp
            else:
                time_text = irregular_time(key, 720, 700)
                destination, fmt = item["blogspot"], "GPT-5 mini 원고·Gemini 독립 검수"
                dependency, gate, status, notes = (
                    "동일 키워드 WP 발행·URL 검증 후", "SEO≥70·120자 설명·라벨8~14",
                    "WP 선행대기", "공개 금지·사람 검토용 초안",
                )
                channel = wp.rsplit(".", 1)[0]
            schedule_id = "ROLL-" + hashlib.sha1(key.encode()).hexdigest()[:10].upper()
            rows.append([
                schedule_id, f"{target_date} {time_text} KST", platform, channel, destination,
                lang, keyword, keyword, fmt, source, dependency, gate, status, "", notes,
            ])
    return rows


def youtube_rows(horizon: dt.date, existing, channels):
    rows = []
    used_slots = {
        (row[1][:10], row[1][11:16]) for row in existing
        if len(row) > 2 and row[2].startswith("YouTube")
    }
    for channel in channels:
        name = channel["display_name"]
        scheduled = sorted(
            (dt.date.fromisoformat(row[1][:10]), row[1][11:16]) for row in existing
            if len(row) > 3 and row[2].startswith("YouTube") and channel_key(row[3]) == channel["channel_key"]
        )
        due = scheduled[-1][0] if scheduled else dt.datetime.now(KST).date()
        previous_time = scheduled[-1][1] if scheduled else ""
        counter = len(scheduled)
        while True:
            gap_min = int(channel.get("interval_days_min", 2))
            gap_max = int(channel.get("interval_days_max", 3))
            if (gap_min, gap_max) != (2, 3):
                raise ValueError(f"{name}: YouTube cadence contract must be 2-3 days")
            gap = gap_min + stable_int(f"{name}|{due}|gap") % (gap_max - gap_min + 1)
            due += dt.timedelta(days=gap)
            if due > horizon:
                break
            platform = "YouTube Playlist" if channel["channel_type"] == "playlist" else "YouTube Knowledge"
            key = f"{due}|{platform}|{name}"
            topic_pool = YT_TOPICS.get(name, [])
            if name == "History Today Times":
                topic = f"{due.strftime('%B %d').upper()} — This Day in History (dated archive event)"
            else:
                topic = topic_pool[counter % len(topic_pool)] if topic_pool else channel["tone"]
            minute = irregular_time(key, channel["allowed_hour_start"] * 60,
                                    (channel["allowed_hour_end"] - channel["allowed_hour_start"] + 1) * 60)
            # A channel must not look like a fixed-time bot. If the deterministic
            # random slot repeats the previous run's HH:MM, reroll with a salt.
            salt = 1
            while (minute == previous_time or (due.isoformat(), minute) in used_slots) and salt <= 64:
                minute = irregular_time(f"{key}|reroll-{salt}", channel["allowed_hour_start"] * 60,
                                        (channel["allowed_hour_end"] - channel["allowed_hour_start"] + 1) * 60)
                salt += 1
            if minute == previous_time:
                raise RuntimeError(f"{name}: could not produce a different publication time")
            if (due.isoformat(), minute) in used_slots:
                raise RuntimeError(f"{name}: could not produce a collision-free publication time")
            is_knowledge = channel["channel_type"] == "knowledge"
            rows.append([
                "ROLL-" + hashlib.sha1(key.encode()).hexdigest()[:10].upper(),
                f"{due} {minute} KST", platform, name, "YouTube channel", channel["language"],
                topic, topic, "장편 지식 영상" if is_knowledge else "장시간 플레이리스트",
                "공식·퍼블릭도메인 영상 우선" if is_knowledge else "FLUX 실사형 이미지·채널별 오디오",
                "자료·권리·렌더 검증 후 비공개 업로드",
                "화면관련≥65·일치도≥80" if is_knowledge else "채널분리·실사품질·권리검수",
                "기획확정·자료준비", "", "비공개 링크 생성 후 토큰 없는 이메일 보고",
            ])
            previous_time = minute
            used_slots.add((due.isoformat(), minute))
            counter += 1
    return rows


def main():
    service = get_sheets_service()
    current = load_rows(service)
    if not current or current[0] != HEADERS:
        raise RuntimeError(f"{TAB} header mismatch; refusing destructive rewrite")
    data = current[1:]
    existing_keys = {
        f"{row[1][:10]}|{row[2]}|{row[3]}" for row in data if len(row) >= 4
    }
    today = dt.datetime.now(KST).date()
    horizon = today + dt.timedelta(days=13)
    new_rows = []
    for offset in range(14):
        new_rows.extend(wp_blogger_rows(today + dt.timedelta(days=offset), existing_keys))
    channels = json.loads((ROOT / "config" / "youtube_channels.json").read_text(encoding="utf-8"))["channels"]
    new_rows.extend(youtube_rows(horizon, data + new_rows, channels))
    if not new_rows:
        print(f"Calendar already covers {today} through {horizon}; no rows added")
        return
    new_rows.sort(key=lambda row: (row[1], row[2], row[3]))
    service.spreadsheets().values().append(
        spreadsheetId=SHEET_ID, range=f"'{TAB}'!A:O", valueInputOption="RAW",
        insertDataOption="INSERT_ROWS", body={"values": new_rows},
    ).execute()
    metadata = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    sheet_id = next(
        sheet["properties"]["sheetId"] for sheet in metadata["sheets"]
        if sheet["properties"]["title"] == TAB
    )
    start_row = len(current)
    end_row = start_row + len(new_rows)
    status_values = [
        "황금키워드 검증대기", "WP 선행대기", "기획확정·자료준비", "자료수집",
        "대본작성", "검수중", "비공개 업로드", "공개완료", "PASS", "보류", "실패",
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={"requests": [
            {"repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": start_row,
                          "endRowIndex": end_row, "startColumnIndex": 0, "endColumnIndex": 15},
                "cell": {"userEnteredFormat": {"verticalAlignment": "MIDDLE", "wrapStrategy": "WRAP"}},
                "fields": "userEnteredFormat(verticalAlignment,wrapStrategy)",
            }},
            {"setDataValidation": {
                "range": {"sheetId": sheet_id, "startRowIndex": start_row,
                          "endRowIndex": end_row, "startColumnIndex": 12, "endColumnIndex": 13},
                "rule": {"condition": {"type": "ONE_OF_LIST", "values": [
                    {"userEnteredValue": value} for value in status_values
                ]}, "strict": True, "showCustomUi": True},
            }},
            {"setBasicFilter": {"filter": {"range": {
                "sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": end_row,
                "startColumnIndex": 0, "endColumnIndex": 15,
            }}}},
        ]},
    ).execute()
    print(f"Added {len(new_rows)} calendar rows; rolling horizon={horizon}")


if __name__ == "__main__":
    main()
