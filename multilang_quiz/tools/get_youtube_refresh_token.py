#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube refresh_token 1회 발급용 로컬 스크립트 (본인 PC에서만 실행)
사전 준비:
  pip install google-auth-oauthlib
사용법:
  python3 get_youtube_refresh_token.py <CLIENT_ID> <CLIENT_SECRET>
실행하면 브라우저가 열리고, 새로 만든 별도 유튜브 채널이 연결된
구글 계정으로 로그인/동의하면 터미널에 refresh_token이 출력됩니다.
그 값을 GitHub Secrets의 ML_YT_REFRESH_TOKEN에 등록하세요.
"""
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

def main():
    if len(sys.argv) != 3:
        print("사용법: python3 get_youtube_refresh_token.py <CLIENT_ID> <CLIENT_SECRET>")
        sys.exit(1)
    client_id, client_secret = sys.argv[1], sys.argv[2]
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
        client_config, scopes=["https://www.googleapis.com/auth/youtube.upload"])
    creds = flow.run_local_server(port=0)
    print("\n=== 아래 값을 GitHub Secrets의 ML_YT_REFRESH_TOKEN 에 등록하세요 ===")
    print(creds.refresh_token)

if __name__ == "__main__":
    main()
