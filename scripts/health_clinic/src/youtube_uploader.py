"""
4단계: 완성된 MP4 + 썸네일을 유튜브에 업로드하고 예약 발행(private → publishAt)합니다.
"""
import json
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import LANGUAGES

# 2026-08-13: 예전엔 Drive와 같은 공용 token.json 하나를 3개 채널(kr/en/jp)에
# 다 쓰려고 했는데, YouTube OAuth는 동의 시점에 고른 "브랜드 계정" 하나로
# 고정되기 때문에 토큰 1개로는 실제로 그 중 한 채널에만 업로드된다(channel_id를
# 아무리 넘겨도 videos().insert()엔 그런 파라미터 자체가 없음 — 라우팅 불가능한
# 설계였음). 그래서 언어별로 완전히 별도의 refresh token을 쓰도록 고쳤다 —
# 이 리포의 다른 모든 유튜브 파이프라인(플리 5채널, 아카이브 8채널)과 동일한 패턴.
# 시크릿 슬롯(저장소당 100개 한도)을 아끼려고 3개를 JSON 하나로 묶어서 저장한다
# (아카이브 채널들의 ARCHIVE_OUTPUT_FOLDER_IDS_JSON과 동일한 패턴).
# 2026-08-15: _NEW를 우선하던 순서가 실제로는 폐기된 클라이언트를 골라서
# unauthorized_client를 유발하는 버그였음(curio_upload.py와 동일 문제, 확인/수정됨) —
# plain YOUTUBE_OAUTH_CLIENT_ID가 오늘 검증된 올바른 값이라 순서를 바꿈.
YOUTUBE_OAUTH_CLIENT_ID = os.environ.get("YOUTUBE_OAUTH_CLIENT_ID") or os.environ.get("YOUTUBE_OAUTH_CLIENT_ID_NEW", "")
YOUTUBE_OAUTH_CLIENT_SECRET = os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRET") or os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRET_NEW", "")

try:
    _REFRESH_TOKENS = json.loads(os.environ.get("HEALTH_CLINIC_YOUTUBE_REFRESH_TOKENS_JSON", "{}"))
except Exception:
    _REFRESH_TOKENS = {}


def get_youtube_service(lang: str):
    refresh_token = (
        os.environ.get(f"HEALTH_CLINIC_YOUTUBE_REFRESH_TOKEN_{lang.upper()}", "")
        or _REFRESH_TOKENS.get(lang.upper(), "")
    )
    if not refresh_token:
        raise RuntimeError(f"{lang.upper()} 언어의 refresh token이 없습니다 — 이 언어 채널은 아직 OAuth 미발급")
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YOUTUBE_OAUTH_CLIENT_ID,
        client_secret=YOUTUBE_OAUTH_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.force-ssl"],
    )
    return build("youtube", "v3", credentials=creds)


def upload_and_schedule(
    video_path: str,
    thumbnail_path: str,
    title: str,
    description: str,
    lang: str,
    publish_at_iso: str = None,
    tags: list[str] | None = None,
) -> str:
    """
    2026-08-15: publishAt 자동예약 제거 — 항상 비공개로만 올리고, 실제 공개
    전환은 사람이 검수 후 직접 하도록 통일(다른 모든 파이프라인과 동일 정책).
    publish_at_iso 인자는 이제 사용 안 하지만 호출부 호환을 위해 남겨둠.
    반환값: 업로드된 유튜브 영상 URL
    """
    youtube = get_youtube_service(lang)
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
            "privacyStatus": "private",
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
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(thumbnail_path)).execute()
            print("[YouTube] 썸네일 설정 완료")
        except Exception as e:
            # 채널 폰인증 안 됐거나 스코프 부족하면 403 — 영상 자체는 이미 올라갔으니
            # 여기서 죽지 않고 넘어간다(archive_channel_upload.py와 동일 패턴, 2026-08-15).
            print(f"[YouTube] ⚠️ 썸네일 설정 실패(무시하고 계속): {e}")

    return f"https://youtu.be/{video_id}"
