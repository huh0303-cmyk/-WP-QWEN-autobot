#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_duplicate_deletion.py
─────────────────────────────────────────────────────────────
resolve_duplicate_titles.py가 만든 duplicate_titles_manifest.json을 읽어서
중복 제목 글(그룹 내 SEO 점수가 낮은 쪽)을 실제로 휴지통으로 이동한다
(force=false — 완전 영구삭제 아니고 휴지통, 실수 시 복구 가능).

사이트별 WP 비밀번호(REST 쓰기 권한) 필요 — GitHub Actions에서
secrets.<SITE> 환경변수로 주입해서 실행.
"""
import os
import socket
import json
import requests
from collections import defaultdict

# ★ 2026-08-03: GitHub Actions 러너에서 27개 사이트 전체가 "Network is
#   unreachable"로 동시에 실패하는 사고 발생 - IPv6 라우팅이 막혀있는데
#   DNS가 AAAA(IPv6)를 먼저 주는 전형적인 러너 버그. urllib3가 쓰는 소켓
#   생성을 IPv4로 강제해서 회피한다.
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_only_getaddrinfo

WP_USER = "huh0303@gmail.com"
MANIFEST_PATH = "duplicate_titles_manifest.json"

SITE_SECRET_MAP = {
    "https://k-health365.com":        "KHEALTH365COM",
    "https://koreamedicaltour.com":   "KOREAMEDICALTOURCOM",
    "https://koreainvest365.com":     "KOREAINVEST365COM",
    "https://ki-korea.com":           "KIKOREACOM",
    "https://koreainsurance365.com":  "KOREAINSURANCE365COM",
    "https://kfinance365.com":        "KFINANCE365COM",
    "https://koreataxnlaw.com":       "KOREATAXNLAWCOM",
    "https://koreacrypto365.com":     "KOREACRYPTO365COM",
    "https://krealestate365.com":     "KREALESTATE365COM",
    "https://ktech365.com":           "KTECH365COM",
    "https://oliveyoungkorea.com":    "OLIVEYOUNGKOREACOM",
    "https://kworld365.com":          "KWORLD365COM",
    "https://k-trip365.com":          "KTRIP365COM",
    "https://k-visa365.com":          "KVISA365COM",
    "https://koreawedding365.com":    "KOREAWEDDING365COM",
    "https://kstudy365.com":          "KSTUDY365COM",
    "https://studyinkorea365.com":    "STUDYINKOREA365COM",
    "https://kieca-korea.org":        "KIECAKOREAORG",
    "https://ksa-korea.org":          "KSAKOREAORG",
    "https://sis-korea.com":          "SISKOREACOM",
    "https://jobkorea365.com":        "JOBKOREA365COM",
    "https://jobinkorea365.com":      "JOBINKOREA365COM",
    "https://jobkoreaglobal.com":     "JOBKOREAGLOBALCOM",
    "https://korea365.org":           "KOREA365ORG",
    "https://koreanews365.com":       "KOREANEWS365COM",
    "https://theseouljournal.com":    "THESEOULJOURNALCOM",
}


def log(msg):
    print(msg, flush=True)


def main():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    by_site = defaultdict(list)
    for item in manifest:
        by_site[item["site"]].append(item)

    ok = fail = skip = 0
    for site, items in by_site.items():
        secret_name = SITE_SECRET_MAP.get(site)
        pw = os.environ.get(secret_name) if secret_name else None
        if not pw:
            log(f"[{site}] ⚠️ 시크릿 없음 → {len(items)}건 건너뜀")
            skip += len(items)
            continue

        auth = requests.auth.HTTPBasicAuth(WP_USER, pw)
        for item in items:
            post_id = item["post_id"]
            try:
                r = requests.delete(
                    f"{site}/wp-json/wp/v2/posts/{post_id}",
                    auth=auth, params={"force": "false"}, timeout=20,
                )
            except Exception as e:
                log(f"[{site}#{post_id}] ⚠️ 삭제 오류: {e}")
                fail += 1
                continue
            if r.status_code in (200, 410):
                log(f"[{site}#{post_id}] ✅ 휴지통 이동 완료 (SEO {item['seo_score']}점, {item['title'][:40]})")
                ok += 1
            else:
                log(f"[{site}#{post_id}] ⚠️ 삭제 실패 HTTP {r.status_code}: {r.text[:150]}")
                fail += 1

    log("=" * 60)
    log(f"완료: 성공(휴지통이동) {ok} / 실패 {fail} / 건너뜀(시크릿없음) {skip} (전체 대상 {len(manifest)}건)")


if __name__ == "__main__":
    main()
