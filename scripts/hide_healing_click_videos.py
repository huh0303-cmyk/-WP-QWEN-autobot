#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hide_healing_click_videos.py
─────────────────────────────────────────────────────────────
2026-08-17에 고친 "healing 채널 반복재생 무음삽입 클릭음" 버그 이전에
업로드된 healing(빗소리) 영상들을 찾아서 비공개 전환한다. 삭제 아님,
복구 가능. 제목에 "Rain"(강한/약한 빗소리 테마) 키워드가 들어간 것만
대상 — 시냇물(stream_calm) 테마는 별도 확인 후 처리.

기본 DRY RUN, --execute로 실제 전환.

사용법: python scripts/hide_healing_click_videos.py [--execute] [--include-stream]
필요 환경변수: YOUTUBE_OAUTH_CLIENT_ID/SECRET, YOUTUBE_OAUTH_REFRESH_TOKEN_HEALING
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def log(msg):
    print(msg, flush=True)


def main():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    execute = "--execute" in sys.argv
    include_stream = "--include-stream" in sys.argv

    client_id = os.environ.get("YOUTUBE_OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRET", "")
    refresh_token = os.environ.get("YOUTUBE_OAUTH_REFRESH_TOKEN_HEALING", "")
    if not (client_id and client_secret and refresh_token):
        log("❌ healing 채널 OAuth 환경변수 없음")
        raise SystemExit(1)

    # 2026-08-17: 채널마다 실제 발급된 스코프가 다를 수 있어서(narrow
    # youtube.upload만 되는 토큰도 있음) 넓은 스코프부터 순서대로 시도한다
    # (curio_upload.py의 get_youtube_service와 동일 패턴).
    last_err = None
    yt = None
    for scope in ("https://www.googleapis.com/auth/youtube",
                  "https://www.googleapis.com/auth/youtube.force-ssl",
                  "https://www.googleapis.com/auth/youtube.upload"):
        creds = Credentials(
            token=None, refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id, client_secret=client_secret,
            scopes=[scope],
        )
        try:
            creds.refresh(Request())
            yt = build("youtube", "v3", credentials=creds)
            log(f"   (OAuth 스코프: {scope.rsplit('/', 1)[-1]})")
            break
        except Exception as e:
            last_err = e
            continue
    if yt is None:
        log(f"❌ 모든 스코프로 인증 실패: {last_err}")
        raise SystemExit(1)

    ch = yt.channels().list(part="contentDetails", mine=True).execute()
    uploads_playlist = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    log(f"1/2 healing 채널 전체 영상 목록 조회 중...")
    videos = []
    page_token = None
    while True:
        resp = yt.playlistItems().list(
            part="snippet", playlistId=uploads_playlist, maxResults=50, pageToken=page_token
        ).execute()
        for item in resp.get("items", []):
            sn = item["snippet"]
            videos.append({"video_id": sn["resourceId"]["videoId"], "title": sn["title"]})
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    log(f"   전체 {len(videos)}개 영상")

    keywords = ["rain", "빗소리"]
    if include_stream:
        keywords += ["stream", "시냇물", "creek", "brook"]

    targets = [v for v in videos if any(k in v["title"].lower() for k in [k.lower() for k in keywords])]
    log(f"   대상(제목에 {keywords} 포함): {len(targets)}개")
    for v in targets:
        log(f"   - {v['video_id']} | {v['title']}")

    if not execute:
        log("\n🔍 DRY RUN — 아무것도 안 바뀜. --execute로 실제 비공개 전환.")
        return

    log("2/2 비공개 전환 중...")
    ok = fail = 0
    for v in targets:
        try:
            yt.videos().update(
                part="status", body={"id": v["video_id"], "status": {"privacyStatus": "private"}}
            ).execute()
            ok += 1
            log(f"   ✅ {v['video_id']}")
        except Exception as e:
            fail += 1
            log(f"   ❌ {v['video_id']}: {e}")
    log(f"\n✅ 완료 — 성공:{ok} / 실패:{fail}")


if __name__ == "__main__":
    main()
