#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_menu_typo.py — theseouljournal.com 네비게이션 메뉴의 'ECONONOMY' 오타를 'ECONOMY'로 수정"""
import os, requests, json

SITE_URL = "https://theseouljournal.com"
WP_USER = "huh0303@gmail.com"
WP_PASS = os.environ["THESEOULJOURNALCOM"]
auth = (WP_USER, WP_PASS)

_LOG = []
def log(m=""):
    print(m)
    _LOG.append(str(m))

r = requests.get(f"{SITE_URL}/wp-json/wp/v2/menu-items", auth=auth,
                  params={"per_page": 100, "context": "edit"}, timeout=20)
log(f"menu-items 조회: HTTP {r.status_code}")

fixed = 0
if r.status_code == 200:
    items = r.json()
    for item in items:
        title_raw = item.get("title", {})
        title = title_raw.get("raw") if isinstance(title_raw, dict) else title_raw
        title = title or item.get("title", {}).get("rendered", "")
        if "ECONONOMY" in title.upper():
            new_title = title.replace("ECONONOMY", "ECONOMY").replace("econonomy", "economy")
            ur = requests.post(f"{SITE_URL}/wp-json/wp/v2/menu-items/{item['id']}", auth=auth,
                                json={"title": new_title}, timeout=20)
            log(f"메뉴 아이템 #{item['id']}: '{title}' → '{new_title}' — HTTP {ur.status_code}")
            if ur.status_code in (200, 201):
                fixed += 1
else:
    log(f"메뉴 API 접근 실패: {r.text[:300]}")

log(f"\n총 {fixed}건 수정")

with open("fix_menu_typo_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(_LOG))
