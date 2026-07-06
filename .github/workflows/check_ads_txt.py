#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""27개 사이트 ads.txt 파일 상태를 점검하고 문제 원인을 진단합니다."""
import requests

PUBLISHER_ID = "pub-3456727916386941"

SITES = [
    "k-health365.com","koreamedicaltour.com","koreainvest365.com","ki-korea.com",
    "koreainsurance365.com","kfinance365.com","koreataxnlaw.com","koreacrypto365.com",
    "krealestate365.com","ktech365.com","kskin365.com","oliveyoungkorea.com",
    "kworld365.com","k-trip365.com","k-visa365.com","koreawedding365.com",
    "kstudy365.com","studyinkorea365.com","kieca-korea.org","ksa-korea.org",
    "sis-korea.com","jobkorea365.com","jobinkorea365.com","jobkoreaglobal.com",
    "korea365.org","koreanews365.com","theseouljournal.com",
]

_LOG = []
def log(m=""):
    print(m)
    _LOG.append(str(m))

for domain in SITES:
    url = f"https://{domain}/ads.txt"
    try:
        r = requests.get(url, timeout=15, allow_redirects=True)
        status = r.status_code
        ctype = r.headers.get("Content-Type", "")
        body = r.text.strip()
        has_pub = PUBLISHER_ID in body
        first_line = body.splitlines()[0] if body else "(빈 파일)"
        final_url = r.url
        redirected = " [리다이렉트됨→" + final_url + "]" if final_url != url else ""
        log(f"{domain:28s} status={status} ctype={ctype[:30]:30s} pub_id_있음={has_pub} 첫줄='{first_line[:60]}'{redirected}")
    except Exception as e:
        log(f"{domain:28s} ⚠️ 접속실패: {type(e).__name__}: {str(e)[:100]}")

with open("ads_txt_check_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(_LOG))
