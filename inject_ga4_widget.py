#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inject_ga4_widget.py
─────────────────────────────────────────────────────────────
플러그인 설정 화면은 REST API로 직접 못 건드리기 때문에,
워드프레스 코어가 기본 제공하는 "커스텀 HTML 위젯" REST 엔드포인트를
이용해 GA4 추적 코드를 각 사이트의 푸터(또는 사용 가능한 위젯 영역)에
자동 삽입합니다.

먼저 --check 모드로 각 사이트의 사용 가능한 위젯 영역(sidebar)을
확인하고, 실제 삽입은 그 다음 단계에서 진행합니다.
"""

import os, sys
import requests

WP_USER = "huh0303@gmail.com"
GA4_MEASUREMENT_ID = os.getenv("GA4_MEASUREMENT_ID", "")

SITES = [
    {"url": "https://k-health365.com",        "wp_pass_env": "KHEALTH365COM"},
    {"url": "https://koreamedicaltour.com",   "wp_pass_env": "KOREAMEDICALTOURCOM"},
    {"url": "https://koreainvest365.com",     "wp_pass_env": "KOREAINVEST365COM"},
    {"url": "https://ki-korea.com",           "wp_pass_env": "KIKOREACOM"},
    {"url": "https://koreainsurance365.com",  "wp_pass_env": "KOREAINSURANCE365COM"},
    {"url": "https://kfinance365.com",        "wp_pass_env": "KFINANCE365COM"},
    {"url": "https://koreataxnlaw.com",       "wp_pass_env": "KOREATAXNLAWCOM"},
    {"url": "https://koreacrypto365.com",     "wp_pass_env": "KOREACRYPTO365COM"},
    {"url": "https://krealestate365.com",     "wp_pass_env": "KREALESTATE365COM"},
    {"url": "https://ktech365.com",           "wp_pass_env": "KTECH365COM"},
    {"url": "https://kskin365.com",           "wp_pass_env": "KSKIN365COM"},
    {"url": "https://oliveyoungkorea.com",    "wp_pass_env": "OLIVEYOUNGKOREACOM"},
    {"url": "https://kworld365.com",          "wp_pass_env": "KWORLD365COM"},
    {"url": "https://k-trip365.com",          "wp_pass_env": "KTRIP365COM"},
    {"url": "https://k-visa365.com",          "wp_pass_env": "KVISA365COM"},
    {"url": "https://koreawedding365.com",    "wp_pass_env": "KOREAWEDDING365COM"},
    {"url": "https://kstudy365.com",          "wp_pass_env": "KSTUDY365COM"},
    {"url": "https://studyinkorea365.com",    "wp_pass_env": "STUDYINKOREA365COM"},
    {"url": "https://kieca-korea.org",        "wp_pass_env": "KIECAKOREAORG"},
    {"url": "https://ksa-korea.org",          "wp_pass_env": "KSAKOREAORG"},
    {"url": "https://sis-korea.com",          "wp_pass_env": "SISKOREACOM"},
    {"url": "https://jobkorea365.com",        "wp_pass_env": "JOBKOREA365COM"},
    {"url": "https://jobinkorea365.com",      "wp_pass_env": "JOBINKOREA365COM"},
    {"url": "https://jobkoreaglobal.com",     "wp_pass_env": "JOBKOREAGLOBALCOM"},
    {"url": "https://korea365.org",           "wp_pass_env": "KOREA365ORG"},
    {"url": "https://koreanews365.com",       "wp_pass_env": "KOREANEWS365COM"},
    {"url": "https://theseouljournal.com",    "wp_pass_env": "THESEOULJOURNALCOM"},
]


def check_sidebars(site_url, wp_pass):
    r = requests.get(f"{site_url}/wp-json/wp/v2/sidebars",
                     auth=(WP_USER, wp_pass), timeout=15)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:150]}"
    sidebars = r.json()
    return sidebars, None


def main():
    lines = []
    def log(m):
        print(m); lines.append(m)

    log("=" * 60)
    log("🔍 27개 사이트 위젯 영역(sidebar) 확인")
    log("=" * 60)

    for site in SITES:
        url = site["url"]
        wp_pass = os.getenv(site["wp_pass_env"], "")
        if not wp_pass:
            log(f"🌐 {url} → 비밀번호 없음")
            continue
        sidebars, err = check_sidebars(url, wp_pass)
        if err:
            log(f"🌐 {url} → 오류: {err}")
            continue
        names = [f"{s.get('id')}({len(s.get('widgets',[]))}개위젯)" for s in sidebars]
        log(f"🌐 {url} → 위젯영역 {len(sidebars)}개: {names}")

    with open("check_sidebars_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
