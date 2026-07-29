#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
youtube_playlist_maker.py
─────────────────────────────────────────────────────────────
구글드라이브 A폴더(원곡)에서 음악을 무작위로 골라 60~80분 분량으로
이어붙이고, B폴더(썸네일창고)에서 썸네일 이미지를 무작위로 골라 결합해
최종 mp4를 만든 뒤 C폴더(최종파일)에 "YYYY_M_D_####.mp4" 형식으로 업로드한다.

곡 파일명에 "일본어", "독일어" 같은 언어 태그가 들어있는 경우, 명령어 인자(또는
LANGUAGE_KEYWORD 환경변수)로 "Japanese", "French" 등을 주면 해당 언어 태그가
파일명에 포함된 곡들 중에서만 무작위로 고른다. 인자가 없거나 "Mixed"/"Mix"이면
필터 없이 전체 곡 중에서 고른다.

사용법:
    python scripts/youtube_playlist_maker.py [언어 키워드]

필요 환경변수(Secrets):
    GOOGLE_CREDENTIALS_JSON - 구글드라이브 서비스계정 JSON(문자열 그대로)
    MUSIC_SOURCE_FOLDER_ID  - (선택) 원곡 폴더 ID, 기본값 있음
    THUMBNAIL_FOLDER_ID     - (선택) 썸네일창고 폴더 ID, 기본값 있음
    OUTPUT_FOLDER_ID        - (선택) 최종파일 폴더 ID, 기본값 있음

