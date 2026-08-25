#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
social_publish.py
─────────────────────────────────────────────────────────────
topik_quiz_shorts.py / health_shorts.py 등이 만든 쇼츠(final.mp4 + meta.json)를
유튜브/틱톡/페이스북에 "발행 대기" 상태로 올리고, 인스타그램/쓰레드는
캡션+영상 링크만 준비한다. 어떤 생성 스크립트가 만든 쇼츠든 meta.json
포맷(youtube_title/youtube_description/short_caption/hashtags/video_path/
public_video_url)만 맞으면 그대로 쓸 수 있다.

원칙: 자동화는 예약/준비까지만 하고, 실제 공개(퍼블리시)는 항상 사람이
마지막에 직접 누른다.
    - 유튜브: private로 업로드 → 스튜디오에서 직접 공개
    - 틱톡: 앱 미감사 상태라 원래 본인 계정 비공개 초안으로만 올라감(자연히 만족)
    - 페이스북: DRAFT로 업로드 → Meta Business Suite에서 직접 게시
    - 인스타그램/쓰레드: API에 진짜 임시저장이 없어서(컨테이너 24시간 뒤 만료)
      아예 API 호출 안 하고 캡션+영상 링크만 결과에 담아 이메일로 보냄 → 앱에서 직접 업로드

각 플랫폼은 독립적으로 실패해도 나머지 플랫폼에 영향을 주지 않는다
(social_stats_daily.py와 동일한 원칙). 필요한 시크릿이 없는 플랫폼은
에러 없이 건너뛴다.

사용법:
    python scripts/social_publish.py <lang>              # 단어퀴즈: topik_quiz_output/meta_{lang}.json
    python scripts/social_publish.py <meta.json 경로>      # 건강채널 등: 경로 그대로 사용

필요 환경변수(플랫폼별로 없으면 해당 플랫폼만 스킵):
    YOUTUBE_OAUTH_CLIENT_ID/SECRET/REFRESH_TOKEN   - 유튜브 업로드(스코프: youtube.upload)

    TIKTOK_ACCESS_TOKEN                            - 틱톡 Content Posting API 액세스 토큰
                                                      (video.publish 스코프)
    TIKTOK_PRIVACY_LEVEL                           - (선택) 기본 SELF_ONLY

    FB_PAGE_ACCESS_TOKEN, FB_PAGE_ID               - 페이스북 릴스 업로드(pages_manage_posts,
                                                      pages_read_engagement 권한 필요)

    IG_ACCESS_TOKEN, IG_USER_ID                    - 인스타그램 비즈니스 계정(캐러셀 카드뉴스
                                                      게시, instagram_content_publish 권한 필요)
    IG_AUTO_PUBLISH                                 - "true"일 때만 실제로 라이브 게시함(기본 꺼짐)

    THREADS_ACCESS_TOKEN, THREADS_USER_ID          - 쓰레드 계정(캐러셀 카드뉴스 게시)
    THREADS_AUTO_PUBLISH                            - "true"일 때만 실제로 라이브 게시함(기본 꺼짐)

    GMAIL_APP_PASSWORD                             - 완료 요약 메일(선택). IG_AUTO_PUBLISH/
                                                      THREADS_AUTO_PUBLISH가 꺼져있으면 인스타/
                                                      쓰레드 캡션+카드이미지는 이 메일로만 전달됨

2026-08-23: 인스타그램/쓰레드는 API 컨테이너에 진짜 임시저장이 없어서(24시간
뒤 만료), 기본값은 여전히 "자동 게시 안 함, 캡션+카드이미지만 준비" 원칙을
유지한다. IG_AUTO_PUBLISH/THREADS_AUTO_PUBLISH를 명시적으로 "true"로 켠
경우에만 카드뉴스 이미지들(topik_quiz_shorts.py가 만드는 card_image_urls)을
캐러셀로 실제 라이브 게시한다 — 이 경우 사람의 최종 확인 없이 바로
공개되므로, 콘텐츠 품질에 확신이 있을 때만 켤 것.
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
IG_AUTO_PUBLISH = os.environ.get("IG_AUTO_PUBLISH", "").strip().lower() == "true"

