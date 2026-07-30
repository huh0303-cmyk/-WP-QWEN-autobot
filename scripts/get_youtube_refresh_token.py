#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
get_youtube_refresh_token.py
─────────────────────────────────────────────────────────────
유튜브 업로드 권한(youtube.upload)용 refresh_token을 로컬에서 한 번만
발급받기 위한 스크립트. 실행하면 기본 브라우저가 자동으로 열리고,
업로드할 유튜브 채널 계정으로 로그인 → 허용을 누르면 터미널에
refresh_token이 출력된다.

사용법:
    pip install google-auth-oauthlib
    python scripts/get_youtube_refresh_token.py <CLIENT_ID> <CLIENT_SECRET>

출력되는 refresh_token을 GitHub Secrets의 YOUTUBE_OAUTH_REFRESH_TOKEN에,
CLIENT_ID/CLIENT_SECRET을 각각 YOUTUBE_OAUTH_CLIENT_ID / _CLIENT_SECRET에 등록.
"""

import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    if len(sys.argv) != 3:
        print("사용법: python scripts/get_youtube_refresh_token.py <CLIENT_ID> <CLIENT_SECRET>")
        raise SystemExit(1)

    client_id, client_secret = sys.argv[1], sys.argv[2]

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("먼저 설치: pip install google-auth-oauthlib")
        raise SystemExit(1)

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(
        client_config, scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )
    print("브라우저가 열립니다 — 업로드할 유튜브 채널 계정으로 로그인 후 허용을 눌러주세요...")
    creds = flow.run_local_server(port=0)

    print("\n" + "=" * 60)
    print("아래 값을 GitHub Secrets에 등록하세요:")
    print("=" * 60)
    print(f"YOUTUBE_OAUTH_CLIENT_ID     = {client_id}")
    print(f"YOUTUBE_OAUTH_CLIENT_SECRET = {client_secret}")
    print(f"YOUTUBE_OAUTH_REFRESH_TOKEN = {creds.refresh_token}")
    print("=" * 60)


if __name__ == "__main__":
    main()
