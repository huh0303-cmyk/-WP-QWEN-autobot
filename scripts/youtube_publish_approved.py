#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
youtube_publish_approved.py
─────────────────────────────────────────────────────────────
generate-youtube-playlist.yml의 "prepare" 잡이 만들어둔 영상(구글드라이브에
이미 업로드됨)을, 사람이 GitHub Environment 승인("Approve and deploy")을
누른 뒤에 실제로 유튜브에 업로드/공개하는 단계. 승인 전까지는 아무것도
유튜브에 올라가지 않는다.

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


def upload_to_youtube(service, video_path, thumb_path, title, description, publish_at_iso=None):
    from googleapiclient.http import MediaFileUpload

    status = {"selfDeclaredMadeForKids": False}
    if publish_at_iso:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at_iso
    else:
        status["privacyStatus"] = "public"

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "10",  # Music
        },
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

    if thumb_path and os.path.exists(thumb_path):
        try:
            service.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumb_path)).execute()
        except Exception as e:
            log(f"   ⚠️ 썸네일 설정 실패(무시): {e}")

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
    thumb_path = os.path.join(WORKDIR, "thumbnail.png")
    if thumb_drive_id:
        download_drive_file(drive, thumb_drive_id, thumb_path)

    log("2/3 유튜브 업로드 중...")
    youtube = get_youtube_service()
    video_id = upload_to_youtube(youtube, video_path, thumb_path if thumb_drive_id else None,
                                  title, description, publish_at_iso)
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    log("3/3 완료 메일 발송 중...")
    when = f"{hours_from_now}시간 뒤 예약 공개" if publish_at_iso else "즉시 공개"
    send_email(
        f"[유튜브 업로드 완료] {title[:60]}",
        f"승인하신 영상이 유튜브에 올라갔어요 ({when}).\n\n{video_url}\n\n제목: {title}\n",
    )
    log(f"✅ 완료: {video_url}")


if __name__ == "__main__":
    main()
