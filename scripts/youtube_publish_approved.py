#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upload an approved playlist render to YouTube in PRIVATE review mode only.

MASTER safety policy: automation may create/upload the asset, but it may not schedule
or publish it publicly. A human must review and explicitly publish later.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

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

GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REFRESH_TOKEN = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN", "")
YOUTUBE_OAUTH_CLIENT_ID = os.environ.get("YOUTUBE_OAUTH_CLIENT_ID", "")
YOUTUBE_OAUTH_CLIENT_SECRET = os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRET", "")
YOUTUBE_OAUTH_REFRESH_TOKEN = os.environ.get("YOUTUBE_OAUTH_REFRESH_TOKEN", "")
GMAIL_USER = "huh0303@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
WORKDIR = "publish_output"
RESULT_PATH = os.environ.get("ROOM_RESULT_SOURCE", "artifacts/youtube_playlist_result.json")


def log(msg):
    print(msg, flush=True)


def send_email(subject, body):
    if os.environ.get("NORMAL_COMPLETION_EMAIL_ENABLED", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        log("   YouTube completion email suppressed; use the CEO control room")
        return
    if not GMAIL_APP_PASSWORD:
        return
    import smtplib
    from email.mime.text import MIMEText
    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"], msg["From"], msg["To"] = subject, GMAIL_USER, GMAIL_USER
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as s:
            s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            s.sendmail(GMAIL_USER, [GMAIL_USER], msg.as_string())
    except Exception as e:
        log(f"   ⚠️ 이메일 발송 실패(무시): {e}")


def get_drive_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials(token=None, refresh_token=GOOGLE_OAUTH_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token", client_id=GOOGLE_OAUTH_CLIENT_ID,
        client_secret=GOOGLE_OAUTH_CLIENT_SECRET, scopes=["https://www.googleapis.com/auth/drive"])
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
    creds = Credentials(token=None, refresh_token=YOUTUBE_OAUTH_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token", client_id=YOUTUBE_OAUTH_CLIENT_ID,
        client_secret=YOUTUBE_OAUTH_CLIENT_SECRET, scopes=["https://www.googleapis.com/auth/youtube.upload"])
    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(service, video_path, thumb_path, title, description, tags=None):
    from googleapiclient.http import MediaFileUpload
    # HARD GATE: automated playlist uploads are always PRIVATE. Never set publishAt here.
    status = {"selfDeclaredMadeForKids": False, "privacyStatus": "private"}
    snippet = {"title": title, "description": description, "categoryId": "10"}
    if tags:
        kept, total = [], 0
        for tag in tags:
            tag = str(tag).strip()
            if tag and total + len(tag) <= 480:
                kept.append(tag); total += len(tag)
        snippet["tags"] = kept
    request = service.videos().insert(part="snippet,status", body={"snippet": snippet, "status": status},
        media_body=MediaFileUpload(video_path, resumable=True, chunksize=5*1024*1024, mimetype="video/mp4"))
    response, retries = None, 0
    max_retries = 3
    while response is None:
        try:
            status_obj, response = request.next_chunk(num_retries=0)
            if status_obj:
                log(f"   유튜브 업로드 진행률: {int(status_obj.progress()*100)}%")
        except Exception as e:
            retries += 1
            if retries >= max_retries: raise
            time.sleep(min(2 ** retries, 8))
    video_id = response["id"]
    if thumb_path and os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
        try:
            service.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumb_path)).execute()
        except Exception as e:
            log(f"   ⚠️ 썸네일 설정 실패(무시): {e}")
    return video_id


def main():
    required = {"VIDEO_DRIVE_ID": os.environ.get("VIDEO_DRIVE_ID", ""), "YT_TITLE": os.environ.get("YT_TITLE", ""),
        "GOOGLE_OAUTH_CLIENT_ID": GOOGLE_OAUTH_CLIENT_ID, "GOOGLE_OAUTH_REFRESH_TOKEN": GOOGLE_OAUTH_REFRESH_TOKEN,
        "YOUTUBE_OAUTH_CLIENT_ID": YOUTUBE_OAUTH_CLIENT_ID, "YOUTUBE_OAUTH_REFRESH_TOKEN": YOUTUBE_OAUTH_REFRESH_TOKEN}
    missing = [k for k,v in required.items() if not v]
    if missing:
        raise SystemExit(f"환경변수 누락: {missing}")
    os.makedirs(WORKDIR, exist_ok=True)
    drive = get_drive_service()
    video_path = os.path.join(WORKDIR, "final.mp4")
    download_drive_file(drive, os.environ["VIDEO_DRIVE_ID"], video_path)
    thumb_path = None
    thumb_id = os.environ.get("THUMB_DRIVE_ID", "")
    if thumb_id:
        meta = drive.files().get(fileId=thumb_id, fields="name").execute()
        thumb_path = os.path.join(WORKDIR, "thumbnail" + (os.path.splitext(meta.get("name", ""))[1] or ".png"))
        download_drive_file(drive, thumb_id, thumb_path)
    youtube = get_youtube_service()
    channel_key = os.environ.get("CHANNEL_KEY", "").strip().lower()
    if not channel_key: raise RuntimeError("CHANNEL_KEY is required")
    verified_id = verify_authenticated_channel(youtube, channel_key)
    video_id = upload_to_youtube(youtube, video_path, thumb_path, os.environ["YT_TITLE"],
        os.environ.get("YT_DESCRIPTION", ""), [t.strip() for t in os.environ.get("YT_TAGS", "").split(",") if t.strip()])
    studio_url = f"https://studio.youtube.com/video/{video_id}/edit"
    result = {"artifact_id": video_id, "video_id": video_id, "artifact_url": studio_url,
        "studio_url": studio_url, "privacy_status": "private", "channel_key": channel_key,
        "verified_channel_id": verified_id, "public_allowed": False, "timestamp": datetime.now(timezone.utc).isoformat()}
    path = os.path.join(ROOT, RESULT_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: json.dump(result, f, ensure_ascii=False, indent=2)
    log(f"✅ 업로드 완료(PRIVATE): {studio_url}")
    if not os.getenv("SCHEDULE_ID"):
        send_email(f"[유튜브 비공개 업로드 완료] {os.environ['YT_TITLE'][:60]}", f"검토 후 직접 공개해주세요.\n\n{studio_url}\n")


if __name__ == "__main__":
    main()
