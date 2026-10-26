#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply a unique, channel-appropriate thumbnail to each existing playlist video.

Important: a small round-robin thumbnail bank makes unrelated videos look duplicated.
This script now requires one successfully generated unique thumbnail per target video
and refuses to update any video if it cannot build a complete bank. This avoids silently
reusing the same six images across an entire channel.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import requests
import youtube_playlist_maker as pm

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")


def get_youtube_service():
    """thumbnails().set() write-only OAuth token for the selected channel."""
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


def build_fresh_bank(channel_key, count):
    """Generate a distinct original thumbnail for every target video; never round-robin."""
    pm.CHANNEL_KEY = channel_key
    paths = []
    seen_topics = set()
    for i in range(count):
        topic, _ = pm.pick_auto_topic()
        # If the topic picker repeats after exhausting its pool, add a distinct scene prompt.
        if topic in seen_topics:
            topic = f"{topic} — romantic moment {i + 1}"
        seen_topics.add(topic)
        pm.log(f"   [{channel_key}] 고유 썸네일 {i+1}/{count} 생성 중 (장면: {topic})...")
        workdir = f"/tmp/thumb_bank_{channel_key}_{i}"
        os.makedirs(workdir, exist_ok=True)
        try:
            image_paths = pm.build_ai_images(topic, workdir)
            if not image_paths:
                raise RuntimeError("이미지 생성 결과가 비어 있음")
            out_path = os.path.join(workdir, f"thumb_{i+1:03d}.png")
            out_path = pm.make_channel_thumbnail(channel_key, image_paths[0], out_path, topic)
            if not os.path.isfile(out_path) or os.path.getsize(out_path) < 10_000:
                raise RuntimeError("썸네일 파일이 없거나 비정상적으로 작음")
            paths.append(out_path)
        except Exception as e:
            pm.log(f"      ❌ 고유 썸네일 생성 실패: {e}")
            raise RuntimeError(
                f"UNIQUE_THUMBNAIL_BANK_INCOMPLETE: {len(paths)}/{count}; "
                "중복 썸네일로 대체하지 않고 전체 교체를 중단함"
            ) from e
    if len(paths) != count:
        raise RuntimeError(f"UNIQUE_THUMBNAIL_BANK_INCOMPLETE: {len(paths)}/{count}")
    return paths


def list_all_video_ids(channel_handle):
    if not YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY 없음 — 영상 목록 조회 불가")
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "contentDetails", "forHandle": channel_handle, "key": YOUTUBE_API_KEY},
        timeout=20,
    )
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"channels.list 실패: {data['error']}")
    if not data.get("items"):
        raise RuntimeError(f"핸들 '{channel_handle}'로 채널을 못 찾음")
    uploads_playlist = data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    video_ids, page_token = [], None
    while True:
        params = {"part": "contentDetails", "playlistId": uploads_playlist,
                  "maxResults": 50, "key": YOUTUBE_API_KEY}
        if page_token:
            params["pageToken"] = page_token
        r = requests.get("https://www.googleapis.com/youtube/v3/playlistItems", params=params, timeout=20)
        resp = r.json()
        if "error" in resp:
            raise RuntimeError(f"playlistItems.list 실패: {resp['error']}")
        video_ids += [item["contentDetails"]["videoId"] for item in resp.get("items", [])]
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return video_ids


CHANNEL_HANDLES = {
    "globalmusic": "cafe_K1",
    "healing": "Studio_k3",
    "starbucks": "Starbucksvibes",
    "mbb": "Mozart_Bach_Beethoven",
    "kpop": "kpop_studio7",
}


def apply_to_channel(channel_key):
    pm.log(f"\n{'='*50}\n[{channel_key}] 고유 썸네일 전체 교체 시작\n{'='*50}")
    handle = os.environ.get("CHANNEL_HANDLE") or CHANNEL_HANDLES.get(channel_key)
    video_ids = list_all_video_ids(handle)
    pm.log(f"   [{channel_key}] 대상 영상 {len(video_ids)}개")
    if not video_ids:
        return 0, 0
    # Build and validate the entire bank before touching any live video.
    bank = build_fresh_bank(channel_key, len(video_ids))
    if len(bank) != len(video_ids):
        raise RuntimeError("고유 썸네일 수와 영상 수가 다름 — 어떤 영상도 변경하지 않음")
    youtube = get_youtube_service()
    import time
    from googleapiclient.http import MediaFileUpload
    ok, fail = 0, 0
    for i, video_id in enumerate(video_ids):
        thumb_path = bank[i]
        for attempt in range(5):
            try:
                youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumb_path)).execute()
                ok += 1
                pm.log(f"   ✅ {i+1}/{len(video_ids)} {video_id} 고유 썸네일 교체 완료")
                break
            except Exception as e:
                msg = str(e)
                rate_limited = "429" in msg or "too many thumbnails" in msg.lower() or "quota" in msg.lower()
                if rate_limited and attempt < 4:
                    wait = 20 * (attempt + 1)
                    pm.log(f"   ⏳ {i+1}/{len(video_ids)} 제한 응답, {wait}초 후 재시도")
                    time.sleep(wait)
                    continue
                fail += 1
                pm.log(f"   ❌ {i+1}/{len(video_ids)} {video_id} 실패: {msg[:200]}")
                break
        time.sleep(3)
    return ok, fail


def main():
    channel_key = os.environ.get("CHANNEL_KEY", "").strip().lower()
    if not channel_key:
        pm.log("❌ CHANNEL_KEY 환경변수 필요")
        raise SystemExit(1)
    if channel_key not in CHANNEL_HANDLES:
        raise SystemExit(f"❌ 허용되지 않은 채널 키: {channel_key}")
    ok, fail = apply_to_channel(channel_key)
    pm.log(f"\n✅ [{channel_key}] 완료 — 성공 {ok}건 / 실패 {fail}건")
    if fail:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
