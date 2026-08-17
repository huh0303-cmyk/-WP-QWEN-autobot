#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hide_healing_click_videos.py
─────────────────────────────────────────────────────────────
healing 채널의 롱폼 영상들을 실제로 오디오 분석해서 "무음 삽입 클릭음"
버그(2026-08-17 youtube_playlist_maker.py에서 고침 — 음원 풀이 1곡뿐인
테마에서 같은 곡을 반복할 때 무음(anullsrc) 갭을 끼워넣어 루프 경계마다
"띡띡" 클릭음이 나던 버그)가 실제로 있는 영상만 비공개 전환한다.

제목 키워드로 넘겨짚지 않고, 각 영상 오디오 앞부분을 내려받아
ffmpeg silencedetect로 완전 무음 구간(진짜 자연음이라면 있을 수 없는
구간)이 있는지 직접 검사한다 — 그 구간이 있으면 버그 있는 영상.

목록 조회는 YOUTUBE_API_KEY(공개, OAuth 불필요)로 하고, 비공개 전환만
OAuth로 한다(청취/판단에는 인증이 필요 없음).

기본 DRY RUN, --execute로 실제 전환. 삭제 아님, 복구 가능.

사용법: python scripts/hide_healing_click_videos.py [--execute] [--sample-seconds 1080]
필요 환경변수: YOUTUBE_API_KEY, YOUTUBE_OAUTH_CLIENT_ID/SECRET,
             YOUTUBE_OAUTH_REFRESH_TOKEN_HEALING
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests  # noqa: E402

HEALING_CHANNEL_ID = "UCKZsfAWyCmY0jckf4IWZrqw"  # situation_room_daily.py 확정 매핑(Studio-K7)
MIN_DURATION_SEC = 30 * 60  # 롱폼(30분+)만 검사 대상 — 쇼츠/다른 실험영상 제외

# anullsrc 갭은 random.uniform(1.0, 3.0)초였음 — 검출 여유를 좀 두고 판정
SILENCE_MIN_DUR = 0.4
SILENCE_MAX_DUR = 6.0
SILENCE_NOISE_DB = "-40dB"


def log(msg):
    print(msg, flush=True)


def iso8601_duration_to_sec(s):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m:
        return 0
    h, mi, se = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + se


def list_healing_videos(api_key):
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "contentDetails", "id": HEALING_CHANNEL_ID, "key": api_key},
        timeout=30,
    )
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        raise RuntimeError("healing 채널 정보를 못 찾음(채널 ID 확인 필요)")
    uploads_playlist = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    video_ids = []
    page_token = None
    while True:
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/playlistItems",
            params={"part": "snippet", "playlistId": uploads_playlist, "maxResults": 50,
                    "pageToken": page_token, "key": api_key},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        for item in data.get("items", []):
            video_ids.append(item["snippet"]["resourceId"]["videoId"])
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    videos = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={"part": "snippet,contentDetails", "id": ",".join(chunk), "key": api_key},
            timeout=30,
        )
        r.raise_for_status()
        for item in r.json().get("items", []):
            videos.append({
                "video_id": item["id"],
                "title": item["snippet"]["title"],
                "duration_sec": iso8601_duration_to_sec(item["contentDetails"]["duration"]),
            })
    return videos


