#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
social_publish_quiz.py
─────────────────────────────────────────────────────────────
topik_quiz_shorts.py가 만든 단어 퀴즈 쇼츠(final.mp4 + meta_{lang}.json)를
유튜브 / 틱톡 / 페이스북 / 인스타그램 / 쓰레드에 직접 업로드한다.

각 플랫폼은 독립적으로 실패해도 나머지 플랫폼 게시에 영향을 주지 않는다
(social_stats_daily.py와 동일한 원칙). 필요한 시크릿이 없는 플랫폼은
에러 없이 건너뛴다.

사용법:
    python scripts/social_publish_quiz.py <lang>
    (topik_quiz_output/meta_{lang}.json 과 final.mp4 를 읽는다)

필요 환경변수(플랫폼별로 없으면 해당 플랫폼만 스킵):
    YOUTUBE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN   - 유튜브 업로드(스코프: youtube.upload)

    TIKTOK_ACCESS_TOKEN                            - 틱톡 Content Posting API 액세스 토큰
                                                      (video.publish 스코프. 앱이 감사 전이면
                                                      PUBLIC_TO_EVERYONE 대신 SELF_ONLY로만 게시됨)
    TIKTOK_PRIVACY_LEVEL                           - (선택) 기본 SELF_ONLY

    FB_PAGE_ACCESS_TOKEN, FB_PAGE_ID               - 페이스북 릴스 업로드(pages_manage_posts,
                                                      pages_read_engagement 권한 필요)

    IG_ACCESS_TOKEN, IG_USER_ID                    - 인스타그램 릴스 업로드
                                                      (instagram_content_publish 권한 필요,
                                                      비즈니스/크리에이터 계정만 가능,
                                                      meta.json의 public_video_url 필요)

    THREADS_ACCESS_TOKEN, THREADS_USER_ID          - 쓰레드 업로드(threads_content_publish
                                                      권한 필요, public_video_url 필요)

    GMAIL_APP_PASSWORD                             - 완료 요약 메일(선택)
