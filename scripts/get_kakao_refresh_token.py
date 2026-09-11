#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
get_kakao_refresh_token.py
─────────────────────────────────────────────────────────────
카카오톡 "나에게 보내기(memo)" API용 access_token/refresh_token을
로컬에서 한 번만 발급받기 위한 스크립트.

사용법:
    pip install requests
    python scripts/get_kakao_refresh_token.py <REST_API_KEY>

실행하면 브라우저로 열어야 할 인가 URL이 출력된다. 그 URL을 열어서
카카오 계정으로 로그인 -> 동의하면, 브라우저가
"https://localhost:8888/?code=..." 같은(안 열리는) 페이지로 이동한다.
그 주소창에 뜬 전체 URL을 복사해서 이 스크립트에 붙여넣으면 토큰이
발급된다.

출력되는 값을 GitHub Secrets의 KAKAO_REST_API_KEY / KAKAO_REFRESH_TOKEN에 등록.
"""
import sys
import urllib.parse

import requests

REDIRECT_URI = "https://localhost:8888"


def main():
    if len(sys.argv) != 2:
        print("사용법: python scripts/get_kakao_refresh_token.py <REST_API_KEY>")
        raise SystemExit(1)

    rest_api_key = sys.argv[1]

    auth_url = (
        "https://kauth.kakao.com/oauth/authorize"
        f"?client_id={rest_api_key}&redirect_uri={REDIRECT_URI}"
        "&response_type=code&scope=talk_message"
    )

    print("=" * 70)
    print("아래 URL을 브라우저에 붙여넣어 열어주세요:")
    print(auth_url)
    print("=" * 70)
    print("로그인/동의 후 이동되는 페이지가 '연결할 수 없음' 같은 에러 화면이")
    print("떠도 정상입니다 — 그 화면의 주소창에 있는 전체 URL을 복사해서")
    print("아래에 붙여넣어주세요.")
    print()

    redirected_url = input("리디렉션된 전체 URL 붙여넣기: ").strip()

    parsed = urllib.parse.urlparse(redirected_url)
    qs = urllib.parse.parse_qs(parsed.query)
    code = qs.get("code", [None])[0]
    if not code:
        print("❌ URL에서 code 값을 못 찾았습니다. 전체 주소를 다시 확인해주세요.")
        raise SystemExit(1)

    r = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": rest_api_key,
            "redirect_uri": REDIRECT_URI,
            "code": code,
        },
        timeout=15,
    )
    if r.status_code != 200:
        print(f"❌ 토큰 발급 실패: HTTP {r.status_code}\n{r.text}")
        raise SystemExit(1)

    data = r.json()
    print("\n" + "=" * 70)
    print("아래 값을 GitHub Secrets에 등록하세요:")
    print("=" * 70)
    print(f"KAKAO_REST_API_KEY = {rest_api_key}")
    print(f"KAKAO_REFRESH_TOKEN = {data['refresh_token']}")
    print("=" * 70)
    print(f"(참고: access_token은 {data.get('expires_in', 0)//3600}시간, "
          f"refresh_token은 {data.get('refresh_token_expires_in', 0)//86400}일 유효 — "
          f"자동화 스크립트는 매번 refresh_token으로 새 access_token을 받아서 씀)")


if __name__ == "__main__":
    main()
