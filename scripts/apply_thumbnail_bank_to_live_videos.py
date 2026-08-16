#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_thumbnail_bank_to_live_videos.py
─────────────────────────────────────────────────────────────
플리 5개 채널(globalmusic/healing/starbucks/mbb/kpop)에 이미 올라가 있는
모든 영상의 썸네일을 전부 새로 만들어서 교체한다(2026-08-16 사용자 지시:
"지금 썸네일 다 삭제하고 다시 만들어봐. 5k 여행잡지 표지수준으로").

영상 개수만큼 Gemini 이미지를 매번 새로 만들면 비용이 커지므로, 채널당
THUMBNAILS_PER_CHANNEL장짜리 신선한 썸네일 뱅크를 한 번만 만들고
(refresh_playlist_thumbnails.py와 동일한 make_channel_thumbnail 경로 —
5K 해상도, healing은 사진만, 나머지는 중앙 PLAYLIST 대문자+중앙 작은 파형)
그 뱅크를 채널의 모든 영상에 순환(round-robin)으로 적용한다.

필요 환경변수:
    GEMINI_API_KEY, GOOGLE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN (이미지 생성용)
    YOUTUBE_OAUTH_CLIENT_ID/SECRET, YOUTUBE_OAUTH_REFRESH_TOKEN (채널별 주입,
    thumbnails().set 에는 youtube.upload 스코프 필요)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import youtube_playlist_maker as pm

THUMBNAILS_PER_CHANNEL = 6


def get_youtube_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=os.environ.get("YOUTUBE_OAUTH_REFRESH_TOKEN", ""),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ.get("YOUTUBE_OAUTH_CLIENT_ID", ""),
        client_secret=os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRET", ""),
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    return build("youtube", "v3", credentials=creds)


def build_fresh_bank(channel_key):
    """채널 하나에 대해 신선한 썸네일 THUMBNAILS_PER_CHANNEL장을 만들어 로컬 경로 리스트로 반환."""
    pm.CHANNEL_KEY = channel_key
    paths = []
    for i in range(THUMBNAILS_PER_CHANNEL):
        topic, _ = pm.pick_auto_topic()
        pm.log(f"   [{channel_key}] 썸네일 {i+1}/{THUMBNAILS_PER_CHANNEL} 생성 중 (주제: {topic})...")
        workdir = f"/tmp/thumb_bank_{channel_key}_{i}"
        os.makedirs(workdir, exist_ok=True)
        try:
            image_paths = pm.build_ai_images(topic, workdir)
        except Exception as e:
            pm.log(f"      ⚠️ 이미지 생성 실패, 건너뜀: {e}")
            continue
        out_path = os.path.join(workdir, "thumb.png")
        pm.make_channel_thumbnail(channel_key, image_paths[0], out_path, topic)
        paths.append(out_path)
    if not paths:
        raise RuntimeError(f"[{channel_key}] 썸네일을 한 장도 못 만들었음")
    return paths


def list_all_video_ids(youtube):
    ch = youtube.channels().list(part="contentDetails", mine=True).execute()
    uploads_playlist = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    video_ids = []
    page_token = None
    while True:
        resp = youtube.playlistItems().list(
            part="contentDetails", playlistId=uploads_playlist,
            maxResults=50, pageToken=page_token,
        ).execute()
        video_ids += [item["contentDetails"]["videoId"] for item in resp.get("items", [])]
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return video_ids


def apply_to_channel(channel_key):
    pm.log(f"\n{'='*50}\n[{channel_key}] 라이브 영상 썸네일 전체 교체 시작\n{'='*50}")
    youtube = get_youtube_service()

    video_ids = list_all_video_ids(youtube)
    pm.log(f"   [{channel_key}] 대상 영상 {len(video_ids)}개")
    if not video_ids:
        return 0, 0

    bank = build_fresh_bank(channel_key)

    ok, fail = 0, 0
    for i, video_id in enumerate(video_ids):
        from googleapiclient.http import MediaFileUpload
        thumb_path = bank[i % len(bank)]
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumb_path)).execute()
            ok += 1
            pm.log(f"   ✅ {i+1}/{len(video_ids)} {video_id} 썸네일 교체 완료")
        except Exception as e:
            fail += 1
            pm.log(f"   ❌ {i+1}/{len(video_ids)} {video_id} 실패: {str(e)[:200]}")
    return ok, fail


def main():
    channel_key = os.environ.get("CHANNEL_KEY", "")
    if not channel_key:
        pm.log("❌ CHANNEL_KEY 환경변수 필요")
        raise SystemExit(1)
    ok, fail = apply_to_channel(channel_key)
    pm.log(f"\n✅ [{channel_key}] 완료 — 성공 {ok}건 / 실패 {fail}건")


if __name__ == "__main__":
    main()
