#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
youtube_publish_approved.py
─────────────────────────────────────────────────────────────
generate-youtube-playlist.yml의 "prepare" 잡이 만들어둔 영상(구글드라이브에
이미 업로드됨)을 유튜브에 업로드/공개하는 단계.

2026-08-07: 5개 채널 전부 완전자동 운영으로 전환하면서 사람이 눌러야 했던
GitHub Environment 승인 게이트를 제거했다 — prepare 잡이 끝나면 이 잡이 바로
이어서 실행되고, PUBLISH_AT_HOURS_FROM_NOW를 안 주면(스케줄 실행은 항상
안 줌) 즉시 공개로 올라간다. 사람 개입 없이 끝까지 자동으로 흘러간다.

필요 환경변수:
    VIDEO_DRIVE_ID, THUMB_DRIVE_ID, YT_TITLE, YT_DESCRIPTION
    GOOGLE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN   - 드라이브에서 파일 내려받기용
    YOUTUBE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN  - 유튜브 업로드용(스코프: youtube.upload)
    GMAIL_APP_PASSWORD                            - 완료 알림 메일(선택)
    PUBLISH_AT_HOURS_FROM_NOW  - (선택) 지금부터 n시간 뒤로 예약 발행. 비우면 즉시 공개
"""

import os
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from automation_hub.youtube_identity import verify_authenticated_channel

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from datetime import datetime, timedelta, timezone

GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REFRESH_TOKEN = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "")

YOUTUBE_OAUTH_CLIENT_ID = os.environ.get("YOUTUBE_OAUTH_CLIENT_ID", "")
YOUTUBE_OAUTH_CLIENT_SECRET = os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRET", "")
YOUTUBE_OAUTH_REFRESH_TOKEN = os.environ.get("YOUTUBE_OAUTH_REFRESH_TOKEN", "")

GMAIL_USER = "huh0303@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

WORKDIR = "publish_output"


def log(msg):
    print(msg, flush=True)


def send_email(subject, body):
    if not GMAIL_APP_PASSWORD:
        return
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = GMAIL_USER
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as s:
            s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            s.sendmail(GMAIL_USER, [GMAIL_USER], msg.as_string())
    except Exception as e:
        log(f"   ⚠️ 이메일 발송 실패(무시): {e}")


def get_drive_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_OAUTH_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_OAUTH_CLIENT_ID,
        client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds)


def download_drive_file(service, file_id, out_path):
    from googleapiclient.http import MediaIoBaseDownload

    request = service.files().get_media(fileId=file_id)
    with open(out_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def get_youtube_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=YOUTUBE_OAUTH_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YOUTUBE_OAUTH_CLIENT_ID,
        client_secret=YOUTUBE_OAUTH_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(service, video_path, thumb_path, title, description,
                       publish_at_iso=None, tags=None, force_private=False):
    from googleapiclient.http import MediaFileUpload

    # PUBLISH_AT_HOURS_FROM_NOW로 명시적 예약 시각을 준 경우에만 그 시각에
    # 자동 공개되도록 예약(private→public)을 걸고, 안 주면(스케줄 자동실행은
    # 항상 안 줌) 즉시 공개로 올린다 — 완전자동 운영이라 사람이 스튜디오에서
    # 따로 공개 버튼을 누르는 단계가 없다.
    # force_private: Gemini 제목생성이 실패해서 기계적인 폴백 제목이 쓰인 경우.
    # "AI 흔적이 남으면 안 된다"는 원칙상 이런 영상은 자동공개 대상에서 제외하고
    # 비공개로만 올려서 사람이 직접 확인/수정 후 공개하게 한다.
    if force_private:
        status = {"selfDeclaredMadeForKids": False, "privacyStatus": "private"}
    else:
        status = {"selfDeclaredMadeForKids": False,
                  "privacyStatus": "private" if publish_at_iso else "public"}
        if publish_at_iso:
            status["publishAt"] = publish_at_iso

    snippet = {
        "title": title,
        "description": description,
        "categoryId": "10",  # Music
    }
    if tags:
        kept, total = [], 0
        for t in tags:
            t = str(t).strip()
            if not t or total + len(t) > 480:
                continue
            kept.append(t)
            total += len(t)
        snippet["tags"] = kept
    body = {
        "snippet": snippet,
        "status": status,
    }
    media = MediaFileUpload(video_path, resumable=True, chunksize=5 * 1024 * 1024, mimetype="video/mp4")
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    retries = 0
    while response is None:
        try:
            status_obj, response = request.next_chunk(num_retries=5)
            if status_obj:
                log(f"   유튜브 업로드 진행률: {int(status_obj.progress() * 100)}%")
        except Exception as e:
            retries += 1
            if retries > 8:
                raise
            wait = min(2 ** retries, 60)
            log(f"   ⚠️ 업로드 재시도({retries}/8): {e}")
            time.sleep(wait)

    video_id = response["id"]

    if thumb_path and os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
        try:
            service.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumb_path)).execute()
            log(f"   ✅ 썸네일 설정 완료")
        except Exception as e:
            log(f"   ⚠️ 썸네일 설정 실패(무시): {e}")
    else:
        log(f"   ⚠️ 썸네일 파일 없음/비어있음(thumb_path={thumb_path}) — 썸네일 없이 업로드됨")

    return video_id


def main():
    missing = [k for k, v in {
        "VIDEO_DRIVE_ID": os.environ.get("VIDEO_DRIVE_ID", ""),
        "YT_TITLE": os.environ.get("YT_TITLE", ""),
        "GOOGLE_OAUTH_CLIENT_ID": GOOGLE_OAUTH_CLIENT_ID,
        "GOOGLE_OAUTH_REFRESH_TOKEN": GOOGLE_OAUTH_REFRESH_TOKEN,
        "YOUTUBE_OAUTH_CLIENT_ID": YOUTUBE_OAUTH_CLIENT_ID,
        "YOUTUBE_OAUTH_REFRESH_TOKEN": YOUTUBE_OAUTH_REFRESH_TOKEN,
    }.items() if not v]
    if missing:
        log(f"❌ 환경변수 누락: {missing}")
        raise SystemExit(1)

    video_drive_id = os.environ["VIDEO_DRIVE_ID"]
    thumb_drive_id = os.environ.get("THUMB_DRIVE_ID", "")
    title = os.environ["YT_TITLE"]
    description = os.environ.get("YT_DESCRIPTION", "")
    tags = [t.strip() for t in os.environ.get("YT_TAGS", "").split(",") if t.strip()]
    title_is_fallback = os.environ.get("TITLE_IS_FALLBACK", "").strip().lower() == "true"
    hours_from_now = os.environ.get("PUBLISH_AT_HOURS_FROM_NOW", "").strip()

    publish_at_iso = None
    if hours_from_now:
        target = datetime.now(timezone.utc) + timedelta(hours=float(hours_from_now))
        publish_at_iso = target.strftime("%Y-%m-%dT%H:%M:%SZ")

    os.makedirs(WORKDIR, exist_ok=True)
    drive = get_drive_service()

    log("1/3 드라이브에서 영상/썸네일 다운로드 중...")
    video_path = os.path.join(WORKDIR, "final.mp4")
    download_drive_file(drive, video_drive_id, video_path)
    thumb_path = None
    if thumb_drive_id:
        # 드라이브에 저장된 실제 파일명의 확장자를 그대로 써야 한다 — 썸네일이
        # 2MB 제한 때문에 .jpg로 저장됐을 수 있는데 로컬 경로를 무조건 .png로
        # 고정하면, thumbnails().set()의 MediaFileUpload가 확장자만 보고
        # image/png로 잘못 추정해 실제 JPEG 바이트와 어긋난다.
        meta = drive.files().get(fileId=thumb_drive_id, fields="name").execute()
        thumb_ext = os.path.splitext(meta.get("name", ""))[1] or ".png"
        thumb_path = os.path.join(WORKDIR, f"thumbnail{thumb_ext}")
        download_drive_file(drive, thumb_drive_id, thumb_path)
        size = os.path.getsize(thumb_path) if os.path.exists(thumb_path) else -1
        log(f"   썸네일 다운로드: {thumb_path} ({size} bytes)")

    # 2026-08-12: 기본값을 "완전자동 즉시공개"에서 "기본 비공개, 사람이 검토 후
    # 직접 공개"로 전환. PUBLISH_AT_HOURS_FROM_NOW를 명시적으로 준 경우에만
    # 예약공개를 걸고, 안 주면(스케줄 자동실행 포함 전부) 비공개로만 올리고 끝난다.
    stay_private = title_is_fallback or not hours_from_now
    log("2/3 유튜브 업로드 중..." + (" ⚠️ 비공개로만 업로드 (검토 후 직접 공개해주세요)" if stay_private else ""))
    youtube = get_youtube_service()
    channel_key = os.environ.get("CHANNEL_KEY", "").strip().lower()
    if not channel_key:
        raise RuntimeError("CHANNEL_KEY is required for OAuth channel identity verification")
    verified_id = verify_authenticated_channel(youtube, channel_key)
    log(f"   ✅ OAuth 채널 일치 확인: {channel_key} ({verified_id})")
    video_id = upload_to_youtube(youtube, video_path, thumb_path if thumb_drive_id else None,
                                  title, description, publish_at_iso, tags=tags, force_private=stay_private)
    studio_url = f"https://studio.youtube.com/video/{video_id}/edit"

    log("3/3 완료 메일 발송 중...")
    if title_is_fallback:
        when = "비공개로만 업로드됨 — 제목 자동생성 실패로 폴백 문구가 쓰여서 자동공개 안 함. 스튜디오에서 제목 확인 후 직접 공개해주세요."
    elif publish_at_iso:
        when = f"{hours_from_now}시간 뒤 예약 공개(private→public 자동전환)"
    else:
        when = "즉시 공개로 업로드 완료"
    send_email(
        f"[유튜브 자동업로드{'-확인필요' if title_is_fallback else '완료'}] {title[:60]}",
        f"영상이 유튜브에 올라갔어요 ({when}).\n\n{studio_url}\n\n제목: {title}\n",
    )
    log(f"✅ 완료: {studio_url}")


if __name__ == "__main__":
    main()