def has_click_bug(video_id, sample_seconds, workdir):
    """앞부분 sample_seconds초만 내려받아 진짜 무음 구간이 있는지 검사.
    있으면 (True, [(start, dur), ...]), 없으면 (False, [])."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    audio_tmpl = os.path.join(workdir, f"{video_id}.%(ext)s")
    dl = subprocess.run(
        ["yt-dlp", "-f", "bestaudio", "--download-sections", f"*0-{sample_seconds}",
         "--no-playlist", "-o", audio_tmpl, url],
        capture_output=True, text=True, timeout=180,
    )
    audio_file = None
    for fn in os.listdir(workdir):
        if fn.startswith(video_id + "."):
            audio_file = os.path.join(workdir, fn)
            break
    if not audio_file:
        log(f"      ⚠️ 오디오 다운로드 실패, 건너뜀: {dl.stderr[-300:]}")
        return None, []

    try:
        proc = subprocess.run(
            ["ffmpeg", "-i", audio_file, "-af",
             f"silencedetect=noise={SILENCE_NOISE_DB}:d={SILENCE_MIN_DUR}",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=120,
        )
        stderr = proc.stderr
        starts = [float(x) for x in re.findall(r"silence_start:\s*([\d.]+)", stderr)]
        durs = [float(x) for x in re.findall(r"silence_duration:\s*([\d.]+)", stderr)]
        hits = [(s, d) for s, d in zip(starts, durs) if SILENCE_MIN_DUR <= d <= SILENCE_MAX_DUR]
        return (len(hits) > 0), hits
    finally:
        try:
            os.remove(audio_file)
        except OSError:
            pass


def main():
    execute = "--execute" in sys.argv
    sample_seconds = 1080
    if "--sample-seconds" in sys.argv:
        idx = sys.argv.index("--sample-seconds")
        sample_seconds = int(sys.argv[idx + 1])

    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        log("❌ YOUTUBE_API_KEY 없음")
        raise SystemExit(1)

    if shutil.which("yt-dlp") is None:
        log("❌ yt-dlp 미설치 (pip install yt-dlp 필요)")
        raise SystemExit(1)

    log("1/3 healing 채널 영상 목록 조회 중 (공개 API, 인증 불필요)...")
    videos = list_healing_videos(api_key)
    longform = [v for v in videos if v["duration_sec"] >= MIN_DURATION_SEC]
    log(f"   전체 {len(videos)}개 중 롱폼(30분+) {len(longform)}개 검사 대상")

    log(f"2/3 각 영상 앞 {sample_seconds}초 오디오 다운로드 후 무음 구간(클릭버그 신호) 검사 중...")
    buggy = []
    with tempfile.TemporaryDirectory() as workdir:
        for i, v in enumerate(longform, 1):
            log(f"   [{i}/{len(longform)}] {v['video_id']} | {v['title'][:50]}")
            is_buggy, hits = has_click_bug(v["video_id"], sample_seconds, workdir)
            if is_buggy is None:
                continue
            if is_buggy:
                log(f"      🔴 무음 구간 {len(hits)}개 발견 (클릭버그 신호): "
                    + ", ".join(f"{s:.1f}s(+{d:.1f}s)" for s, d in hits[:5]))
                buggy.append(v)
            else:
                log("      ✅ 이상 없음 (연속 자연음, 무음 구간 없음)")

    log(f"\n3/3 결과 — 클릭버그 있는 영상: {len(buggy)}개 / 검사한 {len(longform)}개 중")
    for v in buggy:
        log(f"   - {v['video_id']} | {v['title']}")

    if not execute:
        log("\n🔍 DRY RUN — 아무것도 안 바뀜. --execute로 실제 비공개 전환.")
        return

    if not buggy:
        log("\n✅ 전환할 영상 없음")
        return

    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    client_id = os.environ.get("YOUTUBE_OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRET", "")
    refresh_token = os.environ.get("YOUTUBE_OAUTH_REFRESH_TOKEN_HEALING", "")
    if not (client_id and client_secret and refresh_token):
        log("❌ healing 채널 OAuth 환경변수 없음")
        raise SystemExit(1)

    yt = None
    last_err = None
    for scope in ("https://www.googleapis.com/auth/youtube.force-ssl",
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
        except RefreshError as e:
            last_err = e
            continue
    if yt is None:
        log(f"❌ 모든 스코프로 인증 실패: {last_err}")
        raise SystemExit(1)

    log("비공개 전환 중...")
    ok = fail = 0
    for v in buggy:
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