THREADS_ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN", "")
THREADS_USER_ID = os.environ.get("THREADS_USER_ID", "")
THREADS_AUTO_PUBLISH = os.environ.get("THREADS_AUTO_PUBLISH", "").strip().lower() == "true"

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
        # 비공개로 업로드만 해둔다 — 실제 공개(퍼블리시)는 사용자가 유튜브 스튜디오에서
        # 검수 후 직접 누른다. 자동화가 공개 버튼까지 누르지 않는다.
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False},
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
    return {"ok": True, "note": "비공개 업로드 완료 — 스튜디오에서 검수 후 직접 공개 필요",
            "url": f"https://studio.youtube.com/video/{video_id}/edit"}


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

    # DRAFT로 올려두고 실제 게시는 Meta Business Suite에서 사용자가 직접 누른다.
    finish = requests.post(f"{base}/video_reels", params={
        "upload_phase": "finish",
        "video_id": video_id,
        "video_state": "DRAFT",
        "description": caption,
        "access_token": FB_PAGE_ACCESS_TOKEN,
    }, timeout=30)
    finish.raise_for_status()

    return {"ok": True, "note": "초안(DRAFT) 업로드 완료 — Meta Business Suite에서 직접 게시 필요",
            "video_id": video_id}


# ════════════════════════════════════════════════════════════
# Instagram / Threads — 카드뉴스(캐러셀) 게시.
# 두 플랫폼 다 API로 만든 컨테이너는 "초안"으로 앱에 남지 않고 24시간 뒤
# 그냥 만료돼버린다(진짜 임시저장 기능이 없음) — 그래서 기본값은 여전히
# API 호출 없이 캡션+카드이미지 링크만 준비해서 사람이 앱에서 직접
# 업로드하게 한다("최종 공개는 사람이 누른다" 원칙). IG_AUTO_PUBLISH /
# THREADS_AUTO_PUBLISH를 명시적으로 켠 경우에만 카드뉴스 이미지들을
# 캐러셀로 실제 라이브 게시한다.
# ════════════════════════════════════════════════════════════
def _poll_container_ready(status_url, params, tries=10, wait=3):
    """미디어 컨테이너가 FINISHED 상태가 될 때까지 잠깐 기다린다(이미지는
    보통 즉시 끝나지만, 드물게 처리 지연이 있어 바로 publish하면 실패할 수 있음)."""
    for _ in range(tries):
        r = requests.get(status_url, params=params, timeout=20)
        if r.ok:
            status = r.json().get("status_code")
            if status == "FINISHED":
                return True
            if status == "ERROR":
                return False
        time.sleep(wait)
    return True  # 상태를 못 받아도 일단 publish 시도(대부분 이미지는 이미 끝나있음)


