#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
upload_mbb_kpop_ready.py
─────────────────────────────────────────────────────────────
2026-08-06~07에 이미 완성돼서 G드라이브에 대기 중인 MBB(Mozart/Bach/Beethoven)
+ K-pop 영상 4개를, 그 채널 전용 OAuth 토큰이 생기는 즉시 한 번에 업로드하는
1회성 로컬 스크립트. GitHub Actions 파이프라인을 안 거치고 로컬에서 바로
그 채널 계정으로 업로드한다 — get_youtube_refresh_token.py로 mbb/kpop 토큰을
발급받은 직후 이 스크립트만 실행하면 끝.

사용법:
    python scripts/upload_mbb_kpop_ready.py [mbb|kpop|all]
    (기본값: all)

필요 환경변수(.env):
    YOUTUBE_OAUTH_CLIENT_ID, YOUTUBE_OAUTH_CLIENT_SECRET   - 기존과 동일한 앱
    YOUTUBE_OAUTH_REFRESH_TOKEN_MBB                        - mbb 채널용
    YOUTUBE_OAUTH_REFRESH_TOKEN_KPOP                       - kpop 채널용
"""
import os
import sys


def _load_dotenv():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(repo_root, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key and key not in os.environ:
                os.environ[key] = value.strip()


_load_dotenv()

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE = (r"G:\.shortcut-targets-by-id\14FPgjTeXjJ3H1dCLn7sbMLRy9PhMacw_"
        r"\플리채널")

VIDEOS = [
    {
        "channel_key": "mbb",
        "video": os.path.join(BASE, "모짜르트_바흐_베트벤클래식", "완성", "2026-08-06-Mozart.mp4"),
        "thumb": os.path.join(BASE, "모짜르트_바흐_베트벤클래식", "완성", "2026-08-06-claude-Mozart_thumbnail.png"),
        "meta": os.path.join(BASE, "모짜르트_바흐_베트벤클래식", "완성", "2026-08-06-claude-Mozart_description.txt"),
    },
    {
        "channel_key": "mbb",
        "video": os.path.join(BASE, "모짜르트_바흐_베트벤클래식", "완성", "2026-08-06-claude-Bach.mp4"),
        "thumb": os.path.join(BASE, "모짜르트_바흐_베트벤클래식", "완성", "2026-08-06-claude-Bach_thumbnail.png"),
        "meta": os.path.join(BASE, "모짜르트_바흐_베트벤클래식", "완성", "2026-08-06-claude-Bach_description.txt"),
    },
    {
        "channel_key": "mbb",
        "video": os.path.join(BASE, "모짜르트_바흐_베트벤클래식", "완성", "2026-08-06-claude-Beethoven.mp4"),
        "thumb": os.path.join(BASE, "모짜르트_바흐_베트벤클래식", "완성", "2026-08-06-claude-Beethoven_thumbnail.png"),
        "meta": os.path.join(BASE, "모짜르트_바흐_베트벤클래식", "완성", "2026-08-06-claude-Beethoven_description.txt"),
    },
    {
        "channel_key": "kpop",
        "video": os.path.join(BASE, "K-pop", "완성", "2026-08-05-claude-Kpop.mp4"),
        "thumb": os.path.join(BASE, "K-pop", "완성", "2026-08-05-claude-Kpop_thumbnail.png"),
        "meta": os.path.join(BASE, "K-pop", "완성", "2026-08-05-claude-Kpop_description.txt"),
    },
]


def log(msg):
    print(msg, flush=True)


def parse_meta(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    title, description = text, text
    if "TITLE:" in text and "DESCRIPTION:" in text:
        title = text.split("TITLE:")[1].split("DESCRIPTION:")[0].strip()
        description = text.split("DESCRIPTION:")[1].strip()
    return title[:100], description


def get_youtube_service(refresh_token):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_OAUTH_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_OAUTH_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    return build("youtube", "v3", credentials=creds)


def upload_one(item):
    from googleapiclient.http import MediaFileUpload

    for key in ("video", "thumb", "meta"):
        if not os.path.exists(item[key]):
            log(f"  ❌ 파일 없음: {item[key]}")
            return False

    token_env = f"YOUTUBE_OAUTH_REFRESH_TOKEN_{item['channel_key'].upper()}"
    refresh_token = os.environ.get(token_env, "")
    if not refresh_token:
        log(f"  ⚠️ {token_env}가 .env에 없어서 건너뜀 — get_youtube_refresh_token.py로 먼저 발급받으세요")
        return False

    title, description = parse_meta(item["meta"])
    log(f"  제목: {title}")

    youtube = get_youtube_service(refresh_token)
    body = {
        "snippet": {"title": title, "description": description, "categoryId": "10"},
        "status": {"selfDeclaredMadeForKids": False, "privacyStatus": "public"},
    }
    media = MediaFileUpload(item["video"], resumable=True, chunksize=5 * 1024 * 1024, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status_obj, response = request.next_chunk(num_retries=5)
        if status_obj:
            log(f"  업로드 진행률: {int(status_obj.progress() * 100)}%")

    video_id = response["id"]
    try:
        youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(item["thumb"])).execute()
    except Exception as e:
        log(f"  ⚠️ 썸네일 설정 실패(무시): {e}")

    log(f"  ✅ 완료: https://youtu.be/{video_id}")
    return True


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    if not os.environ.get("YOUTUBE_OAUTH_CLIENT_ID") or not os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRET"):
        log("❌ YOUTUBE_OAUTH_CLIENT_ID / YOUTUBE_OAUTH_CLIENT_SECRET이 .env에 없습니다.")
        raise SystemExit(1)

    items = VIDEOS if target == "all" else [v for v in VIDEOS if v["channel_key"] == target]
    if not items:
        log(f"❌ '{target}'에 해당하는 영상이 없습니다 (mbb|kpop|all)")
        raise SystemExit(1)

    ok = 0
    for item in items:
        log(f"\n=== [{item['channel_key']}] {os.path.basename(item['video'])} ===")
        if upload_one(item):
            ok += 1

    log(f"\n{ok}/{len(items)}개 업로드 완료")


if __name__ == "__main__":
    main()
