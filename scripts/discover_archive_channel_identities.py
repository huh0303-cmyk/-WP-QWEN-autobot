#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
discover_archive_channel_identities.py
─────────────────────────────────────────────────────────────
읽기 전용. archive_channel_upload.py / curio_upload.py가 쓰는 10개
"컨텐츠팜" 채널 키 각각의 YOUTUBE_OAUTH_REFRESH_TOKEN_<KEY>가 실제로
어느 채널로 인증되는지 channels().list(mine=true)로 확인만 한다.
업로드/쓰기 없음 — 2026-09-26 AMERICAN_ARCHIVE_TIMES가 실제로는
"French Survival" 채널로 인증되던 사고 이후, 나머지 채널 키들도
브랜드 라벨과 실제 채널이 일치하는지 전수 확인하기 위해 작성.

출력: 각 채널 키별로 {키: 있음/없음, 실제 채널명, 실제 채널ID}를 JSON으로
artifacts/archive_channel_identity_discovery.json에 저장.
"""
import json
import os
import sys
from pathlib import Path

CHANNEL_KEYS = [
    "NASA_SPACE_TIMES",
    "HISTORY_TODAY_TIMES",
    "SCIENCE_FACTS_TIMES",
    "CLASSICAL_JOURNAL",
    "MYTH_LEGEND_TIMES",
    "INVENTION_TIMES",
    "AMERICAN_ARCHIVE_TIMES",
    "SILENT_ERA_TIMES",
    "RETRO_REELS_TIMES",
    "CLASSIC_READS_TIMES",
]


def log(msg):
    print(msg, flush=True)


def _env_fallback(*names):
    for n in names:
        v = os.environ.get(n, "")
        if v:
            return v
    return ""


def check_one(ck):
    refresh_token = os.environ.get(f"YOUTUBE_OAUTH_REFRESH_TOKEN_{ck}", "")
    if not refresh_token:
        return {"channel_key": ck, "configured": False, "reason": "refresh token secret missing"}

    client_id = _env_fallback(f"YOUTUBE_OAUTH_CLIENT_ID_{ck}", "YOUTUBE_OAUTH_CLIENT_ID", "YOUTUBE_OAUTH_CLIENT_ID_NEW")
    client_secret = _env_fallback(f"YOUTUBE_OAUTH_CLIENT_SECRET_{ck}", "YOUTUBE_OAUTH_CLIENT_SECRET", "YOUTUBE_OAUTH_CLIENT_SECRET_NEW")
    if not client_id or not client_secret:
        return {"channel_key": ck, "configured": False, "reason": "client id/secret missing"}

    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    last_err = None
    for scope in ("https://www.googleapis.com/auth/youtube.force-ssl",
                  "https://www.googleapis.com/auth/youtube.readonly",
                  "https://www.googleapis.com/auth/youtube.upload"):
        creds = Credentials(
            token=None, refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id, client_secret=client_secret,
            scopes=[scope],
        )
        try:
            creds.refresh(Request())
            youtube = build("youtube", "v3", credentials=creds)
            resp = youtube.channels().list(part="snippet,statistics", mine=True, maxResults=1).execute()
            items = resp.get("items", [])
            if not items:
                return {"channel_key": ck, "configured": True, "auth_ok": True,
                        "actual_channel_id": "", "actual_title": "(no channel returned)"}
            item = items[0]
            return {
                "channel_key": ck,
                "configured": True,
                "auth_ok": True,
                "scope_used": scope.rsplit("/", 1)[-1],
                "actual_channel_id": item.get("id", ""),
                "actual_title": item.get("snippet", {}).get("title", ""),
                "subscriber_count": item.get("statistics", {}).get("subscriberCount", ""),
                "video_count": item.get("statistics", {}).get("videoCount", ""),
            }
        except RefreshError as e:
            last_err = e
            continue
        except Exception as e:
            last_err = e
            continue
    return {"channel_key": ck, "configured": True, "auth_ok": False, "reason": str(last_err)}


def main():
    results = [check_one(ck) for ck in CHANNEL_KEYS]
    for r in results:
        if not r.get("configured"):
            log(f"⬜ {r['channel_key']}: 미설정 ({r['reason']})")
        elif not r.get("auth_ok"):
            log(f"❌ {r['channel_key']}: 인증 실패 ({r.get('reason')})")
        else:
            log(f"✅ {r['channel_key']} → 실제 채널: \"{r['actual_title']}\" ({r['actual_channel_id']}) "
                f"구독자 {r.get('subscriber_count','?')} 영상 {r.get('video_count','?')}")

    Path("artifacts").mkdir(parents=True, exist_ok=True)
    Path("artifacts/archive_channel_identity_discovery.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
