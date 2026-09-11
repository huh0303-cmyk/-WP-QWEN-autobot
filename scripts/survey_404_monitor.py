#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
survey_404_monitor.py  (1단계: 전수조사 - 읽기 전용, 아무것도 삭제/변경하지 않음)

Rank Math의 404 모니터/리디렉션 화면은 REST API가 아니라 전통적인
wp-admin PHP 화면(WP_List_Table)이라서, 실제 로그인 세션(쿠키)으로
접속해서 화면을 읽어와야 함.

이 스크립트는:
1. 실제 계정(huh0303@gmail.com)으로 각 사이트에 로그인
2. Rank Math > 404 모니터 화면(admin.php?page=rank-math-404-monitor)을 읽어옴
3. 표 안의 URL / 히트수 / 각 행의 액션 링크(redirect/delete 등에 필요한 nonce 포함)를
   그대로 파싱해서 저장
4. 아무 것도 지우거나 리디렉션을 만들지 않음 (읽기 전용 조사만)

결과는 survey_404_result.json 에 사이트별로 저장되고, 이후 이 데이터를 보고
실제 정리(리디렉션 생성/로그 삭제) 스크립트를 정확하게 만들 예정.
"""
import os, re, json, sys
import requests
from bs4 import BeautifulSoup

WP_USER = "huh0303@gmail.com"
WP_PASS = os.getenv("WP_REAL_PASSWORD", "")

SITES = [
    ("https://koreamedicaltour.com",   "koreamedicaltour.com"),
    ("https://koreainvest365.com",     "koreainvest365.com"),
    ("https://ki-korea.com",           "ki-korea.com"),
    ("https://koreainsurance365.com",  "koreainsurance365.com"),
    ("https://kfinance365.com",        "kfinance365.com"),
    ("https://koreataxnlaw.com",       "koreataxnlaw.com"),
    ("https://koreacrypto365.com",     "koreacrypto365.com"),
    ("https://krealestate365.com",     "krealestate365.com"),
    ("https://ktech365.com",           "ktech365.com"),
    ("https://kskin365.com",           "kskin365.com"),
    ("https://oliveyoungkorea.com",    "oliveyoungkorea.com"),
    ("https://kworld365.com",          "kworld365.com"),
    ("https://k-trip365.com",          "k-trip365.com"),
    ("https://k-visa365.com",          "k-visa365.com"),
    ("https://koreawedding365.com",    "koreawedding365.com"),
    ("https://kstudy365.com",          "kstudy365.com"),
    ("https://studyinkorea365.com",    "studyinkorea365.com"),
    ("https://kieca-korea.org",        "kieca-korea.org"),
    ("https://ksa-korea.org",          "ksa-korea.org"),
    ("https://sis-korea.com",          "sis-korea.com"),
    ("https://jobkorea365.com",        "jobkorea365.com"),
    ("https://jobinkorea365.com",      "jobinkorea365.com"),
    ("https://jobkoreaglobal.com",     "jobkoreaglobal.com"),
    ("https://korea365.org",           "korea365.org"),
    ("https://koreanews365.com",       "koreanews365.com"),
    ("https://theseouljournal.com",    "theseouljournal.com"),
]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def login(site):
    s = requests.Session()
    s.headers.update(HEADERS)
    r = s.post(
        f"{site}/wp-login.php",
        data={
            "log": WP_USER,
            "pwd": WP_PASS,
            "wp-submit": "Log In",
            "redirect_to": f"{site}/wp-admin/",
            "testcookie": "1",
        },
        timeout=25,
        allow_redirects=True,
    )
    logged_in = any(c.startswith("wordpress_logged_in_") for c in s.cookies.keys())
    return s, logged_in, r.status_code, r.url


def parse_404_page(html):
    soup = BeautifulSoup(html, "html.parser")
    rows_out = []
    table = soup.find("table", class_=re.compile("wp-list-table"))
    if not table:
        return rows_out, False
    tbody = table.find("tbody")
    if not tbody:
        return rows_out, True
    for tr in tbody.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        row_text = [c.get_text(strip=True) for c in cells]
        # 행 액션 링크(redirect/delete 등) 전부 수집 - href에 nonce 포함되어 있음
        links = {}
        for a in tr.find_all("a", href=True):
            label = a.get_text(strip=True).lower()
            if label:
                links[label] = a["href"]
        if row_text:
            rows_out.append({"cells": row_text, "actions": links})
    return rows_out, True


def find_bulk_nonce(html):
    m = re.search(r'name="_wpnonce"\s+value="([^"]+)"', html)
    return m.group(1) if m else None


results = {}

if not WP_PASS:
    print("NO WP_REAL_PASSWORD secret set"); sys.exit(1)

for site, key in SITES:
    entry = {"site": site}
    try:
        s, logged_in, status, final_url = login(site)
        entry["login_ok"] = logged_in
        entry["login_status"] = status
        entry["login_final_url"] = final_url

        if not logged_in:
            results[key] = entry
            print(f"{key}: ❌ 로그인 실패 (status={status}, url={final_url})")
            sys.stdout.flush()
            continue

        r2 = s.get(f"{site}/wp-admin/admin.php?page=rank-math-404-monitor", timeout=25)
        entry["page_status"] = r2.status_code
        if r2.status_code == 200:
            rows, table_found = parse_404_page(r2.text)
            entry["table_found"] = table_found
            entry["row_count"] = len(rows)
            entry["rows_sample"] = rows[:30]  # 안전하게 최대 30개만 저장 (용량)
            entry["bulk_nonce"] = find_bulk_nonce(r2.text)
        else:
            entry["error"] = f"404모니터 페이지 접근 실패: {r2.status_code}"

        results[key] = entry
        print(f"{key}: ✅ 로그인성공 / 행={entry.get('row_count')}")
        sys.stdout.flush()

    except Exception as e:
        entry["error"] = str(e)
        results[key] = entry
        print(f"{key}: ⚠️ 예외: {e}")
        sys.stdout.flush()

with open("survey_404_result.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n전수조사 완료 (읽기 전용)")
