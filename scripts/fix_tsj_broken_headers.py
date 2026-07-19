#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_tsj_broken_headers.py
theseouljournal.com의 깨진 GP Elements(Global Page Headers, Blog Posts Headers)를
휴지통으로 이동. 두 Element 모두 {{post_title}} 등 미치환 플레이스홀더를
그대로 노출하고 있었으며, 실제 제목/본문은 이 Element와 무관하게
테마 기본 출력으로 이미 정상 렌더링되고 있어 삭제해도 콘텐츠 손실 없음.
"""
import os, requests

SITE = "https://theseouljournal.com"
WP_USER = "huh0303@gmail.com"
WP_PASS = os.environ["THESEOULJOURNALCOM"]
auth = requests.auth.HTTPBasicAuth(WP_USER, WP_PASS)

BROKEN_IDS = [2415, 2412]  # Global Page Headers, Blog Posts Headers

_LOG = []
def log(m=""):
    print(m)
    _LOG.append(str(m))

for eid in BROKEN_IDS:
    r = requests.delete(f"{SITE}/wp-json/wp/v2/gp_elements/{eid}",
                         auth=auth, params={"force": False}, timeout=20)
    log(f"[{eid}] 휴지통 이동: HTTP {r.status_code}")
    if r.status_code not in (200, 410):
        log(f"  응답: {r.text[:300]}")

with open("fix_tsj_broken_headers_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(_LOG))
