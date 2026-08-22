#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_video_metadata.py
─────────────────────────────────────────────────────────────
이미 유튜브에 올라간 플리 채널 영상 중, 제목/설명 생성이 실패해서
파일명 그대로(예: "Chill Playlist | 2026_8_13_1742.mp4") 올라간 것을
나중에 다시 생성해서 고칠 때 쓰는 1회성 스크립트.

필요 환경변수:
    CHANNEL_KEY               - 예: mbb
    FIX_VIDEO_ID               - 유튜브 영상 ID
    FIX_TOPIC                  - 제목/설명 생성에 쓸 주제어(예: "Mozart — Eine kleine Nachtmusik")
    FIX_DURATION_MIN           - 영상 길이(분), 설명 문구에 반영
    GEMINI_API_KEY
    YOUTUBE_OAUTH_CLIENT_ID / _SECRET / _REFRESH_TOKEN (해당 채널 전용, force-ssl 스코프 필요)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
os.environ.setdefault("CHANNEL_KEY", os.environ.get("CHANNEL_KEY", ""))

import youtube_playlist_maker as pm  # noqa: E402

VIDEO_ID = os.environ["FIX_VIDEO_ID"]
TOPIC = os.environ.get("FIX_TOPIC", "Chill")
DURATION_MIN = float(os.environ.get("FIX_DURATION_MIN", "60"))

pm.CHANNEL_KEY = os.environ["CHANNEL_KEY"]

title, description, tags, is_fallback = pm.generate_youtube_title_description(TOPIC, TOPIC, DURATION_MIN)
print(f"새 제목: {title}")
print(f"폴백 여부: {is_fallback}")
print(f"설명 길이: {len(description)}자")
print(f"태그: {tags}")

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials(
    token=None,
    refresh_token=os.environ["YOUTUBE_OAUTH_REFRESH_TOKEN"],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=os.environ["YOUTUBE_OAUTH_CLIENT_ID"],
    client_secret=os.environ["YOUTUBE_OAUTH_CLIENT_SECRET"],
    scopes=["https://www.googleapis.com/auth/youtube.force-ssl"],
)
yt = build("youtube", "v3", credentials=creds)

existing = yt.videos().list(part="snippet", id=VIDEO_ID).execute()
if not existing.get("items"):
    print(f"❌ 영상을 찾을 수 없음: {VIDEO_ID}")
    raise SystemExit(1)
snippet = existing["items"][0]["snippet"]
snippet["title"] = title[:100]
snippet["description"] = description
if tags:
    snippet["tags"] = tags

yt.videos().update(part="snippet", body={"id": VIDEO_ID, "snippet": snippet}).execute()
print(f"✅ 완료: https://studio.youtube.com/video/{VIDEO_ID}/edit")
