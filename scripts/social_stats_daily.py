#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
social_stats_daily.py
─────────────────────────────────────────────────────────────
유튜브 / 틱톡 / 페이스북 / 인스타그램 / Threads 팔로워(구독자) 수를
매일 수집해서 구글시트 웹훅으로 전송한다.

각 플랫폼은 독립적으로 실패해도 나머지에 영향 없이 계속 진행되며,
결과는 social_stats_result.json 으로도 저장되어 커밋된다
(과거 기록 확인 + 다음날 diff 비교용).

필요 환경변수(Secrets) — 없는 항목은 자동 스킵(에러 아님):
    SHEETS_WEBHOOK_SOCIAL / SHEETS_WEBHOOK  - 구글시트 전송 웹훅 (둘 중 하나)

    YOUTUBE_API_KEY       - YouTube Data API v3 키
    YOUTUBE_CHANNEL_ID    - 채널 ID (UC로 시작)

    TIKTOK_USERNAME       - 틱톡 사용자명 (@ 없이)

    FB_PAGE_ACCESS_TOKEN  - 페이스북 페이지 액세스 토큰
    FB_PAGE_ID            - 페이스북 페이지 ID

    IG_ACCESS_TOKEN       - 인스타그램(비즈니스 계정) 액세스 토큰
                            (없으면 FB_PAGE_ACCESS_TOKEN 재사용 시도)
    IG_USER_ID            - 인스타그램 비즈니스 계정 ID

    THREADS_ACCESS_TOKEN  - Threads 액세스 토큰
    THREADS_USER_ID       - Threads 사용자 ID
"""

import os
import re
import json
from datetime import datetime, timezone, timedelta

import requests

KST = timezone(timedelta(hours=9))


def today_kst():
    return datetime.now(KST).strftime("%Y-%m-%d")


def log(msg):
    print(msg, flush=True)


# ════════════════════════════════════════════════════════════
# 플랫폼별 수집 함수 — 실패해도 예외를 던지지 않고 None 반환
# ════════════════════════════════════════════════════════════
def get_youtube_subscribers():
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    channel_id = os.getenv("YOUTUBE_CHANNEL_ID", "")
    if not api_key or not channel_id:
        return None, "YOUTUBE_API_KEY 또는 YOUTUBE_CHANNEL_ID 없음"
    try:
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "statistics", "id": channel_id, "key": api_key},
            timeout=15,
        )
        r.raise_for_status()
        items = r.json().get("items", [])
        if not items:
            return None, "채널을 찾을 수 없음"
        count = int(items[0]["statistics"]["subscriberCount"])
        return count, None
    except Exception as e:
        return None, str(e)[:200]


def get_tiktok_followers():
    """공식 무료 API가 없어 공개 프로필 페이지에서 SIGI_STATE JSON을 파싱(best-effort)."""
    username = os.getenv("TIKTOK_USERNAME", "")
    if not username:
        return None, "TIKTOK_USERNAME 없음"
    try:
        r = requests.get(
            f"https://www.tiktok.com/@{username}",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=15,
        )
        r.raise_for_status()
        m = re.search(r'"followerCount":(\d+)', r.text)
        if not m:
            return None, "followerCount 파싱 실패 (틱톡 페이지 구조 변경 가능성)"
        return int(m.group(1)), None
    except Exception as e:
        return None, str(e)[:200]


def get_facebook_followers():
    token = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
    page_id = os.getenv("FB_PAGE_ID", "")
    if not token or not page_id:
        return None, "FB_PAGE_ACCESS_TOKEN 또는 FB_PAGE_ID 없음"
    try:
        r = requests.get(
            f"https://graph.facebook.com/v21.0/{page_id}",
            params={"fields": "followers_count,fan_count", "access_token": token},
            timeout=15,
        )
        data = r.json()
        if "error" in data:
            return None, data["error"].get("message", "알 수 없는 오류")[:200]
        count = data.get("followers_count", data.get("fan_count"))
        return count, None
    except Exception as e:
        return None, str(e)[:200]


def get_instagram_followers():
    token = os.getenv("IG_ACCESS_TOKEN", "") or os.getenv("FB_PAGE_ACCESS_TOKEN", "")
    ig_user_id = os.getenv("IG_USER_ID", "")
    if not token or not ig_user_id:
        return None, "IG_ACCESS_TOKEN(또는 FB_PAGE_ACCESS_TOKEN) 또는 IG_USER_ID 없음"
    try:
        r = requests.get(
            f"https://graph.facebook.com/v21.0/{ig_user_id}",
            params={"fields": "followers_count", "access_token": token},
            timeout=15,
        )
        data = r.json()
        if "error" in data:
            return None, data["error"].get("message", "알 수 없는 오류")[:200]
        return data.get("followers_count"), None
    except Exception as e:
        return None, str(e)[:200]


def get_threads_followers():
    token = os.getenv("THREADS_ACCESS_TOKEN", "")
    user_id = os.getenv("THREADS_USER_ID", "")
    if not token or not user_id:
        return None, "THREADS_ACCESS_TOKEN 또는 THREADS_USER_ID 없음"
    try:
        r = requests.get(
            f"https://graph.threads.net/v1.0/{user_id}/threads_insights",
            params={"metric": "followers_count", "access_token": token},
            timeout=15,
        )
        data = r.json()
        if "error" in data:
            return None, data["error"].get("message", "알 수 없는 오류")[:200]
        values = data.get("data", [])
        if values and values[0].get("total_value"):
            return values[0]["total_value"].get("value"), None
        return None, "followers_count 값 없음 (Threads API 응답 형식 변경 가능성)"
    except Exception as e:
        return None, str(e)[:200]


# ════════════════════════════════════════════════════════════
# 시트 전송
# ════════════════════════════════════════════════════════════
def send_to_sheets(records):
    webhook = os.getenv("SHEETS_WEBHOOK_SOCIAL", "") or os.getenv("SHEETS_WEBHOOK", "")
    if not webhook:
        log("⚠️ SHEETS_WEBHOOK_SOCIAL / SHEETS_WEBHOOK 둘 다 없음 — 시트 전송 스킵")
        return
    try:
        r = requests.post(webhook, json={"type": "sns_stats", "records": records}, timeout=20)
        log(f"📊 구글시트 전송 완료 ({len(records)}건) HTTP {r.status_code}")
    except Exception as e:
        log(f"⚠️ 구글시트 전송 실패: {e}")


# ════════════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════════════
def main():
    date = today_kst()
    platforms = [
        ("YouTube", get_youtube_subscribers),
        ("TikTok", get_tiktok_followers),
        ("Facebook", get_facebook_followers),
        ("Instagram", get_instagram_followers),
        ("Threads", get_threads_followers),
    ]

    records = []
    result = {"date": date, "platforms": {}}

    for name, fn in platforms:
        count, error = fn()
        if error:
            log(f"⚠️ {name}: 수집 실패 — {error}")
        else:
            log(f"✅ {name}: {count:,}")
        records.append({"date": date, "platform": name, "count": count, "error": error or ""})
        result["platforms"][name] = {"count": count, "error": error}

    send_to_sheets(records)

    with open("social_stats_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    with open("last_success_date.txt", "w", encoding="utf-8") as f:
        f.write(date)

    log("🎉 SNS 통계 수집 완료")


if __name__ == "__main__":
    main()
