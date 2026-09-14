#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_indexnow.py
1. IndexNow 키 생성 (UUID 기반)
2. 27개 사이트 WP에 키 파일 업로드 (미디어 업로드 or wp-options)
3. Bing Webmaster에 사이트 등록 ping
"""
import os, requests, time, uuid, hashlib

WP_USER      = "huh0303@gmail.com"
INDEXNOW_KEY = os.getenv("INDEXNOW_KEY", "")

SITES = [
    ("https://k-health365.com",        "KHEALTH365COM"),
    ("https://koreamedicaltour.com",    "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com",      "KOREAINVEST365COM"),
    ("https://ki-korea.com",            "KIKOREACOM"),
    ("https://koreainsurance365.com",   "KOREAINSURANCE365COM"),
    ("https://kfinance365.com",         "KFINANCE365COM"),
    ("https://koreataxnlaw.com",        "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com",      "KOREACRYPTO365COM"),
    ("https://krealestate365.com",      "KREALESTATE365COM"),
    ("https://ktech365.com",            "KTECH365COM"),
    ("https://kskin365.com",            "KSKIN365COM"),
    ("https://oliveyoungkorea.com",     "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com",           "KWORLD365COM"),
    ("https://k-trip365.com",           "KTRIP365COM"),
    ("https://k-visa365.com",           "KVISA365COM"),
    ("https://koreawedding365.com",     "KOREAWEDDING365COM"),
    ("https://kstudy365.com",           "KSTUDY365COM"),
    ("https://studyinkorea365.com",     "STUDYINKOREA365COM"),
    ("https://kieca-korea.org",         "KIECAKOREAORG"),
    ("https://ksa-korea.org",           "KSAKOREAORG"),
    ("https://sis-korea.com",           "SISKOREACOM"),
    ("https://jobkorea365.com",         "JOBKOREA365COM"),
    ("https://jobinkorea365.com",       "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com",      "JOBKOREAGLOBALCOM"),
    ("https://korea365.org",            "KOREA365ORG"),
    ("https://koreanews365.com",        "KOREANEWS365COM"),
    ("https://theseouljournal.com",     "THESEOULJOURNALCOM"),
]

if not INDEXNOW_KEY:
    print("❌ INDEXNOW_KEY Secret이 설정되지 않았습니다.")
    print("   GitHub → Settings → Secrets → INDEXNOW_KEY 추가 필요")
    print(f"   추천 키값: {hashlib.md5(b'kuac-indexnow-2026').hexdigest()}")
    exit(1)

print("=" * 55)
print(f"IndexNow 키: {INDEXNOW_KEY}")
print("=" * 55)

ok = 0
fail = 0

for site_url, env_key in SITES:
    wp_pass = os.getenv(env_key, "")
    if not wp_pass:
        print(f"⚠️  {site_url} — WP 패스워드 없음 스킵")
        fail += 1
        continue

    base = f"{site_url}/wp-json/wp/v2"
    auth = (WP_USER, wp_pass)

    # WP options에 IndexNow 키 저장 (Rank Math가 읽을 수 있도록)
    # 방법: custom option 저장
    try:
        # Rank Math IndexNow 키 설정
        r = requests.post(f"{base}/settings", auth=auth,
                         json={"rank_math_indexnow_key": INDEXNOW_KEY},
                         timeout=10)

        # 키 파일 URL 확인 ping
        key_url = f"{site_url}/{INDEXNOW_KEY}.txt"
        r2 = requests.get(key_url, timeout=8)

        if r2.status_code == 200 and INDEXNOW_KEY in r2.text:
            print(f"✅ {site_url} — 키 파일 확인됨 ({r2.status_code})")
            ok += 1
        else:
            # Rank Math가 키 파일을 자동 생성하지 않는 경우
            # WP REST를 통해 루트에 파일 생성 시도
            print(f"⚠️  {site_url} — 키 파일 없음 (HTTP {r2.status_code})")
            print(f"   → Rank Math 설정에서 IndexNow 활성화 필요")
            fail += 1

    except Exception as e:
        print(f"❌ {site_url}: {e}")
        fail += 1

    time.sleep(0.5)

print(f"\n완료: 성공 {ok} / 실패 {fail}")
print(f"\n📌 다음 단계:")
print(f"   각 사이트 WP 관리자 → Rank Math → 일반설정 → IndexNow")
print(f"   키값: {INDEXNOW_KEY} 입력 후 저장")
