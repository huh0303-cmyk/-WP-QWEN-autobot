#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""27개 사이트에 설치된 플러그인 확인 - GA4 코드 삽입 방법 결정용"""
import os
import requests

WP_USER = "huh0303@gmail.com"

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

CODE_INJECTION_KEYWORDS = ["wpcode", "insert-headers-and-footers", "header-footer",
                            "code-snippets", "insert-headers", "site-kit"]


def main():
    lines = []
    def log(m):
        print(m); lines.append(m)

    for site in SITES:
        url = site["url"]
        wp_pass = os.getenv(site["wp_pass_env"], "")
        if not wp_pass:
            log(f"🌐 {url} → 비밀번호 없음")
            continue
        try:
            r = requests.get(f"{url}/wp-json/wp/v2/plugins",
                             auth=(WP_USER, wp_pass),
                             params={"status": "active"}, timeout=15)
            if r.status_code != 200:
                log(f"🌐 {url} → 플러그인 조회 실패 (HTTP {r.status_code}: {r.text[:100]})")
                continue
            plugins = r.json()
            names = [p.get("plugin", p.get("name", "")) for p in plugins]
            matches = [n for n in names if any(k in n.lower() for k in CODE_INJECTION_KEYWORDS)]
            log(f"🌐 {url} → 코드삽입 관련: {matches if matches else '없음'} | 전체 {len(names)}개 플러그인")
        except Exception as e:
            log(f"🌐 {url} → 오류: {e}")

    with open("check_plugins_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
