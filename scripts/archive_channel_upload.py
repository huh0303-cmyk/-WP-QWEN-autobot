#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
archive_channel_upload.py
─────────────────────────────────────────────────────────────
"컨텐츠팜" 아카이브 채널들(AMERICAN_ARCHIVE_TIMES, CLASSIC_READS_TIMES,
NASA_SPACE_TIMES, SCIENCE_FACTS_TIMES, INVENTION_TIMES, MYTH_LEGEND_TIMES,
RETRO_REELS_TIMES 등) 공용 업로드 스크립트. 각 채널 드라이브의 "완성" 폴더에
있는, 아직 안 올라간 영상 중 하나를 골라 유튜브에 비공개/예약 업로드한다.

플리 5개 채널과의 차이점: 이 채널들은 매번 새로 영상을 만드는 게 아니라
"완성" 폴더에 미리 준비해둔(원본 다운로드+자막+4K 썸네일까지 끝난) 영상들을
순서대로 하나씩 꺼내 올리는 방식이다. "완성" 폴더가 비면 그 채널은 건너뛴다
(다음 리서치 라운드에서 다시 채워야 함).

필요 환경변수:
    CHANNEL_KEY                                   - 예: AMERICAN_ARCHIVE_TIMES
    GOOGLE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN    - 드라이브 접근용(공용)
    YOUTUBE_OAUTH_CLIENT_ID_<CHANNEL_KEY> (없으면 _NEW, 그것도 없으면 공용)
    YOUTUBE_OAUTH_CLIENT_SECRET_<CHANNEL_KEY> (위와 동일 폴백)
    YOUTUBE_OAUTH_REFRESH_TOKEN_<CHANNEL_KEY>      - 필수, 채널별 고유
    OUTPUT_FOLDER_ID_<CHANNEL_KEY>                 - "완성" 폴더(영상+썸네일)
    UPLOADED_LOG_FOLDER_ID_<CHANNEL_KEY>           - (선택) 업로드 완료 기록 저장 위치
    PUBLISH_AT_HOURS_FROM_NOW                      - (선택) 예약 발행까지 시간