def publish_instagram(meta):
    image_urls = meta.get("card_image_urls") or []
    if not image_urls:
        return {"ok": False, "skipped": True, "reason": "card_image_urls 없음 — 카드뉴스 이미지 생성/드라이브 업로드 설정 확인 필요"}
    caption = build_caption(meta)

    if not (IG_AUTO_PUBLISH and IG_ACCESS_TOKEN and IG_USER_ID):
        return {
            "ok": True,
            "note": "IG_AUTO_PUBLISH 꺼짐(기본값) — 인스타그램은 임시저장이 없어 자동 게시 안 함. 아래 카드이미지로 직접 캐러셀 업로드 필요",
            "image_urls": image_urls,
            "caption": caption,
        }

    base = f"https://graph.facebook.com/{GRAPH_VERSION}/{IG_USER_ID}"
    try:
        if len(image_urls) == 1:
            r = requests.post(f"{base}/media", data={
                "image_url": image_urls[0], "caption": caption, "access_token": IG_ACCESS_TOKEN,
            }, timeout=30)
            r.raise_for_status()
            creation_id = r.json()["id"]
        else:
            child_ids = []
            for url in image_urls[:10]:  # 인스타그램 캐러셀 최대 10장
                r = requests.post(f"{base}/media", data={
                    "image_url": url, "is_carousel_item": "true", "access_token": IG_ACCESS_TOKEN,
                }, timeout=30)
                r.raise_for_status()
                child_ids.append(r.json()["id"])
            r = requests.post(f"{base}/media", data={
                "media_type": "CAROUSEL", "children": ",".join(child_ids),
                "caption": caption, "access_token": IG_ACCESS_TOKEN,
            }, timeout=30)
            r.raise_for_status()
            creation_id = r.json()["id"]

        _poll_container_ready(f"https://graph.facebook.com/{GRAPH_VERSION}/{creation_id}",
                               {"fields": "status_code", "access_token": IG_ACCESS_TOKEN})
        pub = requests.post(f"{base}/media_publish", data={
            "creation_id": creation_id, "access_token": IG_ACCESS_TOKEN,
        }, timeout=30)
        pub.raise_for_status()
        return {"ok": True, "note": "카드뉴스 캐러셀 실시간 게시 완료", "media_id": pub.json().get("id")}
    except Exception as e:
        return {"ok": False, "error": f"인스타그램 게시 실패: {e}"}


def publish_threads(meta):
    image_urls = meta.get("card_image_urls") or []
    if not image_urls:
        return {"ok": False, "skipped": True, "reason": "card_image_urls 없음 — 카드뉴스 이미지 생성/드라이브 업로드 설정 확인 필요"}
    caption = build_caption(meta, max_hashtags=3)

    if not (THREADS_AUTO_PUBLISH and THREADS_ACCESS_TOKEN and THREADS_USER_ID):
        return {
            "ok": True,
            "note": "THREADS_AUTO_PUBLISH 꺼짐(기본값) — 쓰레드는 임시저장이 없어 자동 게시 안 함. 아래 카드이미지로 직접 캐러셀 업로드 필요",
            "image_urls": image_urls,
            "caption": caption,
        }

    base = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}"
    try:
        if len(image_urls) == 1:
            r = requests.post(f"{base}/threads", data={
                "media_type": "IMAGE", "image_url": image_urls[0],
                "text": caption, "access_token": THREADS_ACCESS_TOKEN,
            }, timeout=30)
            r.raise_for_status()
            creation_id = r.json()["id"]
        else:
            child_ids = []
            for url in image_urls[:10]:  # 쓰레드 캐러셀 최대 10장
                r = requests.post(f"{base}/threads", data={
                    "media_type": "IMAGE", "image_url": url,
                    "is_carousel_item": "true", "access_token": THREADS_ACCESS_TOKEN,
                }, timeout=30)
                r.raise_for_status()
                child_ids.append(r.json()["id"])
            r = requests.post(f"{base}/threads", data={
                "media_type": "CAROUSEL", "children": ",".join(child_ids),
                "text": caption, "access_token": THREADS_ACCESS_TOKEN,
            }, timeout=30)
            r.raise_for_status()
            creation_id = r.json()["id"]

        _poll_container_ready(f"https://graph.threads.net/v1.0/{creation_id}",
                               {"fields": "status", "access_token": THREADS_ACCESS_TOKEN})
        pub = requests.post(f"{base}/threads_publish", data={
            "creation_id": creation_id, "access_token": THREADS_ACCESS_TOKEN,
        }, timeout=30)
        pub.raise_for_status()
        return {"ok": True, "note": "카드뉴스 캐러셀 실시간 게시 완료", "post_id": pub.json().get("id")}
    except Exception as e:
        return {"ok": False, "error": f"쓰레드 게시 실패: {e}"}


