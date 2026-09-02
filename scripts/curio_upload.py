#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upload Curio longform videos to YouTube in PRIVATE review mode only."""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from automation_hub.youtube_readiness import UPLOAD_SCOPE, assert_access_scope, check_channel
from automation_hub.youtube_registry import load_channels

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CHANNEL_SECRET_MAP = {
    "nasa": "NASA_SPACE_TIMES",
    "history": "HISTORY_TODAY_TIMES",
    "science": "SCIENCE_FACTS_TIMES",
    "classical": "CLASSICAL_JOURNAL",
    "myth": "MYTH_LEGEND_TIMES",
    "invention": "INVENTION_TIMES",
    "american_archive": "AMERICAN_ARCHIVE_TIMES",
    "silent_era": "SILENT_ERA_TIMES",
    "retro_reels": "RETRO_REELS_TIMES",
    "classic_reads": "CLASSIC_READS_TIMES",
}

RESULT_PATH = os.environ.get("ROOM_RESULT_SOURCE", "artifacts/youtube_curio_result.json")


def log(msg):
    print(msg, flush=True)


def _env_fallback(*names):
    for name in names:
        value = os.environ.get(name, "")
        if value:
            return value
    return ""


def strip_ai_fingerprint(video_path):
    tmp_path = video_path + ".stripped.mp4"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-map_metadata", "-1", "-c", "copy", "-movflags", "+faststart", tmp_path],
            check=True,
            capture_output=True,
            timeout=120,
        )
        os.replace(tmp_path, video_path)
        log("   메타데이터 제거 완료")
    except Exception as exc:
        log(f"   ⚠️ 메타데이터 제거 실패(원본 사용): {exc}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def get_youtube_service(secret_key):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    client_id = _env_fallback(
        f"YOUTUBE_OAUTH_CLIENT_ID_{secret_key}", "YOUTUBE_OAUTH_CLIENT_ID", "YOUTUBE_OAUTH_CLIENT_ID_NEW"
    )
    client_secret = _env_fallback(
        f"YOUTUBE_OAUTH_CLIENT_SECRET_{secret_key}", "YOUTUBE_OAUTH_CLIENT_SECRET", "YOUTUBE_OAUTH_CLIENT_SECRET_NEW"
    )
    refresh_token = os.environ.get(f"YOUTUBE_OAUTH_REFRESH_TOKEN_{secret_key}", "")
    if not refresh_token:
        raise SystemExit(f"YOUTUBE_OAUTH_REFRESH_TOKEN_{secret_key} 시크릿이 없습니다.")

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[UPLOAD_SCOPE],
    )
    creds.refresh(Request())
    assert_access_scope(creds, UPLOAD_SCOPE)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload_to_youtube(service, video_path, thumb_path, title, description, tags=None):
    from googleapiclient.http import MediaFileUpload

    snippet = {
        "title": title[:100],
        "description": description[:5000],
        "categoryId": "27",
    }
    if tags:
        kept, total = [], 0
        for tag in tags:
            tag = str(tag).strip()
            if tag and total + len(tag) <= 480:
                kept.append(tag)
                total += len(tag)
        snippet["tags"] = kept

    # MASTER POLICY: automated Curio uploads never set publishAt and never publish public.
    body = {
        "snippet": snippet,
        "status": {
            "selfDeclaredMadeForKids": False,
            "privacyStatus": "private",
        },
    }
    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(video_path, resumable=True, chunksize=5 * 1024 * 1024, mimetype="video/mp4"),
    )
    response = None
    while response is None:
        status_obj, response = request.next_chunk(num_retries=5)
        if status_obj:
            log(f"   업로드 진행률: {int(status_obj.progress() * 100)}%")

    response_status = response.get("status", {})
    if response_status.get("privacyStatus") != "private" or response_status.get("publishAt"):
        raise RuntimeError("YouTube did not confirm a private unscheduled upload; receipt withheld")

    video_id = response["id"]
    if thumb_path and os.path.exists(thumb_path):
        try:
            service.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumb_path)).execute()
            log("   ✅ 썸네일 설정 완료")
        except Exception as exc:
            log(f"   ⚠️ 썸네일 설정 실패(무시): {exc}")
    return video_id


def write_result(video_id, channel_key, verified_channel_id):
    studio_url = f"https://studio.youtube.com/video/{video_id}/edit"
    result = {
        "artifact_id": video_id,
        "video_id": video_id,
        "artifact_url": studio_url,
        "studio_url": studio_url,
        "privacy_status": "private",
        "channel_key": channel_key,
        "verified_channel_id": verified_channel_id,
        "public_allowed": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    path = os.path.join(ROOT, RESULT_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return studio_url


def main():
    channel_key = sys.argv[1] if len(sys.argv) > 1 else ""
    lang = sys.argv[2] if len(sys.argv) > 2 else "en"
    if channel_key not in CHANNEL_SECRET_MAP:
        raise SystemExit(f"알 수 없는 channel_key: {channel_key!r}")

    workdir = os.path.join("curio_longform_output", channel_key, lang)
    meta_path = os.path.join(workdir, "meta.json")
    if not os.path.exists(meta_path):
        raise SystemExit(f"meta.json 없음: {meta_path}")
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    video_path = meta["video_path"]
    thumb_path = meta.get("thumbnail_path", "")
    title = meta.get("title") or meta["topic"]
    description = meta.get("description") or f"{meta['topic']}\n\nA deep dive into a topic worth knowing."
    tags = meta.get("tags") or []

    strip_ai_fingerprint(video_path)
    channel = next((item for item in load_channels() if item.channel_key == channel_key), None)
    if channel is None:
        raise RuntimeError(f"Unknown channel registry entry: {channel_key}")
    readiness = check_channel(channel)
    if not readiness.ready:
        raise RuntimeError("YouTube OAuth/channel readiness failed: " + "; ".join(readiness.errors))
    verified_id = readiness.verified_channel_id
    log(f"   ✅ OAuth 채널 일치 확인: {channel_key} ({verified_id})")
    service = get_youtube_service(CHANNEL_SECRET_MAP[channel_key])
    video_id = upload_to_youtube(service, video_path, thumb_path, title, description, tags)
    studio_url = write_result(video_id, channel_key, verified_id)
    log(f"✅ 업로드 완료(PRIVATE): {studio_url}")


if __name__ == "__main__":
    main()
