#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
발행 크론(06:10/14:10/22:10 KST) 직후 실행되어, 최근 N시간 내 발행된 글만 골라
wp-admin 편집화면을 실제로 열어 Rank Math SEO점수를 계산·저장시킨다.
전체 백필이 아니라 '방금 발행된 글'만 대상으로 하므로 매 실행이 짧게 끝난다.
"""
import os
import sys
import asyncio
import datetime
import requests
from playwright.async_api import async_playwright

WP_USER = "huh0303@gmail.com"
WP_PASS = os.getenv("WP_ADMIN_PASSWORD", "")
LOOKBACK_HOURS = int(os.getenv("SEO_SCORE_LOOKBACK_HOURS", "6"))

SITES = [
    ("https://k-health365.com", "KHEALTH365COM"),
    ("https://koreamedicaltour.com", "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com", "KOREAINVEST365COM"),
    ("https://ki-korea.com", "KIKOREACOM"),
    ("https://koreainsurance365.com", "KOREAINSURANCE365COM"),
    ("https://kfinance365.com", "KFINANCE365COM"),
    ("https://koreataxnlaw.com", "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com", "KOREACRYPTO365COM"),
    ("https://krealestate365.com", "KREALESTATE365COM"),
    ("https://ktech365.com", "KTECH365COM"),
    ("https://kskin365.com", "KSKIN365COM"),
    ("https://oliveyoungkorea.com", "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com", "KWORLD365COM"),
    ("https://k-trip365.com", "KTRIP365COM"),
    ("https://k-visa365.com", "KVISA365COM"),
    ("https://koreawedding365.com", "KOREAWEDDING365COM"),
    ("https://kstudy365.com", "KSTUDY365COM"),
    ("https://studyinkorea365.com", "STUDYINKOREA365COM"),
    ("https://kieca-korea.org", "KIECAKOREAORG"),
    ("https://ksa-korea.org", "KSAKOREAORG"),
    ("https://sis-korea.com", "SISKOREACOM"),
    ("https://jobkorea365.com", "JOBKOREA365COM"),
    ("https://jobinkorea365.com", "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com", "JOBKOREAGLOBALCOM"),
    ("https://korea365.org", "KOREA365ORG"),
    ("https://koreanews365.com", "KOREANEWS365COM"),
    ("https://theseouljournal.com", "THESEOULJOURNALCOM"),
]


def get_recent_post_ids(site_url, wp_pass, log):
    since = (datetime.datetime.utcnow() - datetime.timedelta(hours=LOOKBACK_HOURS)).isoformat()
    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, wp_pass),
                          params={"per_page": 50, "status": "publish", "after": since,
                                  "_fields": "id,title"}, timeout=20)
        if r.status_code == 200 and isinstance(r.json(), list):
            return [(p["id"], p["title"]["rendered"]) for p in r.json()]
    except Exception as e:
        log(f"  ⚠️ 최근글 조회 실패: {e}")
    return []


async def process_post(page, site_url, post_id, title, log):
    edit_url = f"{site_url}/wp-admin/post.php?post={post_id}&action=edit"
    try:
        await page.goto(edit_url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(4500)
        canvas = None
        for f in page.frames:
            if f.url.startswith("blob:"):
                canvas = f
                break
        if canvas is None:
            log(f"    ⚠️ [{post_id}] canvas 못찾음")
            return False
        title_el = canvas.locator(".editor-post-title__input")
        if await title_el.count() == 0:
            log(f"    ⚠️ [{post_id}] 제목필드 못찾음")
            return False
        await title_el.click(timeout=10000)
        await page.keyboard.press("End")
        await page.keyboard.type(" ")
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(2200)
        save_btn = page.locator("button.editor-post-publish-button__button")
        if await save_btn.count() == 0:
            log(f"    ⚠️ [{post_id}] 저장버튼 못찾음")
            return False
        await save_btn.first.click(timeout=10000)
        await page.wait_for_timeout(3000)
        log(f"    ✅ [{post_id}] {title[:40]}")
        return True
    except Exception as e:
        log(f"    ⚠️ [{post_id}] 오류: {str(e)[:100]}")
        return False


async def process_site(browser, site_url, wp_pass, log):
    posts = get_recent_post_ids(site_url, wp_pass, log)
    if not posts:
        log(f"  (최근 {LOOKBACK_HOURS}시간 내 신규 발행 없음)")
        return 0
    page = await browser.new_page(ignore_https_errors=True)
    try:
        await page.goto(f"{site_url}/wp-login.php", timeout=30000)
        await page.fill("#user_login", WP_USER)
        await page.fill("#user_pass", WP_PASS)
        await page.click("#wp-submit")
        await page.wait_for_load_state("networkidle", timeout=30000)
    except Exception as e:
        log(f"  ⚠️ 로그인 실패: {e}")
        await page.close()
        return 0

    ok = 0
    for pid, title in posts:
        if await process_post(page, site_url, pid, title, log):
            ok += 1
    await page.close()
    return ok


async def main():
    lines = []

    def log(m):
        print(m)
        lines.append(m)

    if not WP_PASS:
        log("❌ WP_ADMIN_PASSWORD 시크릿 없음 — 중단")
        with open("seo_score_trigger_result.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        sys.exit(1)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        total_ok = 0
        for site_url, env_key in SITES:
            wp_pass_site = os.getenv(env_key, "")  # 사이트별 App Password (REST 조회용)
            log(f"\n🌐 {site_url}")
            if not wp_pass_site:
                log("  ⚠️ App Password 없음 — 스킵")
                continue
            ok = await process_site(browser, site_url, wp_pass_site, log)
            total_ok += ok
        await browser.close()
        log(f"\n총 {total_ok}건 SEO점수 갱신")

    with open("seo_score_trigger_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    asyncio.run(main())