PLATFORMS = {
    "youtube": lambda video_path, meta: publish_youtube(video_path, meta),
    "tiktok": lambda video_path, meta: publish_tiktok(video_path, meta),
    "facebook": lambda video_path, meta: publish_facebook(video_path, meta),
    "instagram": lambda video_path, meta: publish_instagram(meta),
    "threads": lambda video_path, meta: publish_threads(meta),
}


def main():
    # 인자가 meta json 경로 그대로면(예: health_shorts_output/meta.json) 그걸 바로 쓰고,
    # 아니면 기존 단어퀴즈 방식대로 "언어 코드"로 보고 topik_quiz_output/meta_{lang}.json을 찾는다.
    arg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TARGET_LANG", "ko")
    if arg.endswith(".json"):
        meta_path = arg
        label = os.path.dirname(meta_path) or arg
    else:
        meta_path = os.path.join(WORKDIR, f"meta_{arg}.json")
        label = arg

    if not os.path.exists(meta_path):
        log(f"❌ {meta_path} 없음 — 먼저 생성 스크립트를 실행해야 함")
        raise SystemExit(1)

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    video_path = meta.get("video_path") or os.path.join(os.path.dirname(meta_path), "final.mp4")
    if not os.path.exists(video_path):
        log(f"❌ 영상 파일 없음: {video_path}")
        raise SystemExit(1)

    log(f"게시 시작 — {label}, 영상: {video_path}")
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
            log(f"     ✅ {result.get('note') or '완료'} — "
                f"{result.get('url') or result.get('video_id') or result.get('publish_id') or result.get('media_id') or result.get('post_id') or ''}")
        else:
            log(f"     ❌ 실패: {result.get('error')}")

    result_path = os.path.join(os.path.dirname(meta_path) or WORKDIR, f"publish_result_{os.path.basename(meta_path)}")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok_count = sum(1 for r in results.values() if r.get("ok"))
    skip_count = sum(1 for r in results.values() if r.get("skipped"))
    fail_count = len(results) - ok_count - skip_count

    summary_lines = [f"[{label}] {meta.get('youtube_title', '')}", "",
                      "※ 유튜브/틱톡/페이스북은 발행 대기 상태 — 최종 공개는 직접 눌러야 합니다. "
                      "인스타그램/쓰레드는 IG_AUTO_PUBLISH/THREADS_AUTO_PUBLISH가 켜진 경우에만 바로 라이브 게시됩니다.", ""]
    for name, r in results.items():
        if r.get("ok"):
            line = f"✅ {name}: {r.get('note') or '완료'}"
            if r.get("url"):
                line += f"\n   {r['url']}"
            if r.get("caption"):
                media_line = r.get("video_url") or ", ".join(r.get("image_urls") or [])
                line += f"\n   미디어: {media_line}\n   캡션:\n   {r['caption']}"
            summary_lines.append(line)
        elif r.get("skipped"):
            summary_lines.append(f"⏭️ {name}: 스킵 ({r.get('reason')})")
        else:
            summary_lines.append(f"❌ {name}: {r.get('error')}")
    send_email(
        f"[쇼츠 게시 결과] {label} — 성공 {ok_count} / 스킵 {skip_count} / 실패 {fail_count}",
        "\n".join(summary_lines),
    )

    log(f"완료 — 성공 {ok_count} / 스킵 {skip_count} / 실패 {fail_count}")
    # 플랫폼별 실패는 서로 독립적이라는 설계 원칙(파일 상단 docstring 참고)대로,
    # 개별 플랫폼 실패(예: 페이스북 권한 문제)가 워크플로 전체를 매일 "실패"로
    # 표시하게 만들지 않는다 — 결과는 이미 이메일/publish_result_*.json으로 보고됨.
    # 유튜브(핵심 플랫폼)조차 아무것도 성공 못 했을 때만 CI를 실패로 표시한다.
    if ok_count == 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
