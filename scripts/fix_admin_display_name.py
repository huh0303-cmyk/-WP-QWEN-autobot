#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_admin_display_name.py
─────────────────────────────────────────────────────────────
2026-08-22: 27개 사이트 전부에서 WP 관리자 계정(REST API 인증에 쓰는
huh0303@gmail.com 계정) 자체의 공개 표시 이름이 이메일 원문 그대로
/wp-json/wp/v2/users 에 노출되고 있던 게 실사용자 검증으로 확인됨
(예: koreainvest365.com -> {"id":1,"name":"huh0303@gmail.com",
"slug":"huh0303gmail-com","link":".../author/huh0303gmail-com/"}).

이건 각 사이트가 서로 다른 필자(AUTHOR_BY_SITE_DEF)로 글을 쓰게 만든
것과 완전히 별개로, WP REST API의 공개 users 엔드포인트가 인증 없이
누구나 조회 가능해서 생긴 문제 — 실제 발행글의 저자는 이미 사이트별로
분리돼 있지만, 이 관리자 계정 자체가 huh0303gmail-com이라는 슬러그로
남아있는 한 "이 27개 사이트가 전부 한 사람 것"이라는 사실이 누구나 5초
안에 확인 가능한 상태였다.

이 스크립트는 관리자 계정의 표시 이름/슬러그만 안전한 값으로 바꾼다
(비밀번호·이메일 자체는 안 건드림 — REST API 인증은 계속 정상 작동).
글쓴이(byline)는 여전히 사이트별 페르소나 그대로 유지된다.
"""
import os
import sys
import requests

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

WP_USER = "huh0303@gmail.com"
SAFE_NAME = os.environ.get("SAFE_ADMIN_NAME", "Editorial Team")
SAFE_SLUG = os.environ.get("SAFE_ADMIN_SLUG", "editorial-team")

# autopost_mega.py SITES_CONFIG와 동일한 (url, wp_pass_env) 목록.
# publish_scheduler.py와 같은 관례로, 무거운 google-genai 의존성을 피하려고
# autopost_mega.py를 import하지 않고 독립 유지.
SITES = [
    ("https://k-health365.com", "KHEALTH365COM"),
    ("https://koreamedicaltour.com", "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com", "KOREAINVEST365COM"),
    ("https://ki-korea.com", "KIKOREACOM"),
    ("https://koreainsurance365.com", "KOREAINSURANCE365COM"),
    ("https://kfinance365.com", "KFINANCE365COM"),
    ("https://koreataxnlaw.com", "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com", "KOREACRYPTO365COM"),
    ("https://krealestate365.com", "KREALESTATE365COM"),
    ("https://ktech365.com", "KTECH365COM"),
    # kskin365.com — retired, no new content, skip.
    ("https://oliveyoungkorea.com", "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com", "KWORLD365COM"),
    ("https://k-trip365.com", "KTRIP365COM"),
    ("https://k-visa365.com", "KVISA365COM"),
    ("https://koreawedding365.com", "KOREAWEDDING365COM"),
    ("https://kstudy365.com", "KSTUDY365COM"),
    ("https://studyinkorea365.com", "STUDYINKOREA365COM"),
    ("https://kieca-korea.org", "KIECAKOREAORG"),
    ("https://ksa-korea.org", "KSAKOREAORG"),
    ("https://sis-korea.com", "SISKOREACOM"),
    ("https://jobkorea365.com", "JOBKOREA365COM"),
    ("https://jobinkorea365.com", "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com", "JOBKOREAGLOBALCOM"),
    ("https://korea365.org", "KOREA365ORG"),
    ("https://koreanews365.com", "KOREANEWS365COM"),
    ("https://theseouljournal.com", "THESEOULJOURNALCOM"),
]


def find_admin_user_id(url, pw):
    try:
        r = requests.get(f"{url}/wp-json/wp/v2/users", auth=(WP_USER, pw),
                          params={"search": "huh0303", "per_page": 10, "context": "edit"},
                          timeout=15)
        if r.status_code != 200:
            return None, f"list HTTP {r.status_code}"
        for u in r.json():
            if "huh0303" in (u.get("slug") or "").lower() or "gmail" in (u.get("email") or "").lower():
                return u.get("id"), None
        return None, "admin user not found in search"
    except Exception as e:
        return None, str(e)[:150]


def main():
    print(f"목표 표시이름: '{SAFE_NAME}' (slug: {SAFE_SLUG})\n")
    ok = fail = skip = 0
    for url, env_name in SITES:
        pw = os.getenv(env_name, "")
        if not pw:
            print(f"⏭  {url} — {env_name} 시크릿 없음, 스킵")
            skip += 1
            continue
        uid, err = find_admin_user_id(url, pw)
        if uid is None:
            print(f"⚠️  {url} — 관리자 계정 못 찾음 ({err})")
            fail += 1
            continue
        try:
            r = requests.post(
                f"{url}/wp-json/wp/v2/users/{uid}", auth=(WP_USER, pw),
                json={"name": SAFE_NAME, "slug": SAFE_SLUG, "nickname": SAFE_NAME}, timeout=15,
            )
            if r.status_code == 200:
                new_link = r.json().get("link", "")
                print(f"✅ {url} — user {uid} 이름 변경 완료 ({new_link})")
                ok += 1
            else:
                print(f"❌ {url} — user {uid} 변경 실패 HTTP {r.status_code}: {r.text[:150]}")
                fail += 1
        except Exception as e:
            print(f"❌ {url} — 예외: {e}")
            fail += 1

    print(f"\n완료 — 성공:{ok} / 실패:{fail} / 스킵:{skip}")


if __name__ == "__main__":
    main()
