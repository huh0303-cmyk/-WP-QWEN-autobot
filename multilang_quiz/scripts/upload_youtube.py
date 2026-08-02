#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube 업로드 — 항상 비공개로 올리고 자동 공개 전환은 하지 않는다.
사용자가 스튜디오에서 직접 확인하고 공개 버튼을 눌러야만 실제로 게시된다
(예전엔 publishAt을 지정해 업로드 후 일정 시간 뒤 자동 공개되도록 되어
있었는데, 이게 사용자 승인 없이 그대로 발행돼버리는 문제라 제거함).
필요 Secrets: ML_YT_CLIENT_ID, ML_YT_CLIENT_SECRET, ML_YT_REFRESH_TOKEN
"""
import os, sys, datetime, requests
from common import list_videos, SOCIAL_LANGS, get_secret
import report

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
    metadata = {
        "snippet": {"title": title, "description": desc, "categoryId": "27",
                    "tags": ["language learning", "vocabulary quiz", "shorts"]},
        # publishAt을 지정하지 않음 -> 계속 비공개로 남아있고, 사람이 스튜디오에서
        # 직접 확인 후 공개 버튼을 눌러야만 실제로 게시된다.
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False},
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
            print(f"[YouTube][{lang}] 업로드 완료 (비공개 - 스튜디오에서 직접 공개 승인 필요): https://youtube.com/watch?v={vid}")
            report.add("YouTube", lang, "success", f"https://youtube.com/watch?v={vid}")
        except Exception as e:
            print(f"[YouTube][{lang}] 업로드 실패: {e}")
            report.add("YouTube", lang, "fail", str(e))

if __name__ == "__main__":
    main()
