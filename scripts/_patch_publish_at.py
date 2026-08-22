#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""(1회성) 예약발행 수정 전에 이미 비공개로만 올라간 지식채널 첫 영상 3개에
직접 publishAt을 걸어서 시간 분산시킨다. 완료 후 삭제해도 되는 1회성 스크립트."""
import os
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

VIDEOS = [
    ("qD3KYB5W83k", "HISTORY_TODAY_TIMES", 4),
    ("45C2WWT8IBI", "SILENT_ERA_TIMES", 10),
    ("MW0ChU-0Bmo", "RETRO_REELS_TIMES", 13),
]


def main():
    for video_id, secret_key, hours in VIDEOS:
        refresh_token = os.environ[f"YOUTUBE_OAUTH_REFRESH_TOKEN_{secret_key}"]
        creds = Credentials(
            token=None, refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ["YOUTUBE_OAUTH_CLIENT_ID"],
            client_secret=os.environ["YOUTUBE_OAUTH_CLIENT_SECRET"],
            scopes=["https://www.googleapis.com/auth/youtube.force-ssl"],
        )
        yt = build("youtube", "v3", credentials=creds)
        publish_at = (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
        yt.videos().update(part="status", body={
            "id": video_id,
            "status": {"privacyStatus": "private", "publishAt": publish_at, "selfDeclaredMadeForKids": False},
        }).execute()
        print(f"OK {video_id} ({secret_key}) -> {publish_at}")


if __name__ == "__main__":
    main()
