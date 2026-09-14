#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""27개 사이트의 현재 활성 테마(디자인 테마)와 기본 사이트 상태를 점검합니다."""
import os, requests

WP_USER = "huh0303@gmail.com"

SITES = [
    ("https://k-health365.com",        "KHEALTH365COM"),
    ("https://koreamedicaltour.com",   "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com",     "KOREAINVEST365COM"),
    ("https://ki-korea.com",           "KIKOREACOM"),
    ("https://koreainsurance365.com",  "KOREAINSURANCE365COM"),
    ("https://kfinance365.com",        "KFINANCE365COM"),
    ("https://koreataxnlaw.com",       "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com",     "KOREACRYPTO365COM"),
    ("https://krealestate365.com",     "KREALESTATE365COM"),
    ("https://ktech365.com",           "KTECH365COM"),
    ("https://kskin365.com",           "KSKIN365COM"),
    ("https://oliveyoungkorea.com",    "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com",          "KWORLD365COM"),
    ("https://k-trip365.com",          "KTRIP365COM"),
    ("https://k-visa365.com",          "KVISA365COM"),
    ("https://koreawedding365.com",    "KOREAWEDDING365COM"),
    ("https://kstudy365.com",          "KSTUDY365COM"),
    ("https://studyinkorea365.com",    "STUDYINKOREA365COM"),
    ("https://kieca-korea.org",        "KIECAKOREAORG"),
    ("https://ksa-korea.org",          "KSAKOREAORG"),
    ("https://sis-korea.com",          "SISKOREACOM"),
    ("https://jobkorea365.com",        "JOBKOREA365COM"),
    ("https://jobinkorea365.com",      "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com",     "JOBKOREAGLOBALCOM"),
    ("https://korea365.org",           "KOREA365ORG"),
    ("https://koreanews365.com",       "KOREANEWS365COM"),
    ("https://theseouljournal.com",    "THESEOULJOURNALCOM"),
]

_LOG = []
def log(m=""):
    print(m)
    _LOG.append(str(m))

for site_url, secret in SITES:
    pw = os.environ.get(secret)
    log(f"\n🌐 {site_url}")
    if not pw:
        log("   ⚠️ 시크릿 없음 → 건너뜀")
        continue
    auth = requests.auth.HTTPBasicAuth(WP_USER, pw)

    # 1) 활성 테마
    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/themes", auth=auth,
                          params={"status": "active"}, timeout=20)
        if r.status_code == 200 and r.json():
            t = r.json()[0]
            name = t.get("name", {}).get("rendered", t.get("stylesheet", "?"))
            version = t.get("version", "?")
            log(f"   활성 테마: {name} (v{version}, stylesheet={t.get('stylesheet')})")
        elif r.status_code == 401 or r.status_code == 403:
            log(f"   ⚠️ 테마 조회 권한 없음 (status={r.status_code}) — REST API 계정에 edit_theme_options 권한 필요")
        else:
            log(f"   ⚠️ 테마 조회 실패 (status={r.status_code})")
    except Exception as e:
        log(f"   ⚠️ 테마 조회 오류: {e}")

    # 2) 홈페이지 응답 상태 및 응답시간
    try:
        r2 = requests.get(site_url, timeout=20)
        log(f"   홈페이지 응답: status={r2.status_code}, 응답시간={r2.elapsed.total_seconds():.2f}초, "
            f"크기={len(r2.content)//1024}KB")
        # 아주 단순한 이상징후 체크
        body_lower = r2.text.lower()
        if "fatal error" in body_lower or "parse error" in body_lower:
            log("   🚨 PHP 오류 문자열이 홈페이지에 노출되어 있습니다!")
        if "<body" not in body_lower:
            log("   🚨 정상적인 HTML body가 감지되지 않습니다 (테마 렌더링 실패 의심)")
    except Exception as e:
        log(f"   ⚠️ 홈페이지 접속 오류: {e}")

with open("theme_check_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(_LOG))
