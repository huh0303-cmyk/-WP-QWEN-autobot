#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""koreanews365.com에 문의하기(Contact) 페이지 생성"""
import os
import requests

WP_USER = "huh0303@gmail.com"
SITE_URL = "https://koreanews365.com"
WP_PASS = os.getenv("KOREANEWS365COM", "")
CONTACT_EMAIL = "huh0303@gmail.com"

CONTENT = f"""<p>koreanews365.com에 문의사항이 있으시면 아래 이메일로 연락해주세요.</p>
<p><strong>이메일:</strong> {CONTACT_EMAIL}</p>
<p>콘텐츠 수정 요청, 보도자료 제보, 광고 및 제휴 문의 등 모두 환영합니다.</p>"""


def main():
    if not WP_PASS:
        print("❌ KOREANEWS365COM 비밀번호 없음")
        return
    r = requests.post(f"{SITE_URL}/wp-json/wp/v2/pages",
                      auth=(WP_USER, WP_PASS),
                      json={"title": "문의하기", "slug": "contact", "content": CONTENT, "status": "publish"},
                      timeout=20)
    print(f"HTTP {r.status_code}")
    if r.status_code in (200, 201):
        print(f"✅ 생성 완료: {r.json().get('link')}")
    else:
        print(f"❌ 실패: {r.text[:300]}")


if __name__ == "__main__":
    main()