"""
import os
import sys
import json

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from datetime import datetime, timedelta, timezone

CHANNEL_KEY = os.environ.get("CHANNEL_KEY", "").strip()
if not CHANNEL_KEY:
    print("❌ CHANNEL_KEY가 없습니다.")
    raise SystemExit(1)
CK = CHANNEL_KEY.upper()

GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REFRESH_TOKEN = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "")


def _env_fallback(*names):
    for n in names:
        v = os.environ.get(n, "")
        if v:
            return v
    return ""


YOUTUBE_OAUTH_CLIENT_ID = _env_fallback(
    f"YOUTUBE_OAUTH_CLIENT_ID_{CK}", "YOUTUBE_OAUTH_CLIENT_ID_NEW", "YOUTUBE_OAUTH_CLIENT_ID")
YOUTUBE_OAUTH_CLIENT_SECRET = _env_fallback(
    f"YOUTUBE_OAUTH_CLIENT_SECRET_{CK}", "YOUTUBE_OAUTH_CLIENT_SECRET_NEW", "YOUTUBE_OAUTH_CLIENT_SECRET")
YOUTUBE_OAUTH_REFRESH_TOKEN = os.environ.get(f"YOUTUBE_OAUTH_REFRESH_TOKEN_{CK}", "")

# 시크릿 슬롯(저장소당 100개 한도)을 아끼려고 채널별 완성폴더 ID를 JSON 하나로 묶어서 저장
_FOLDER_IDS_JSON = os.environ.get("ARCHIVE_OUTPUT_FOLDER_IDS_JSON", "{}")
try:
    _FOLDER_IDS = json.loads(_FOLDER_IDS_JSON)
except Exception as _e:
    print(f"⚠️ ARCHIVE_OUTPUT_FOLDER_IDS_JSON 파싱 실패: {_e!r} raw(len={len(_FOLDER_IDS_JSON)})={_FOLDER_IDS_JSON!r}", flush=True)
    _FOLDER_IDS = {}
OUTPUT_FOLDER_ID = os.environ.get(f"OUTPUT_FOLDER_ID_{CK}", "") or _FOLDER_IDS.get(CK, "")
if not OUTPUT_FOLDER_ID:
    print(f"⚠️ OUTPUT_FOLDER_ID 못찾음. CK={CK!r} keys={list(_FOLDER_IDS.keys())!r}", flush=True)

WORKDIR = "archive_publish_output"


def log(msg):
    print(msg, flush=True)


def get_drive_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None, refresh_token=GOOGLE_OAUTH_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_OAUTH_CLIENT_ID, client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds)


def get_youtube_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None, refresh_token=YOUTUBE_OAUTH_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YOUTUBE_OAUTH_CLIENT_ID, client_secret=YOUTUBE_OAUTH_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    return build("youtube", "v3", credentials=creds)


def find_next_unpublished(drive):
    """완성 폴더에서 아직 안 올린 영상 하나 고르기.
    파일명 뒤에 '_UPLOADED' 마커가 안 붙은 것 중 첫 번째를 쓰고,
    성공하면 드라이브에서 파일명 뒤에 마커를 붙여 표시한다(재업로드 방지)."""
    resp = drive.files().list(
        q=f"'{OUTPUT_FOLDER_ID}' in parents and trashed=false and "
          f"(mimeType='video/mp4' or name contains '.mp4')",
        fields="files(id,name)", pageSize=100, orderBy="name",
    ).execute()
    candidates = [f for f in resp.get("files", []) if "_UPLOADED" not in f["name"]]
    if not candidates:
        return None
    return candidates[0]


def find_matching_thumbnail(drive, video_name):
    """완성 폴더의 영상과 짝을 이루는 썸네일(같은 base 파일명 + _thumb.png)을 찾는다."""
    base = video_name.rsplit(".", 1)[0]
    for suffix in ("_captioned", ""):
        stem = base.replace("_captioned", "")
        query_name = f"{stem}_thumb.png"
        resp = drive.files().list(
            q=f"'{OUTPUT_FOLDER_ID}' in parents and trashed=false and name='{query_name}'",
            fields="files(id,name)", pageSize=5,
        ).execute()
        files = resp.get("files", [])
        if files:
            return files[0]
    return None


def download_drive_file(service, file_id, out_path):
    from googleapiclient.http import MediaIoBaseDownload
    request = service.files().get_media(fileId=file_id)
    with open(out_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def mark_uploaded(drive, file_id, old_name):
    new_name = old_name.rsplit(".", 1)[0] + "_UPLOADED." + old_name.rsplit(".", 1)[1]
    drive.files().update(fileId=file_id, body={"name": new_name}).execute()


def upload_to_youtube(service, video_path, thumb_path, title, description, publish_at_iso=None):
    from googleapiclient.http import MediaFileUpload

    status = {"selfDeclaredMadeForKids": False,
              "privacyStatus": "private" if publish_at_iso else "private"}
    if publish_at_iso:
        status["publishAt"] = publish_at_iso

    body = {
        "snippet": {"title": title[:100], "description": description, "categoryId": "27"},
        "status": status,
    }
    media = MediaFileUpload(video_path, resumable=True, chunksize=5 * 1024 * 1024, mimetype="video/mp4")
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status_obj, response = request.next_chunk(num_retries=5)
        if status_obj:
            log(f"   업로드 진행률: {int(status_obj.progress() * 100)}%")

    video_id = response["id"]
    if thumb_path and os.path.exists(thumb_path):
        try:
            service.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumb_path)).execute()
            log("   ✅ 썸네일 설정 완료")
        except Exception as e:
            log(f"   ⚠️ 썸네일 설정 실패(계정 폰인증 필요할 수 있음, 무시): {e}")
    return video_id


def fix_thumbnail_only(video_id, thumb_name):
    """이미 업로드된 영상에 완성 폴더의 썸네일을 나중에 붙일 때 쓰는 1회성 모드."""
    drive = get_drive_service()
    resp = drive.files().list(
        q=f"'{OUTPUT_FOLDER_ID}' in parents and trashed=false and name='{thumb_name}'",
        fields="files(id,name)", pageSize=5,
    ).execute()
    files = resp.get("files", [])
    if not files:
        log(f"❌ 썸네일 파일을 완성 폴더에서 못 찾음: {thumb_name}")
        raise SystemExit(1)
    os.makedirs(WORKDIR, exist_ok=True)
    thumb_path = os.path.join(WORKDIR, "fix_thumb.png")
    download_drive_file(drive, files[0]["id"], thumb_path)
    from googleapiclient.http import MediaFileUpload
    youtube = get_youtube_service()
    youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumb_path)).execute()
    log(f"✅ 썸네일 적용 완료: video_id={video_id} thumb={thumb_name}")


def main():
    fix_video_id = os.environ.get("FIX_VIDEO_ID", "").strip()
    fix_thumb_name = os.environ.get("FIX_THUMB_NAME", "").strip()
    if fix_video_id and fix_thumb_name:
        fix_thumbnail_only(fix_video_id, fix_thumb_name)
        return

    missing = [k for k, v in {
        "GOOGLE_OAUTH_CLIENT_ID": GOOGLE_OAUTH_CLIENT_ID,
        "GOOGLE_OAUTH_REFRESH_TOKEN": GOOGLE_OAUTH_REFRESH_TOKEN,
        "YOUTUBE_OAUTH_CLIENT_ID": YOUTUBE_OAUTH_CLIENT_ID,
        "YOUTUBE_OAUTH_REFRESH_TOKEN": YOUTUBE_OAUTH_REFRESH_TOKEN,
        "OUTPUT_FOLDER_ID": OUTPUT_FOLDER_ID,
    }.items() if not v]
    if missing:
        log(f"❌ [{CHANNEL_KEY}] 환경변수/시크릿 누락: {missing} — 이 채널은 아직 준비 안 됨, 건너뜀")
        raise SystemExit(0)  # 워크플로우 전체를 실패시키지 않고 조용히 스킵

    os.makedirs(WORKDIR, exist_ok=True)
    drive = get_drive_service()

    log(f"1/4 [{CHANNEL_KEY}] 완성 폴더에서 안 올린 영상 찾는 중...")
    video_file = find_next_unpublished(drive)
    if not video_file:
        log(f"   ⚠️ 업로드할 새 영상이 없습니다 (완성 폴더가 비었거나 다 올림) — 리서치 필요")
        raise SystemExit(0)
    log(f"   찾음: {video_file['name']}")

    thumb_file = find_matching_thumbnail(drive, video_file["name"])

    log("2/4 다운로드 중...")
    video_path = os.path.join(WORKDIR, "video.mp4")
    download_drive_file(drive, video_file["id"], video_path)
    thumb_path = None
    if thumb_file:
        thumb_path = os.path.join(WORKDIR, "thumb.png")
        download_drive_file(drive, thumb_file["id"], thumb_path)
        log(f"   썸네일: {thumb_file['name']}")
    else:
        log("   ⚠️ 짝 맞는 썸네일을 못 찾음 — 기본 썸네일로 업로드됨")

    title = video_file["name"].replace("_captioned", "").rsplit(".", 1)[0].replace("_", " ")
    description = (
        f"{title}\n\nPublic domain archival footage, part of the {CHANNEL_KEY.replace('_', ' ').title()} "
        f"collection.\n\n#archive #history #documentary"
    )

    hours_from_now = os.environ.get("PUBLISH_AT_HOURS_FROM_NOW", "").strip()
    publish_at_iso = None
    if hours_from_now:
        target = datetime.now(timezone.utc) + timedelta(hours=float(hours_from_now))
        publish_at_iso = target.strftime("%Y-%m-%dT%H:%M:%SZ")

    log("3/4 유튜브 업로드 중..." + (f" (예약: {hours_from_now}시간 뒤 공개)" if publish_at_iso else " (비공개로만 업로드)"))
    youtube = get_youtube_service()
    video_id = upload_to_youtube(youtube, video_path, thumb_path, title, description, publish_at_iso)
    studio_url = f"https://studio.youtube.com/video/{video_id}/edit"

    log("4/4 완성 폴더에 업로드 완료 표시 중...")
    mark_uploaded(drive, video_file["id"], video_file["name"])

    log(f"✅ 완료: {studio_url}")


if __name__ == "__main__":
    main()
