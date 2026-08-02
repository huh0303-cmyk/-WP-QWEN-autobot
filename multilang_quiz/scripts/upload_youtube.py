#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube 업로드 — 항상 비공개로 올리고 자동 공개 전환은 하지 않는다.
사용자가 스튜디오에서 직접 확인하고 공개 버튼을 눌러야만 실제로 게시된다
(예전엔 publishAt을 지정해 업로드 후 일정 시간 뒤 자동 공개되도록 되어
있었는데, 이게 사용자 승인 없이 그대로 발행돼버리는 문제라 제거함).

2026-08-02: 언어별 전용 토큰(YOUTUBE_OAUTH_REFRESH_TOKEN_{LANG})이 없을 때
공용 fallback 토큰으로 조용히 넘어가던 로직을 제거했다. 그 fallback이 엉뚱한
채널(스타벅스 플리 채널)을 가리키고 있어서 9개 언어가 전부 그 채널 하나로
뒤섞여 올라간 사고가 있었음. 이제 언어별 토큰이 없으면 그 언어는 그냥
건너뛴다 — "각 언어는 반드시 그 언어 전용 채널에만 발행" 원칙을 코드로 강제.

필요 Secrets: ML_YT_CLIENT_ID/ML_YT_CLIENT_SECRET (또는 YOUTUBE_OAUTH_CLIENT_ID/SECRET,
공용 재사용 가능) + 언어별 YOUTUBE_OAUTH_REFRESH_TOKEN_{EN,JA,ES,VI,FR,DE,ZH,AR,RU}
"""
import os, sys, datetime, requests
from common import list_videos, SOCIAL_LANGS, get_secret
import report

def get_access_token(lang):
    # 언어별 전용 채널 토큰만 사용한다 — 공용 fallback 토큰 사용 금지
    # (엉뚱한 채널로 뒤섞여 올라가는 사고를 코드 차원에서 원천 차단).
    refresh_token = get_secret(f"YOUTUBE_OAUTH_REFRESH_TOKEN_{lang.upper()}")
    if not refresh_token:
        return None
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
            if not token:
                print(f"[YouTube][{lang}] 이 언어 전용 채널 토큰(YOUTUBE_OAUTH_REFRESH_TOKEN_{lang.upper()}) "
                      f"미설정 - 다른 채널로 잘못 올라가지 않도록 건너뜀")
                report.add("YouTube", lang, "skipped", "전용 채널 토큰 미설정")
                continue
            vid = upload_one(token, path, title, desc)
            print(f"[YouTube][{lang}] 업로드 완료 (비공개 - 스튜디오에서 직접 공개 승인 필요): https://youtube.com/watch?v={vid}")
            report.add("YouTube", lang, "success", f"https://youtube.com/watch?v={vid}")
        except Exception as e:
            print(f"[YouTube][{lang}] 업로드 실패: {e}")
            report.add("YouTube", lang, "fail", str(e))

if __name__ == "__main__":
    main()
