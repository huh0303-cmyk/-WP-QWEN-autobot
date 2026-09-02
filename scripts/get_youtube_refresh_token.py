#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
get_youtube_refresh_token.py
─────────────────────────────────────────────────────────────
등록부의 정확한 10개 유튜브 채널(플레이리스트 5 + 지식 5) 각각의
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
import argparse
import os
import subprocess
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
SCOPES = [
    # Upload workers downscope to youtube.upload; readiness uses readonly.
    # Do not grant youtube.force-ssl/youtube: those scopes permit status mutation.
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from automation_hub.youtube_registry import load_channels
from automation_hub.youtube_readiness import FORBIDDEN_MUTATION_SCOPES

TARGETS = {channel.channel_key: channel.secret_profile for channel in load_channels()}


def log(msg):
    print(msg, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", "huh0303-cmyk/-WP-QWEN-autobot"))
    parser.add_argument("--show-token", action="store_true", help="Print tokens instead of saving with gh (unsafe)")
    args = parser.parse_args()
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

    all_keys = list(TARGETS)
    log(f"채널 {len(all_keys)}개 각각에 대해 순서대로 진행합니다. 그 채널이 연결된 구글 계정으로 로그인해서 승인해주세요.")
    log("(다른 채널 차례에는 반드시 그 채널 계정으로 다시 로그인/전환해야 합니다)\n")

    results = {}
    for key in all_keys:
        go = input(f"=== [{key}] 채널 인증 시작 — 진행하려면 엔터, 건너뛰려면 s+엔터: ").strip().lower()
        if go == "s":
            log(f"   ⏭️  {key} 건너뜀\n")
            continue

        flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
        log(f"[{key}] 브라우저가 열립니다 — 그 채널 계정으로 로그인 후 허용을 눌러주세요...")
        try:
            creds = flow.run_local_server(
                port=0, access_type="offline", prompt="consent", include_granted_scopes="true",
            )
        except Exception as e:
            log(f"   ❌ 인증 실패: {e}\n")
            continue

        if not creds.refresh_token:
            log("   ⚠️ refresh_token이 없습니다 (이미 한 번 승인한 적 있으면 안 줄 수 있음 — "
                "구글 계정 > 보안 > 타사 앱 액세스에서 기존 연결을 해제하고 다시 시도해보세요)\n")
            continue

        granted = set(creds.granted_scopes or ())
        if not set(SCOPES).issubset(granted):
            log(f"   ❌ 필수 scope 누락: {sorted(set(SCOPES) - granted)}\n")
            continue
        if granted & FORBIDDEN_MUTATION_SCOPES:
            log(f"   ❌ 공개상태 변경 가능 scope가 기존 동의에 남아 있습니다: {sorted(granted & FORBIDDEN_MUTATION_SCOPES)}")
            log("   Google 계정에서 기존 앱 연결을 해제한 뒤 다시 승인하세요. 토큰을 저장하지 않습니다.\n")
            continue

        results[key] = creds.refresh_token
        log(f"   ✅ {key} 완료\n")

    if not results:
        log("발급된 토큰이 없습니다.")
        return

    log("\n" + "=" * 60)
    log("발급된 리프레시 토큰 저장 결과:")
    log("=" * 60)
    for key, token in results.items():
        secret_name = f"YOUTUBE_OAUTH_REFRESH_TOKEN_{TARGETS[key]}"
        if args.show_token:
            log(f"{secret_name} = {token}")
            continue
        try:
            subprocess.run(
                ["gh", "secret", "set", secret_name, "--repo", args.repo],
                input=token, check=True, capture_output=True, text=True, timeout=30,
            )
            log(f"✅ {secret_name}: GitHub Secret 저장 완료")
        except (OSError, subprocess.SubprocessError) as exc:
            log(f"❌ {secret_name}: GitHub Secret 저장 실패 ({type(exc).__name__}); 토큰은 출력하지 않았습니다")
            log("   gh auth login 후 다시 실행하거나, 노출 위험을 이해한 경우에만 --show-token을 사용하세요.")


if __name__ == "__main__":
    main()
