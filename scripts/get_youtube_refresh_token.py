#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
get_youtube_refresh_token.py
─────────────────────────────────────────────────────────────
플리채널 5개(globalmusic/healing/starbucks/mbb/kpop) 각각의 유튜브 채널용
OAuth 리프레시 토큰을 발급받기 위한 1회성 로컬 스크립트. 채널마다 그 채널이
연결된 구글 계정으로 로그인해서 딱 한 번만 승인하면 되고, 그 뒤로는 이
토큰으로 사람 개입 없이 계속 업로드할 수 있다.

로컬 서버(run_local_server) 방식을 쓴다 — OOB(코드 직접 복붙) 리다이렉트는
2026-08-06부터 구글이 새로 만든 OAuth 클라이언트에 대해 차단해서 더 이상
작동하지 않는다("OOB flow has been blocked"). 이 방식은 브라우저 승인 후
자동으로 로컬호스트로 리다이렉트돼서 코드를 복붙할 필요가 없다.

사용법:
    python scripts/get_youtube_refresh_token.py

필요 환경변수(Secrets, .env에 이미 있어야 함):
    YOUTUBE_OAUTH_CLIENT_ID
    YOUTUBE_OAUTH_CLIENT_SECRET
    (5개 채널 모두 같은 OAuth 클라이언트 앱을 공유해도 됨 — 계정만 다르게 로그인)
"""
import os
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _load_dotenv():
    # .env 파일은 그냥 텍스트 파일이라 셸에 자동으로 로드되지 않는다 —
    # python-dotenv 설치 없이 직접 KEY=VALUE 줄만 파싱해서 os.environ에 넣는다.
    # (기존 셸 환경변수가 있으면 그게 우선 — .env 값으로 덮어쓰지 않는다.)
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

CLIENT_ID = os.environ.get("YOUTUBE_OAUTH_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRET", "")
# 2026-09-03: youtube.upload 단독 스코프로는 업로드 직전 채널 신원 확인
# (automation_hub/youtube_identity.py의 channels().list(mine=true))이
# "Insufficient Permission"으로 실패한다(globalmusic에서 실제 발생). 업로드
# 권한을 포함하면서 읽기도 되는 전체 youtube 스코프로 재발급해야 한다.
SCOPE = "https://www.googleapis.com/auth/youtube"

CHANNELS = ["globalmusic", "healing", "starbucks", "mbb", "kpop"]

# 2026-08-15: 위 5개 플리채널과 똑같이 공용 client_id 불일치로 깨져있던 걸 확인한
# 지식/아카이브 10채널도 추가. 짧은 키와 실제 GitHub Secret 접미사가 다른
# 채널들이 있어서(예: nasa → NASA_SPACE_TIMES) 별도 매핑 사용.
EXTRA_CHANNELS = {
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

# 2026-08-15: Health Clinic 3채널도 같은 client_id 불일치로 unauthorized_client였음.
# 이 셋은 시크릿 이름 접두어 자체가 다름(YOUTUBE_OAUTH_REFRESH_TOKEN_ 아니라
# HEALTH_CLINIC_YOUTUBE_REFRESH_TOKEN_) — 값은 EXTRA_CHANNELS_FULL_NAME에 전체
# 시크릿 이름을 직접 넣어서 처리.
EXTRA_CHANNELS_FULL_NAME = {
    "health_kr": "HEALTH_CLINIC_YOUTUBE_REFRESH_TOKEN_KR",
    "health_en": "HEALTH_CLINIC_YOUTUBE_REFRESH_TOKEN_EN",
    "health_jp": "HEALTH_CLINIC_YOUTUBE_REFRESH_TOKEN_JP",
}


def log(msg):
    print(msg, flush=True)


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        log("❌ YOUTUBE_OAUTH_CLIENT_ID / YOUTUBE_OAUTH_CLIENT_SECRET이 .env에 없습니다.")
        log("   구글 클라우드 콘솔 > API 및 서비스 > 사용자 인증 정보에서 기존 OAuth 클라이언트 값을 .env에 추가해주세요.")
        raise SystemExit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        log("먼저 설치: pip install google-auth-oauthlib")
        raise SystemExit(1)

    client_config = {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    all_keys = CHANNELS + list(EXTRA_CHANNELS.keys()) + list(EXTRA_CHANNELS_FULL_NAME.keys())
    log(f"채널 {len(all_keys)}개 각각에 대해 순서대로 진행합니다. 그 채널이 연결된 구글 계정으로 로그인해서 승인해주세요.")
    log("(다른 채널 차례에는 반드시 그 채널 계정으로 다시 로그인/전환해야 합니다)\n")

    results = {}
    for key in all_keys:
        go = input(f"=== [{key}] 채널 인증 시작 — 진행하려면 엔터, 건너뛰려면 s+엔터: ").strip().lower()
        if go == "s":
            log(f"   ⏭️  {key} 건너뜀\n")
            continue

        flow = InstalledAppFlow.from_client_config(client_config, scopes=[SCOPE])
        log(f"[{key}] 브라우저가 열립니다 — 그 채널 계정으로 로그인 후 허용을 눌러주세요...")
        try:
            creds = flow.run_local_server(port=0)
        except Exception as e:
            log(f"   ❌ 인증 실패: {e}\n")
            continue

        if not creds.refresh_token:
            log("   ⚠️ refresh_token이 없습니다 (이미 한 번 승인한 적 있으면 안 줄 수 있음 — "
                "구글 계정 > 보안 > 타사 앱 액세스에서 기존 연결을 해제하고 다시 시도해보세요)\n")
            continue

        results[key] = creds.refresh_token
        log(f"   ✅ {key} 완료\n")

    if not results:
        log("발급된 토큰이 없습니다.")
        return

    log("\n" + "=" * 60)
    log("발급된 리프레시 토큰 (GitHub Secrets에 아래 이름으로 등록하세요):")
    log("=" * 60)
    for key, token in results.items():
        if key in EXTRA_CHANNELS_FULL_NAME:
            log(f"{EXTRA_CHANNELS_FULL_NAME[key]} = {token}")
        else:
            secret_suffix = EXTRA_CHANNELS.get(key, key.upper())
            log(f"YOUTUBE_OAUTH_REFRESH_TOKEN_{secret_suffix} = {token}")


if __name__ == "__main__":
    main()