필요 시스템 도구: ffmpeg, ffprobe
"""

import os
import sys
import json
import random
import subprocess
from datetime import datetime, timezone, timedelta

GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
MUSIC_SOURCE_FOLDER_ID = os.environ.get("MUSIC_SOURCE_FOLDER_ID") or "1RqL44lM5oUSW5_PAZLHHlevrVkr1ibxd"
THUMBNAIL_FOLDER_ID = os.environ.get("THUMBNAIL_FOLDER_ID") or "1jVDuCjTVJPnNSIBEXjnU6DPSzZO56d68"
OUTPUT_FOLDER_ID = os.environ.get("OUTPUT_FOLDER_ID") or "11OrhFj1r0XFu4IAxUmZ29hiA8wExOUfe"

# 영어 키워드 → 파일명에 박힌 한글 언어 태그 매핑
LANGUAGE_TAG_MAP = {
    "japanese": "일본어", "japan": "일본어",
    "french": "프랑스어", "france": "프랑스어",
    "german": "독일어", "germany": "독일어",
    "english": "영어",
    "korean": "한국어",
    "chinese": "중국어", "china": "중국어",
    "spanish": "스페인어", "spain": "스페인어",
    "italian": "이탈리아어", "italy": "이탈리아어",
    "portuguese": "포르투갈어",
    "russian": "러시아어",
    "vietnamese": "베트남어",
    "thai": "태국어",
}
MIXED_KEYWORDS = {"mixed", "mix", "all", ""}

KST = timezone(timedelta(hours=9))
WORKDIR = "playlist_output"
TARGET_MIN_SEC = 60 * 60
TARGET_MAX_SEC = 80 * 60

AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg")
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def log(msg):
    print(msg, flush=True)


def run_ffmpeg(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg 실패: {' '.join(cmd)}\n{proc.stderr[-2000:]}")


def get_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


# ════════════════════════════════════════════════════════════
# 구글드라이브
# ════════════════════════════════════════════════════════════
def get_drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    sa_info = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = service_account.Credentials.from_service_account_info(
        sa_info, scopes=["https://www.googleapis.com/auth/drive"])
    return build("drive", "v3", credentials=creds)


def list_folder_files(service, folder_id, exts):
    files = []
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token,
            pageSize=200,
        ).execute()
        for f in resp.get("files", []):
            name = f.get("name", "")
            mime = f.get("mimeType", "")
            if mime.startswith("audio/") or mime.startswith("image/") or \
               name.lower().endswith(exts):
                files.append(f)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    # 지정한 확장자/미디어 타입으로 한번 더 좁힘 (오디오/이미지 폴더 구분용)
    return [f for f in files if f.get("name", "").lower().endswith(exts)
            or f.get("mimeType", "").startswith(("audio/", "image/"))]


def download_drive_file(service, file_id, out_path):
    from googleapiclient.http import MediaIoBaseDownload

    request = service.files().get_media(fileId=file_id)
    with open(out_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def upload_to_drive(service, file_path, folder_id, name):
    from googleapiclient.http import MediaFileUpload

    metadata = {"name": name, "parents": [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)
    f = service.files().create(body=metadata, media_body=media,
                                fields="id,webViewLink").execute()
    return f.get("webViewLink"), f.get("id")


# ════════════════════════════════════════════════════════════
# 오디오 조합 (무작위 60~80분)
# ════════════════════════════════════════════════════════════
def build_playlist_audio(service, tracks_meta, out_path):
    shuffled = list(tracks_meta)
    random.shuffle(shuffled)

    selected_paths = []
    accumulated = 0.0

    for i, meta in enumerate(shuffled):
        ext = os.path.splitext(meta["name"])[1] or ".mp3"
        local_path = os.path.join(WORKDIR, f"track_{i:03d}{ext}")
        log(f"   다운로드 중: {meta['name']}")
        try:
            download_drive_file(service, meta["id"], local_path)
            dur = get_duration(local_path)
        except Exception as e:
            log(f"   ⚠️ 스킵({meta['name']}): {e}")
            if os.path.exists(local_path):
                os.remove(local_path)
            continue

        if accumulated >= TARGET_MIN_SEC and accumulated + dur > TARGET_MAX_SEC:
            os.remove(local_path)
            continue

        selected_paths.append(local_path)
        accumulated += dur
        log(f"   ✅ 추가: {meta['name']} ({dur/60:.1f}분) — 누적 {accumulated/60:.1f}분")

        if accumulated >= TARGET_MAX_SEC:
            break

    if accumulated < TARGET_MIN_SEC:
        log(f"   ⚠️ 보유한 음원을 다 써도 {accumulated/60:.1f}분 (목표 60분 미만)")

    if not selected_paths:
        raise RuntimeError("사용 가능한 음원이 없습니다")

    cmd = ["ffmpeg", "-y"]
    for p in selected_paths:
        cmd += ["-i", p]
    n = len(selected_paths)
    filter_complex = "".join(f"[{i}:a:0]" for i in range(n)) + f"concat=n={n}:v=0:a=1[outa]"
    cmd += ["-filter_complex", filter_complex, "-map", "[outa]",
            "-c:a", "aac", "-b:a", "192k", out_path]
    run_ffmpeg(cmd)

    return accumulated


def make_video(image_path, audio_path, out_path):
    vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
          "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p")
    run_ffmpeg(["ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
                "-vf", vf, "-c:v", "libx264", "-tune", "stillimage",
                "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
                "-shortest", out_path])


def filter_tracks_by_language(tracks, keyword):
    """keyword가 Mixed/빈값이면 전체 반환, 아니면 파일명에 해당 언어 태그가
    포함된 곡만 골라 반환. 매칭되는 곡이 하나도 없으면 전체로 폴백."""
    if not keyword or keyword.strip().lower() in MIXED_KEYWORDS:
        log("   (필터 없음 — Mixed, 전체 곡에서 무작위 선택)")
        return tracks

    tag = LANGUAGE_TAG_MAP.get(keyword.strip().lower(), keyword.strip())
    matched = [t for t in tracks if tag.lower() in t["name"].lower()]
    if not matched:
        log(f"   ⚠️ '{keyword}'({tag}) 태그가 포함된 곡이 없어서 전체 곡으로 진행")
        return tracks
    log(f"   '{keyword}'({tag}) 태그 매칭: {len(matched)}개")
    return matched


# ════════════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════════════
def main():
    if not GOOGLE_CREDENTIALS_JSON:
        log("❌ GOOGLE_CREDENTIALS_JSON 없음")
        raise SystemExit(1)

    language_keyword = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("LANGUAGE_KEYWORD", "")

    os.makedirs(WORKDIR, exist_ok=True)
    service = get_drive_service()

    log("1/4 원곡 폴더에서 음악 목록 조회 중...")
    tracks = list_folder_files(service, MUSIC_SOURCE_FOLDER_ID, AUDIO_EXTS)
    if not tracks:
        log("❌ 원곡 폴더에 음원이 없습니다")
        raise SystemExit(1)
    log(f"   -> {len(tracks)}개 트랙 발견")
    tracks = filter_tracks_by_language(tracks, language_keyword)

    log("2/4 썸네일창고에서 이미지 무작위 선택 중...")
    thumbs = list_folder_files(service, THUMBNAIL_FOLDER_ID, IMAGE_EXTS)
    if not thumbs:
        log("❌ 썸네일창고에 이미지가 없습니다")
        raise SystemExit(1)
    thumb_meta = random.choice(thumbs)
    thumb_ext = os.path.splitext(thumb_meta["name"])[1] or ".jpg"
    thumb_path = os.path.join(WORKDIR, f"thumbnail{thumb_ext}")
    download_drive_file(service, thumb_meta["id"], thumb_path)
    log(f"   ✅ 썸네일: {thumb_meta['name']}")

    log("3/4 음악 60~80분 분량으로 무작위 이어붙이는 중...")
    audio_path = os.path.join(WORKDIR, "playlist_audio.m4a")
    total_sec = build_playlist_audio(service, tracks, audio_path)
    log(f"   ✅ 총 재생시간: {total_sec/60:.1f}분")

    log("4/4 최종 mp4 생성 및 업로드 중...")
    final_path = os.path.join(WORKDIR, "final.mp4")
    make_video(thumb_path, audio_path, final_path)

    now = datetime.now(KST)
    rand_suffix = f"{random.randint(0, 9999):04d}"
    filename = f"{now.year}_{now.month}_{now.day}_{rand_suffix}.mp4"

    link, _ = upload_to_drive(service, final_path, OUTPUT_FOLDER_ID, filename)
    log("🎉 완료")
    log(f"   파일명: {filename}")
    log(f"   링크: {link}")


if __name__ == "__main__":
    main()
