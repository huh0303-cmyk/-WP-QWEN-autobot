#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube 자동 업로드 + 자동 예약 발행 (완전 자동, 수동 검토 불필요)
- privacyStatus='private' + publishAt 지정 -> 업로드 후 YT_PUBLISH_DELAY_MINUTES(기본 15분) 뒤
  유튜브가 알아서 공개로 전환함. 스튜디오에서 사람이 버튼 누를 필요 없음.
필요 Secrets: ML_YT_CLIENT_ID, ML_YT_CLIENT_SECRET, ML_YT_REFRESH_TOKEN
선택 env: YT_PUBLISH_DELAY_MINUTES (기본 15)
"""
import os, sys, datetime, requests
from common import list_videos, SOCIAL_LANGS, get_secret
import report

PUBLISH_DELAY_MINUTES = int(os.environ.get("YT_PUBLISH_DELAY_MINUTES", "15"))

def get_access_token(lang):
    # 언어별로 별도 채널에 올리기 위해 YOUTUBE_OAUTH_REFRESH_TOKEN_EN/_JA/_ES/_VI처럼
    # 언어 접미사가 붙은 토큰을 우선 사용. Client ID/Secret은 채널 공용으로 재사용.
    refresh_token = get_secret(
        f"YOUTUBE_OAUTH_REFRESH_TOKEN_{lang.upper()}",
        "ML_YT_REFRESH_TOKEN", "YOUTUBE_OAUTH_REFRESH_TOKEN",
    )
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": get_secret("ML_YT_CLIENT_ID", "YOUTUBE_OAUTH_CLIENT_ID"),
        "client_secret": get_secret("ML_YT_CLIENT_SECRET", "YOUTUBE_OAUTH_CLIENT_SECRET"),
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

def upload_one(access_token, path, title, desc):
    size = os.path.getsize(path)
    publish_at = (datetime.datetime.now(datetime.timezone.utc)
                  + datetime.timedelta(minutes=PUBLISH_DELAY_MINUTES)
                  ).strftime("%Y-%m-%dT%H:%M:%SZ")
    metadata = {
        "snippet": {"title": title, "description": desc, "categoryId": "27",
                    "tags": ["language learning", "vocabulary quiz", "shorts"]},
        # private로 업로드하되 publishAt을 지정하면 그 시각에 유튜브가 자동으로 공개 전환함
        # -> 스튜디오에서 수동으로 공개 버튼을 누를 필요가 없는 완전 자동 예약 발행
        "status": {"privacyStatus": "private", "publishAt": publish_at, "selfDeclaredMadeForKids": False},
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Length": str(size),
        "X-Upload-Content-Type": "video/mp4",
    }
    r = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        headers=headers, json=metadata, timeout=30)
    r.raise_for_status()
    upload_url = r.headers.get("Location")
    with open(path, "rb") as f:
        r2 = requests.put(upload_url, headers={"Content-Type": "video/mp4"}, data=f, timeout=600)
    r2.raise_for_status()
    return r2.json().get("id")

def main():
    videos = list_videos(SOCIAL_LANGS)
    if not videos:
        print("업로드할 영상이 없습니다 (outputs/quiz_*_beginner.mp4)")
        return
    if not get_secret("ML_YT_CLIENT_ID", "YOUTUBE_OAUTH_CLIENT_ID"):
        print("유튜브 토큰 미설정 - 유튜브 업로드 건너뜀")
        return
    for lang, path, title, desc in videos:
        try:
            token = get_access_token(lang)
            vid = upload_one(token, path, title, desc)
            print(f"[YouTube][{lang}] 업로드 완료 (약 {PUBLISH_DELAY_MINUTES}분 뒤 자동 공개): https://youtube.com/watch?v={vid}")
            report.add("YouTube", lang, "success", f"https://youtube.com/watch?v={vid}")
        except Exception as e:
            print(f"[YouTube][{lang}] 업로드 실패: {e}")
            report.add("YouTube", lang, "fail", str(e))

if __name__ == "__main__":
    main()
