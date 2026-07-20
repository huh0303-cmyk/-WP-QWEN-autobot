#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_playwright_redirect.py
실제 브라우저(headless Chromium)로 koreacrypto365.com 1곳에서만
404 모니터 -> Redirect 링크 클릭 -> 목적지 홈으로 저장 흐름이 실제로
동작하는지 검증. 성공하면 이 로직을 26개 사이트 전체로 확장.
"""
import os, json, sys, time
from playwright.sync_api import sync_playwright

WP_USER = "huh0303@gmail.com"
WP_PASS = os.getenv("WP_REAL_PASSWORD", "")
SITE = "https://koreacrypto365.com"

result = {"steps": []}

def log(msg):
    print(msg)
    result["steps"].append(msg)
    sys.stdout.flush()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # 1) 로그인
    page.goto(f"{SITE}/wp-login.php", timeout=30000)
    page.fill("#user_login", WP_USER)
    page.fill("#user_pass", WP_PASS)
    page.click("#wp-submit")
    page.wait_for_load_state("networkidle", timeout=30000)
    log(f"로그인 후 URL: {page.url}")

    if "wp-admin" not in page.url:
        log("❌ 로그인 실패")
        page.screenshot(path="login_fail.png")
        browser.close()
        with open("verify_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        sys.exit(1)

    # 2) 404 모니터 페이지
    page.goto(f"{SITE}/wp-admin/admin.php?page=rank-math-404-monitor", timeout=30000)
    page.wait_for_load_state("networkidle", timeout=30000)
    rows = page.query_selector_all("table.wp-list-table tbody tr")
    log(f"404 로그 행 수: {len(rows)}")

    if not rows:
        log("행 없음, 종료")
        browser.close()
        with open("verify_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        sys.exit(0)

    # 첫 번째 행에서 "Redirect" 링크 텍스트 찾기 (hover 시 나타나는 row-actions)
    first_row = rows[0]
    row_text = first_row.inner_text()
    log(f"첫 행 내용 미리보기: {row_text[:120]}")

    redirect_link = first_row.query_selector("a:has-text('Redirect')")
    if not redirect_link:
        log("❌ Redirect 링크를 찾을 수 없음")
        page.screenshot(path="no_redirect_link.png")
        browser.close()
        with open("verify_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        sys.exit(1)

    href = redirect_link.get_attribute("href")
    log(f"Redirect 링크 href: {href}")

    redirect_link.click()
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(2000)  # React 렌더링 대기
    log(f"클릭 후 URL: {page.url}")
    page.screenshot(path="after_redirect_click.png", full_page=True)

    # 3) 폼 필드 탐색 (Destination URL 입력창 찾기)
    # Rank Math의 Add New Redirection 폼은 보통 placeholder나 label로 식별 가능
    html_snapshot = page.content()
    with open("redirect_form_snapshot.html", "w", encoding="utf-8") as f:
        f.write(html_snapshot)
    log(f"폼 페이지 HTML 저장 완료 ({len(html_snapshot)} bytes)")

    browser.close()

with open("verify_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

log("검증 완료 (아직 저장은 안 함 - 폼 구조 확인 단계)")
