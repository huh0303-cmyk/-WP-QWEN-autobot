#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_title_years.py
27개 사이트 전체 게시물 제목에서 2026이 아닌 연도(2024,2025,2027 등)를 찾아
안전하게 제거합니다. ("확실하지 않으면 연도 자체를 빼는 것이 원칙" 규칙 적용)

DRY_RUN=True: 변경 예정 목록만 출력
DRY_RUN=False: 실제 제목 업데이트 실행
"""
import os, re, requests

DRY_RUN = False

WP_USER = "huh0303@gmail.com"
YEAR_PATTERN = re.compile(r'(?<!\d)(19\d{2}|20\d{2})(?!\d)')
KEEP_YEAR = "2026"

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


def clean_title(title):
    def repl(m):
        return "" if m.group(1) != KEEP_YEAR else m.group(1)
    new_title = YEAR_PATTERN.sub(repl, title)
    # 정리: 남은 빈 괄호/대괄호, 중복 공백/기호 제거
    new_title = re.sub(r'[\[\(]\s*[\]\)]', '', new_title)
    new_title = re.sub(r'\s{2,}', ' ', new_title)
    new_title = re.sub(r'^[\s\-–\|:,]+|[\s\-–\|:,]+$', '', new_title)
    return new_title.strip()


def fetch_all_posts(site_url, pw):
    posts = []
    page = 1
    while True:
        try:
            r = requests.get(f"{site_url}/wp-json/wp/v2/posts",
                              auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                              params={"per_page": 50, "page": page, "status": "publish",
                                      "_fields": "id,title,link"},
                              timeout=20)
        except Exception as e:
            log(f"    ⚠️ 연결 오류: {e}")
            break
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 50:
            break
        page += 1
    return posts


def main():
    log(f"모드: {'DRY RUN' if DRY_RUN else '실제 수정'}")
    total_fixed = 0
    for site_url, secret_name in SITES:
        pw = os.environ.get(secret_name)
        if not pw:
            continue
        posts = fetch_all_posts(site_url, pw)
        site_fixed = 0
        for p in posts:
            title = p.get("title", {}).get("rendered", "")
            new_title = clean_title(title)
            if new_title and new_title != title:
                log(f"[{site_url}] #{p['id']}: '{title}' -> '{new_title}'")
                if not DRY_RUN:
                    up = requests.post(f"{site_url}/wp-json/wp/v2/posts/{p['id']}",
                                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                                        json={"title": new_title}, timeout=20)
                    if up.status_code in (200, 201):
                        site_fixed += 1
                    else:
                        log(f"   ⚠️ 업데이트 실패 status={up.status_code}")
                else:
                    site_fixed += 1
        if site_fixed:
            log(f"🌐 {site_url}: {site_fixed}건 제목 연도 수정")
        total_fixed += site_fixed
    log(f"\n총 {total_fixed}건 제목 수정 {'예정' if DRY_RUN else '완료'}")
    with open("fix_title_years_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(_LOG))


if __name__ == "__main__":
    main()
