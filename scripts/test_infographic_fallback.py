#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_infographic_fallback.py
autopost_mega.py의 인포그래픽 폴백 로직만 따로 떼어 실제 동작 검증.
(발행은 하지 않고, WP 미디어 라이브러리 업로드까지만 확인 후 테스트 미디어는 삭제)
"""
import os, sys
sys.path.insert(0, "scripts")
import autopost_mega as m

SITE_URL = "https://k-health365.com"
WP_USER = "huh0303@gmail.com"
WP_PASS = os.environ["KHEALTH365COM"]

test_keyword = "홍삼 효능과 부작용 테스트"
theme = "건강과 의학"
lang = "ko"

print("1) 카드 이미지 생성 테스트")
path = m.generate_infographic_card(test_keyword, theme, lang)
print(f"   생성됨: {path}, size={os.path.getsize(path)} bytes")

print("2) WP 미디어 업로드 테스트")
url = m.upload_local_image_to_wp(SITE_URL, WP_PASS, path, "test-infographic-fallback")
print(f"   업로드 결과 URL: {url}")

if url:
    print("✅ 인포그래픽 폴백 파이프라인 정상 작동 확인")
    # 테스트 미디어 정리 (실제 발행물 아님)
    import requests, re
    media_id = None
    r = requests.get(f"{SITE_URL}/wp-json/wp/v2/media", auth=(WP_USER, WP_PASS),
                      params={"search": "test-infographic-fallback", "per_page": 5}, timeout=15)
    if r.status_code == 200:
        for item in r.json():
            if "test-infographic-fallback" in item.get("source_url", ""):
                media_id = item["id"]
    if media_id:
        dr = requests.delete(f"{SITE_URL}/wp-json/wp/v2/media/{media_id}",
                              auth=(WP_USER, WP_PASS), params={"force": True}, timeout=15)
        print(f"   테스트 미디어 정리: HTTP {dr.status_code}")
else:
    print("❌ 업로드 실패 — 파이프라인 점검 필요")

with open("test_infographic_fallback_result.txt", "w", encoding="utf-8") as f:
    f.write(f"card_path={path}\nuploaded_url={url}\n")
