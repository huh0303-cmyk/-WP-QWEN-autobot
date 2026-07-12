#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""k-trip365.com 401 권한 문제 진단 + kworld365.com 발행 현황 확인"""
import os, json
import requests

WP_USER = "huh0303@gmail.com"


def diagnose_ktrip():
    print("=" * 60)
    print("🔍 k-trip365.com 권한 진단")
    print("=" * 60)
    wp_pass = os.getenv("KTRIP365COM", "")
    if not wp_pass:
        print("❌ KTRIP365COM 비밀번호 없음")
        return

    site_url = "https://k-trip365.com"

    # 1) 내 사용자 정보 및 역할 확인
    r = requests.get(f"{site_url}/wp-json/wp/v2/users/me",
                     auth=(WP_USER, wp_pass),
                     params={"context": "edit"}, timeout=15)
    print(f"\n[내 계정 정보] HTTP {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"  이름: {data.get('name')}")
        print(f"  역할(roles): {data.get('roles')}")
        print(f"  권한(capabilities) 일부: {json.dumps(data.get('capabilities', {}), ensure_ascii=False)[:300]}")
    else:
        print(f"  응답: {r.text[:300]}")

    # 2) 글 목록 조회는 되는지 (읽기 권한 확인)
    r2 = requests.get(f"{site_url}/wp-json/wp/v2/posts",
                      auth=(WP_USER, wp_pass), params={"per_page": 1}, timeout=15)
    print(f"\n[글 목록 조회(읽기)] HTTP {r2.status_code}")

    # 3) 실제로 글 생성 시도 (테스트 후 바로 삭제)
    r3 = requests.post(f"{site_url}/wp-json/wp/v2/posts",
                       auth=(WP_USER, wp_pass),
                       json={"title": "권한테스트-삭제예정", "content": "test", "status": "draft"},
                       timeout=15)
    print(f"\n[글 생성 테스트] HTTP {r3.status_code}")
    print(f"  응답: {r3.text[:300]}")
    if r3.status_code in (200, 201):
        test_id = r3.json().get("id")
        dr = requests.delete(f"{site_url}/wp-json/wp/v2/posts/{test_id}",
                             auth=(WP_USER, wp_pass), params={"force": True}, timeout=15)
        print(f"  (테스트 글 삭제: HTTP {dr.status_code})")

    # 4) 애플리케이션 비밀번호 목록 확인 (내가 몇 개나 만들어놨는지)
    r4 = requests.get(f"{site_url}/wp-json/wp/v2/users/me/application-passwords",
                      auth=(WP_USER, wp_pass), timeout=15)
    print(f"\n[애플리케이션 비밀번호 목록] HTTP {r4.status_code}")
    if r4.status_code == 200:
        for ap in r4.json():
            print(f"  - {ap.get('name')} (생성: {ap.get('created')}, 마지막사용: {ap.get('last_used')})")
    else:
        print(f"  응답: {r4.text[:300]}")


def check_kworld():
    print("\n" + "=" * 60)
    print("🔍 kworld365.com 발행 현황 확인")
    print("=" * 60)
    wp_pass = os.getenv("KWORLD365COM", "")
    if not wp_pass:
        print("❌ KWORLD365COM 비밀번호 없음")
        return

    site_url = "https://kworld365.com"
    r = requests.get(f"{site_url}/wp-json/wp/v2/posts",
                     auth=(WP_USER, wp_pass),
                     params={"per_page": 20, "status": "publish", "orderby": "date",
                             "order": "desc", "_fields": "id,title,date,link,categories"},
                     timeout=15)
    total = r.headers.get("X-WP-Total", "?")
    print(f"HTTP {r.status_code} | 전체 발행글수(X-WP-Total): {total}")
    if r.status_code == 200:
        for p in r.json():
            title = p.get("title", {}).get("rendered", "")[:40]
            print(f"  - [{p.get('date')}] {title} (카테고리ID: {p.get('categories')})")


if __name__ == "__main__":
    diagnose_ktrip()
    check_kworld()
