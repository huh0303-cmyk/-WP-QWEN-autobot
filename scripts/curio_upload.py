#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
curio_upload.py
─────────────────────────────────────────────────────────────
curio_longform.py가 만든 결과물(curio_longform_output/<channel_key>/<lang>/meta.json)을
읽어서 해당 "Times/Journal" 지식채널에 유튜브 업로드한다. curio_longform.py 자체는
영상만 만들고 업로드는 안 하길래(2026-08-14 확인), archive_channel_upload.py의
검증된 OAuth/업로드 패턴을 그대로 재사용해서 분리했다.

사용법:
    python scripts/curio_upload.py <channel_key>
    예: python scripts/curio_upload.py nasa

필요 환경변수:
    YOUTUBE_OAUTH_CLIENT_ID_<SECRET_KEY> (없으면 _NEW, 그것도 없으면 공용)
    YOUTUBE_OAUTH_CLIENT_SECRET_<SECRET_KEY> (위와 동일 폴백)
    YOUTUBE_OAUTH_REFRESH_TOKEN_<SECRET_KEY>  - 필수, 채널별 고유
"""
import os
import sys
import json
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from automation_hub.youtube_identity import verify_authenticated_channel

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def log(msg):
    print(msg, flush=True)


# curio_longform.py의 짧은 channel_key → 실제 GitHub Secrets에 등록된 채널 시크릿 접미사.
# (channel_key: cli 인자로 넘기는 짧은 이름 / SECRET_KEY: YOUTUBE_OAUTH_REFRESH_TOKEN_<...>)
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

# 2026-08-22 사용자 지시("예약 걸어놔줘. 시간 펼쳐서.. 너 한꺼번 말고"): 같은 날
# 여러 채널 영상이 한꺼번에 공개되면 배치 발행처럼 보이고 각 채널 개별 신호도
# 흐려짐 — [[feedback_upload_pacing_schedule]]과 같은 원칙을 지식채널 5개에도
# 적용. 채널별로 고정된 시차를 둬서, 생성 직후 바로 공개하는 대신 이 시간만큼
# 뒤에 자동 공개(YouTube의 status.publishAt)되게 예약한다.
PUBLISH_DELAY_HOURS = {
    "nasa": 1,
    "history": 4,
    "invention": 7,
    "silent_era": 10,
    "retro_reels": 13,
}


def _env_fallback(*names):
    for n in names:
        v = os.environ.get(n, "")
        if v:
            return v
    return ""


def strip_ai_fingerprint(video_path):
    """업로드 직전 인코더/제작 메타데이터 제거 — archive_channel_upload.py와 동일 원칙
    ("AI 흔적 없어야 한다", 2026-08-14). 스트림 복사라 화질/시간 손실 거의 없음."""
    import subprocess
    tmp_path = video_path + ".stripped.mp4"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-map_metadata", "-1",
             "-c", "copy", "-movflags", "+faststart", tmp_path],
            check=True, capture_output=True, timeout=120,
        )
        os.replace(tmp_path, video_path)
        log("   메타데이터 제거 완료(AI 흔적 최소화)")
    except Exception as e:
        log(f"   ⚠️ 메타데이터 제거 실패(무시하고 원본 그대로 업로드): {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def get_youtube_service(secret_key):
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    # 2026-08-15: _NEW 변형을 먼저 시도하던 순서가 문제였음 — YOUTUBE_OAUTH_CLIENT_ID_NEW는
    # 예전 세션에서 만들어진 폐기된 클라이언트였고, 오늘 15채널 unauthorized_client를
    # 고치면서 확정한 올바른 클라이언트는 plain YOUTUBE_OAUTH_CLIENT_ID 쪽이었음
    # (raw refresh grant로 직접 검증 완료, [[project_21_channels_pipeline_status]] 참고).
    # _NEW를 우선하면 이 수정이 무시돼서 다시 unauthorized_client가 남 — 순서 반대로.
    client_id = _env_fallback(
        f"YOUTUBE_OAUTH_CLIENT_ID_{secret_key}", "YOUTUBE_OAUTH_CLIENT_ID", "YOUTUBE_OAUTH_CLIENT_ID_NEW")
    client_secret = _env_fallback(
        f"YOUTUBE_OAUTH_CLIENT_SECRET_{secret_key}", "YOUTUBE_OAUTH_CLIENT_SECRET", "YOUTUBE_OAUTH_CLIENT_SECRET_NEW")
    refresh_token = os.environ.get(f"YOUTUBE_OAUTH_REFRESH_TOKEN_{secret_key}", "")
    if not refresh_token:
        log(f"❌ YOUTUBE_OAUTH_REFRESH_TOKEN_{secret_key} 시크릿이 없습니다.")
        raise SystemExit(1)

    # 채널마다 실제 발급 스코프가 다른 경우가 있어(2026-08-14 확인) 둘 다 시도.
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
            log(f"   (OAuth 스코프: {scope.rsplit('/', 1)[-1]})")
            return build("youtube", "v3", credentials=creds)
        except RefreshError as e:
            last_err = e
            continue
    raise last_err


def upload_to_youtube(service, video_path, thumb_path, title, description, tags=None, publish_at=None):
    from googleapiclient.http import MediaFileUpload

    snippet = {"title": title[:100], "description": description[:5000], "categoryId": "27"}
    if tags:
        # 유튜브 태그 전체 문자열 합 500자 제한 — 넘는 태그부터 잘라낸다.
        kept, total = [], 0
        for t in tags:
            t = str(t).strip()
            if not t or total + len(t) > 480:
                continue
            kept.append(t)
            total += len(t)
        snippet["tags"] = kept
    # YouTube API 규칙: publishAt을 쓰려면 업로드 시점 privacyStatus는 반드시
    # "private"이어야 하고, 지정한 시각에 유튜브가 자동으로 공개 전환해준다.
    status = {"selfDeclaredMadeForKids": False, "privacyStatus": "private"}
    if publish_at:
        status["publishAt"] = publish_at
    body = {
        "snippet": snippet,
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


def main():
    channel_key = sys.argv[1] if len(sys.argv) > 1 else ""
    lang = sys.argv[2] if len(sys.argv) > 2 else "en"
    if channel_key not in CHANNEL_SECRET_MAP:
        log(f"❌ 알 수 없는 channel_key: {channel_key!r} (허용: {list(CHANNEL_SECRET_MAP)})")
        raise SystemExit(1)
    secret_key = CHANNEL_SECRET_MAP[channel_key]

    workdir = os.path.join("curio_longform_output", channel_key, lang)
    meta_path = os.path.join(workdir, "meta.json")
    if not os.path.exists(meta_path):
        log(f"❌ meta.json 없음: {meta_path} — curio_longform.py를 먼저 실행해야 함")
        raise SystemExit(1)
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    video_path = meta["video_path"]
    thumb_path = meta.get("thumbnail_path", "")
    topic = meta["topic"]

    log("1/2 업로드 직전 메타데이터 스트리핑...")
    strip_ai_fingerprint(video_path)

    # curio_longform.py가 실제 대본 내용 기반으로 생성한 제목/설명(1000자 내외).
    # (2026-08-15 추가 — 없으면 구버전 meta.json 대비 최소 폴백)
    title = meta.get("title") or topic
    description = meta.get("description") or (
        f"{topic}\n\nA deep dive into a topic worth knowing.\n\n#education #didyouknow #knowledge"
    )
    tags = meta.get("tags") or []

    configured_delay = os.environ.get("PUBLISH_AT_HOURS_FROM_NOW", "").strip()
    delay_hours = float(configured_delay) if configured_delay else PUBLISH_DELAY_HOURS.get(channel_key)
    publish_at = None
    if delay_hours is not None:
        publish_at = (datetime.now(timezone.utc) + timedelta(hours=delay_hours)).strftime(
            "%Y-%m-%dT%H:%M:%SZ")

    log(f"2/2 유튜브 업로드 중 (채널: {secret_key})...")
    service = get_youtube_service(secret_key)
    verified_id = verify_authenticated_channel(service, channel_key)
    log(f"   ✅ OAuth 채널 일치 확인: {channel_key} ({verified_id})")
    video_id = upload_to_youtube(service, video_path, thumb_path, title, description, tags, publish_at)
    if publish_at:
        log(f"✅ 업로드 완료(비공개, {publish_at}에 자동 공개 예약됨): https://youtube.com/watch?v={video_id}")
    else:
        log(f"✅ 업로드 완료(비공개): https://youtube.com/watch?v={video_id}")


if __name__ == "__main__":
    main()
