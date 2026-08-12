"""
4단계: 완성된 MP4 + 썸네일을 유튜브에 업로드하고 예약 발행(private → publishAt)합니다.
"""
import os

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import LANGUAGES
from src.drive_utils import get_credentials


def get_youtube_service():
    return build("youtube", "v3", credentials=get_credentials())


def upload_and_schedule(
    video_path: str,
    thumbnail_path: str,
    title: str,
    description: str,
    lang: str,
    publish_at_iso: str,
    tags: list[str] | None = None,
) -> str:
    """
    publish_at_iso 예: '2026-07-28T09:00:00Z' (UTC, RFC3339 형식)
    반환값: 업로드된 유튜브 영상 URL
    """
    youtube = get_youtube_service()
    lang_cfg = LANGUAGES[lang]

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags or [],
            "categoryId": lang_cfg["youtube_category_id"],
            "defaultLanguage": lang_cfg["code"],
            "defaultAudioLanguage": lang_cfg["code"],
        },
        "status": {
            "privacyStatus": "private",  # 예약 발행은 private + publishAt 조합
            "publishAt": publish_at_iso,
            "selfDeclaredMadeForKids": False,
        },
    }

    print(f"[YouTube] 업로드 시작: {title}")
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"[YouTube] 업로드 진행률: {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"[YouTube] 업로드 완료: https://youtu.be/{video_id}")

    if thumbnail_path and os.path.exists(thumbnail_path):
        youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_path)).execute()
        print("[YouTube] 썸네일 설정 완료")

    return f"https://youtu.be/{video_id}"
