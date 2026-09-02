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

    GMAIL_APP_PASSWORD                             - 완료 요약 메일(선택, 인스타/쓰레드
                                                      캡션은 이 메일로만 전달됨)
"""

import os
import sys
import json
import time
import hashlib
import re
from datetime import datetime, timedelta, timezone

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

GMAIL_USER = "huh0303@gmail.com"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

GRAPH_VERSION = "v21.0"


def log(msg):
    print(msg, flush=True)


def sanitize_error(error):
    """Keep credentials out of logs, emails, and uploaded result artifacts."""
    message = str(error)
    for secret in (
        YOUTUBE_OAUTH_CLIENT_ID,
        YOUTUBE_OAUTH_CLIENT_SECRET,
        YOUTUBE_OAUTH_REFRESH_TOKEN,
        TIKTOK_ACCESS_TOKEN,
        FB_PAGE_ACCESS_TOKEN,
    ):
        if secret:
            message = message.replace(secret, "[REDACTED]")
    return re.sub(r"(?i)(access_token=)[^&\\s'\"]+", r"\1[REDACTED]", message)


def send_email(subject, body):
    if os.environ.get("NORMAL_COMPLETION_EMAIL_ENABLED", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        log("normal SNS completion email suppressed; use the CEO control room")
        return
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


def platform_copy(meta, platform, max_hashtags=8):
    native = (meta.get("platform_copy") or {}).get(platform) or {}
    tags = " ".join(f"#{h}" for h in native.get("hashtags", [])[:max_hashtags])
    parts = [native.get("hook", ""), native.get("caption", ""), native.get("cta", "")]
    caption = "\n".join(part.strip() for part in parts if part and part.strip())
    return {"title": native.get("title", "").strip(), "caption": f"{caption}\n\n{tags}".strip()}


def content_fingerprint(meta, platform):
    identity = {"platform": platform, "video": meta.get("public_video_url") or meta.get("video_path"),
                "copy": (meta.get("platform_copy") or {}).get(platform),
                "youtube_title": meta.get("youtube_title") if platform == "youtube" else None}
    return hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def recommended_publish_times(meta):
    """Deterministic stagger suggestions; no simultaneous mechanical publishing."""
    created = datetime.fromisoformat(meta["created_at"]) if meta.get("created_at") else datetime.now(timezone.utc)
    offsets = {"youtube": 37, "tiktok": 83, "instagram": 149, "facebook": 221, "threads": 307}
    seed = int(hashlib.sha256((meta.get("youtube_title") or "content").encode()).hexdigest()[:8], 16)
    return {name: (created + timedelta(minutes=minutes + seed % 23)).isoformat() for name, minutes in offsets.items()}


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
            _, response = request.next_chunk(num_retries=0)
        except Exception as e:
            retries += 1
            if retries >= 3:
                raise
            time.sleep(min(2 ** retries, 8))

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
            "title": (platform_copy(meta, "tiktok")["title"] or platform_copy(meta, "tiktok")["caption"])[:150],
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
    caption = platform_copy(meta, "facebook")["caption"]

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
# Instagram / Threads — 두 플랫폼 다 API로 만든 컨테이너는 "초안"으로
# 앱에 남지 않고 24시간 뒤 그냥 만료돼버린다(진짜 임시저장 기능이 없음).
# 그래서 여기서는 API로 대신 올려버리지 않고, 캡션+영상 링크만 준비해서
# 사용자가 앱에서 직접 업로드하게 한다("최종 업로드는 내가 함" 원칙).
# ════════════════════════════════════════════════════════════
def publish_instagram(meta):
    if not meta.get("public_video_url"):
        return {"ok": False, "skipped": True, "reason": "공개 video_url 없음 — 드라이브 업로드 설정 확인 필요"}
    caption = platform_copy(meta, "instagram")["caption"]
    return {
        "ok": True,
        "note": "인스타그램 API는 임시저장이 없어 자동 게시 안 함 — 아래 캡션으로 직접 릴스 업로드 필요",
        "video_url": meta["public_video_url"],
        "caption": caption,
    }


def publish_threads(meta):
    if not meta.get("public_video_url"):
        return {"ok": False, "skipped": True, "reason": "공개 video_url 없음 — 드라이브 업로드 설정 확인 필요"}
    caption = platform_copy(meta, "threads", max_hashtags=3)["caption"]
    return {
        "ok": True,
        "note": "쓰레드 API는 임시저장이 없어 자동 게시 안 함 — 아래 캡션으로 직접 업로드 필요",
        "video_url": meta["public_video_url"],
        "caption": caption,
    }


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
    publish_times = recommended_publish_times(meta)
    video_path = meta.get("video_path") or os.path.join(os.path.dirname(meta_path), "final.mp4")
    if not os.path.exists(video_path):
        log(f"❌ 영상 파일 없음: {video_path}")
        raise SystemExit(1)

    log(f"게시 시작 — {label}, 영상: {video_path}")
    results = {}
    state_path = os.path.join(os.path.dirname(meta_path) or WORKDIR, "social_publish_state.json")
    try:
        with open(state_path, encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {}
    for name, fn in PLATFORMS.items():
        log(f"  → {name} 게시 중...")
        fingerprint = content_fingerprint(meta, name)
        if state.get(name) == fingerprint:
            result = {"ok": False, "skipped": True, "reason": "동일 플랫폼 중복 콘텐츠 차단"}
            results[name] = result
            log(f"     ⏭️  건너뜀: {result['reason']}")
            continue
        try:
            result = fn(video_path, meta)
        except Exception as e:
            result = {"ok": False, "error": sanitize_error(e)}
        results[name] = result
        result["recommended_publish_at"] = publish_times[name]
        if result.get("ok"):
            state[name] = fingerprint
        if result.get("skipped"):
            log(f"     ⏭️  건너뜀: {result.get('reason')}")
        elif result.get("ok"):
            log(f"     ✅ {result.get('note') or '완료'} — {result.get('url') or result.get('video_id') or result.get('publish_id') or ''}")
        else:
            log(f"     ❌ 실패: {result.get('error')}")

    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    result_path = os.path.join(os.path.dirname(meta_path) or WORKDIR, f"publish_result_{os.path.basename(meta_path)}")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok_count = sum(1 for r in results.values() if r.get("ok"))
    skip_count = sum(1 for r in results.values() if r.get("skipped"))
    fail_count = len(results) - ok_count - skip_count

    summary_lines = [f"[{label}] {meta.get('youtube_title', '')}", "", "※ 전부 발행 대기 상태입니다 — 최종 공개는 직접 눌러야 합니다.", ""]
    for name, r in results.items():
        if r.get("ok"):
            line = f"✅ {name}: {r.get('note') or '완료'}"
            if r.get("url"):
                line += f"\n   {r['url']}"
            if r.get("caption"):
                line += f"\n   영상: {r.get('video_url')}\n   캡션:\n   {r['caption']}"
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
    # 플랫폼은 독립적으로 끝까지 시도하되, 실제 실패가 하나라도 있으면
    # 워크플로도 실패시켜 실패를 성공으로 기록하지 않는다.
    if fail_count:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