"""

import os
import sys
import json
import time

import requests

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

WORKDIR = "topik_quiz_output"

YOUTUBE_OAUTH_CLIENT_ID = os.environ.get("YOUTUBE_OAUTH_CLIENT_ID", "")
YOUTUBE_OAUTH_CLIENT_SECRET = os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRET", "")
YOUTUBE_OAUTH_REFRESH_TOKEN = os.environ.get("YOUTUBE_OAUTH_REFRESH_TOKEN", "")

TIKTOK_ACCESS_TOKEN = os.environ.get("TIKTOK_ACCESS_TOKEN", "")
TIKTOK_PRIVACY_LEVEL = os.environ.get("TIKTOK_PRIVACY_LEVEL") or "SELF_ONLY"

FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN", "")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID", "")

IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
IG_USER_ID = os.environ.get("IG_USER_ID", "")

THREADS_ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN", "")
THREADS_USER_ID = os.environ.get("THREADS_USER_ID", "")

GMAIL_USER = "huh0303@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

GRAPH_VERSION = "v21.0"


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


def build_caption(meta, max_hashtags=8):
    tags = " ".join(f"#{h}" for h in meta.get("hashtags", [])[:max_hashtags])
    caption = meta.get("short_caption", "").strip()
    return f"{caption}\n\n{tags}".strip()


# ════════════════════════════════════════════════════════════
# YouTube Shorts
# ════════════════════════════════════════════════════════════
def publish_youtube(video_path, meta):
    if not all([YOUTUBE_OAUTH_CLIENT_ID, YOUTUBE_OAUTH_CLIENT_SECRET, YOUTUBE_OAUTH_REFRESH_TOKEN]):
        return {"ok": False, "skipped": True, "reason": "YOUTUBE_OAUTH_* 시크릿 없음"}

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(
        token=None,
        refresh_token=YOUTUBE_OAUTH_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YOUTUBE_OAUTH_CLIENT_ID,
        client_secret=YOUTUBE_OAUTH_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    service = build("youtube", "v3", credentials=creds)

    title = meta.get("youtube_title", "TOPIK Word Quiz")[:100]
    description = (meta.get("youtube_description", "") + "\n\n#Shorts").strip()

    body = {
        "snippet": {"title": title, "description": description, "categoryId": "27"},  # Education
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(video_path, resumable=True, chunksize=5 * 1024 * 1024, mimetype="video/mp4")
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    retries = 0
    while response is None:
        try:
            _, response = request.next_chunk(num_retries=5)
        except Exception as e:
            retries += 1
            if retries > 8:
                raise
            time.sleep(min(2 ** retries, 60))

    video_id = response["id"]
    return {"ok": True, "url": f"https://www.youtube.com/watch?v={video_id}"}


# ════════════════════════════════════════════════════════════
# TikTok — Content Posting API v2
# ════════════════════════════════════════════════════════════
def publish_tiktok(video_path, meta):
    if not TIKTOK_ACCESS_TOKEN:
        return {"ok": False, "skipped": True, "reason": "TIKTOK_ACCESS_TOKEN 없음"}

    size = os.path.getsize(video_path)
    init_body = {
        "post_info": {
            "title": meta.get("short_caption", "")[:150],
            "privacy_level": TIKTOK_PRIVACY_LEVEL,
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
            "video_cover_timestamp_ms": 1000,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": size,
            "chunk_size": size,
            "total_chunk_count": 1,
        },
    }
    headers = {"Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}", "Content-Type": "application/json"}
    r = requests.post("https://open.tiktokapis.com/v2/post/publish/video/init/",
                       headers=headers, json=init_body, timeout=30)
    r.raise_for_status()
    data = r.json().get("data", {})
    upload_url = data.get("upload_url")
    publish_id = data.get("publish_id")
    if not upload_url:
        raise RuntimeError(f"틱톡 init 실패: {r.text[:500]}")

    with open(video_path, "rb") as f:
        video_bytes = f.read()
    up = requests.put(
        upload_url,
        data=video_bytes,
        headers={"Content-Type": "video/mp4", "Content-Range": f"bytes 0-{size - 1}/{size}"},
        timeout=120,
    )
    up.raise_for_status()

    note = "" if TIKTOK_PRIVACY_LEVEL == "PUBLIC_TO_EVERYONE" else " (앱 미감사 상태 — 본인 계정 비공개 초안으로만 올라감)"
    return {"ok": True, "publish_id": publish_id, "note": note.strip()}


# ════════════════════════════════════════════════════════════
# Facebook — Reels
# ════════════════════════════════════════════════════════════
def publish_facebook(video_path, meta):
    if not all([FB_PAGE_ACCESS_TOKEN, FB_PAGE_ID]):
        return {"ok": False, "skipped": True, "reason": "FB_PAGE_ACCESS_TOKEN/FB_PAGE_ID 없음"}

    base = f"https://graph.facebook.com/{GRAPH_VERSION}/{FB_PAGE_ID}"
    caption = build_caption(meta)

    start = requests.post(f"{base}/video_reels",
                           params={"upload_phase": "start", "access_token": FB_PAGE_ACCESS_TOKEN},
                           timeout=30)
    start.raise_for_status()
    start_data = start.json()
    video_id = start_data["video_id"]
    upload_url = start_data["upload_url"]

    size = os.path.getsize(video_path)
    with open(video_path, "rb") as f:
        video_bytes = f.read()
    up = requests.post(
        upload_url,
        headers={
            "Authorization": f"OAuth {FB_PAGE_ACCESS_TOKEN}",
            "offset": "0",
            "file_size": str(size),
        },
        data=video_bytes,
        timeout=180,
    )
    up.raise_for_status()

    finish = requests.post(f"{base}/video_reels", params={
        "upload_phase": "finish",
        "video_id": video_id,
        "video_state": "PUBLISHED",
        "description": caption,
        "access_token": FB_PAGE_ACCESS_TOKEN,
    }, timeout=30)
    finish.raise_for_status()

    return {"ok": True, "video_id": video_id, "url": f"https://www.facebook.com/reel/{video_id}"}


# ════════════════════════════════════════════════════════════
# Instagram — Reels (공개 video_url 필요)
# ════════════════════════════════════════════════════════════
def _poll_container(url_base, container_id, token, status_field="status_code", done_value="FINISHED"):
    for _ in range(30):
        r = requests.get(f"{url_base}/{container_id}", params={"fields": status_field, "access_token": token}, timeout=20)
        r.raise_for_status()
        status = r.json().get(status_field)
        if status == done_value:
            return True
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"컨테이너 처리 실패: {status}")
        time.sleep(5)
    raise RuntimeError("컨테이너 처리 타임아웃")


def publish_instagram(meta):
    if not all([IG_ACCESS_TOKEN, IG_USER_ID]):
        return {"ok": False, "skipped": True, "reason": "IG_ACCESS_TOKEN/IG_USER_ID 없음"}
    video_url = meta.get("public_video_url")
    if not video_url:
        return {"ok": False, "skipped": True, "reason": "공개 video_url 없음(드라이브 공개 업로드 실패했을 가능성)"}

    base = f"https://graph.facebook.com/{GRAPH_VERSION}/{IG_USER_ID}"
    caption = build_caption(meta)

    create = requests.post(f"{base}/media", data={
        "media_type": "REELS", "video_url": video_url, "caption": caption,
        "access_token": IG_ACCESS_TOKEN,
    }, timeout=30)
    create.raise_for_status()
    creation_id = create.json()["id"]

    _poll_container(f"https://graph.facebook.com/{GRAPH_VERSION}", creation_id, IG_ACCESS_TOKEN)

    publish = requests.post(f"{base}/media_publish", data={
        "creation_id": creation_id, "access_token": IG_ACCESS_TOKEN,
    }, timeout=30)
    publish.raise_for_status()
    media_id = publish.json()["id"]

    return {"ok": True, "media_id": media_id}


# ════════════════════════════════════════════════════════════
# Threads (공개 video_url 필요)
# ════════════════════════════════════════════════════════════
def publish_threads(meta):
    if not all([THREADS_ACCESS_TOKEN, THREADS_USER_ID]):
        return {"ok": False, "skipped": True, "reason": "THREADS_ACCESS_TOKEN/THREADS_USER_ID 없음"}
    video_url = meta.get("public_video_url")
    if not video_url:
        return {"ok": False, "skipped": True, "reason": "공개 video_url 없음(드라이브 공개 업로드 실패했을 가능성)"}

    base = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}"
    caption = build_caption(meta, max_hashtags=3)

    create = requests.post(f"{base}/threads", data={
        "media_type": "VIDEO", "video_url": video_url, "text": caption,
        "access_token": THREADS_ACCESS_TOKEN,
    }, timeout=30)
    create.raise_for_status()
    container_id = create.json()["id"]

    _poll_container("https://graph.threads.net/v1.0", container_id, THREADS_ACCESS_TOKEN, status_field="status", done_value="FINISHED")

    publish = requests.post(f"{base}/threads_publish", data={
        "creation_id": container_id, "access_token": THREADS_ACCESS_TOKEN,
    }, timeout=30)
    publish.raise_for_status()
    thread_id = publish.json()["id"]

    return {"ok": True, "thread_id": thread_id}


PLATFORMS = {
    "youtube": lambda video_path, meta: publish_youtube(video_path, meta),
    "tiktok": lambda video_path, meta: publish_tiktok(video_path, meta),
    "facebook": lambda video_path, meta: publish_facebook(video_path, meta),
    "instagram": lambda video_path, meta: publish_instagram(meta),
    "threads": lambda video_path, meta: publish_threads(meta),
}


def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TARGET_LANG", "ko")
    meta_path = os.path.join(WORKDIR, f"meta_{lang}.json")
    if not os.path.exists(meta_path):
        log(f"❌ {meta_path} 없음 — 먼저 topik_quiz_shorts.py를 실행해야 함")
        raise SystemExit(1)

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    video_path = meta.get("video_path") or os.path.join(WORKDIR, "final.mp4")
    if not os.path.exists(video_path):
        log(f"❌ 영상 파일 없음: {video_path}")
        raise SystemExit(1)

    log(f"게시 시작 — 언어: {lang}, 영상: {video_path}")
    results = {}
    for name, fn in PLATFORMS.items():
        log(f"  → {name} 게시 중...")
        try:
            result = fn(video_path, meta)
        except Exception as e:
            result = {"ok": False, "error": str(e)}
        results[name] = result
        if result.get("skipped"):
            log(f"     ⏭️  건너뜀: {result.get('reason')}")
        elif result.get("ok"):
            log(f"     ✅ 성공: {result.get('url') or result.get('media_id') or result.get('thread_id') or result.get('publish_id') or ''}")
        else:
            log(f"     ❌ 실패: {result.get('error')}")

    result_path = os.path.join(WORKDIR, f"publish_result_{lang}.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok_count = sum(1 for r in results.values() if r.get("ok"))
    skip_count = sum(1 for r in results.values() if r.get("skipped"))
    fail_count = len(results) - ok_count - skip_count

    summary_lines = [f"[{lang}] {meta.get('youtube_title', '')}", ""]
    for name, r in results.items():
        if r.get("ok"):
            summary_lines.append(f"✅ {name}: {r.get('url') or r.get('media_id') or r.get('thread_id') or r.get('publish_id') or '완료'}")
        elif r.get("skipped"):
            summary_lines.append(f"⏭️ {name}: 스킵 ({r.get('reason')})")
        else:
            summary_lines.append(f"❌ {name}: {r.get('error')}")
    send_email(
        f"[퀴즈 쇼츠 게시 결과] {lang} — 성공 {ok_count} / 스킵 {skip_count} / 실패 {fail_count}",
        "\n".join(summary_lines),
    )

    log(f"완료 — 성공 {ok_count} / 스킵 {skip_count} / 실패 {fail_count}")
    if fail_count > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
