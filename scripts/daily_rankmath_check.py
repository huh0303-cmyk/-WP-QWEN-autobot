#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
매일 실행: 27개 사이트 Rank Math 종합 점검
1) 포커스키워드 누락 자동 백필 (글+페이지)
2) SEO Analyzer 점수 스냅샷
3) 404 모니터 로그 건수 확인 (너무 많으면 자동 정리 — 로그는 정보성이라 안전)
4) 리디렉션 건수 확인 (많으면 검토 필요 플래그만, 삭제는 안 함 — 링크 깨짐 위험)
5) 사이트 헬스 상태 확인
"""
import asyncio
import html as _html
import re
import requests
from playwright.async_api import async_playwright

WP_USER = "huh0303@gmail.com"
WP_PASS = "Huh522676!"

SITES = [
    "https://k-health365.com", "https://koreamedicaltour.com", "https://koreainvest365.com",
    "https://ki-korea.com", "https://koreainsurance365.com", "https://kfinance365.com",
    "https://koreataxnlaw.com", "https://koreacrypto365.com", "https://krealestate365.com",
    "https://ktech365.com", "https://kskin365.com", "https://oliveyoungkorea.com",
    "https://kworld365.com", "https://k-trip365.com", "https://k-visa365.com",
    "https://koreawedding365.com", "https://kstudy365.com", "https://studyinkorea365.com",
    "https://kieca-korea.org", "https://ksa-korea.org", "https://sis-korea.com",
    "https://jobkorea365.com", "https://jobinkorea365.com", "https://jobkoreaglobal.com",
    "https://korea365.org", "https://koreanews365.com", "https://theseouljournal.com",
]

REDIRECT_WARN_THRESHOLD = 150
NOTFOUND_AUTOCLEAR_THRESHOLD = 50

TEMPLATE_STRIP_PREFIX = re.compile(
    r'^(Before You Try|Is |Study Reveals:?\s*\d*\s*(in|of)?\s*\d*\s*People\s*(Misunderstand)?|'
    r'How to Actually Handle|A Practical Look at|The Real Cost of|The Truth About|Rethinking |'
    r'Behind the Scenes:\s*What |Why Does |\d+\s*(Things|Mistakes)\s*(About|People Make With)\s*|'
    r'What Nobody Tells You About)\s*', re.IGNORECASE)
TEMPLATE_STRIP_SUFFIX = re.compile(
    r'(:\s*A (Specialist.?s|Closer)\s*(Guide|Look).*|,\s*Read This First.*|'
    r'\s*Really Worth It\?.*|Explained in Plain English.*|:\s*What (Most People Get Wrong|to Expect|'
    r'First-Timers Should Know).*|Warning Signs.*|Has (Changed|Really Changed).*|'
    r'Q&A:.*|101:.*|Frequently Overlooked Facts.*|Complete Guide.*)$', re.IGNORECASE)


def strip_tags(s):
    return re.sub(r'<[^>]+>', '', s or '').strip()


def derive_keyword(title):
    t = _html.unescape(strip_tags(title))
    t2 = TEMPLATE_STRIP_PREFIX.sub('', t)
    t2 = TEMPLATE_STRIP_SUFFIX.sub('', t2).strip(" :,-")
    return (t2 if len(t2) >= 3 else t)[:60]


def backfill_keywords_rest(url, log):
    filled = 0
    for post_type in ["posts", "pages"]:
        page_num = 1
        while True:
            try:
                r = requests.get(f"{url}/wp-json/wp/v2/{post_type}", auth=(WP_USER, WP_PASS),
                                  params={"per_page": 100, "page": page_num, "status": "publish",
                                          "_fields": "id,title,meta"}, timeout=20)
            except Exception:
                break
            if r.status_code != 200:
                break
            batch = r.json()
            if not isinstance(batch, list) or not batch:
                break
            for p in batch:
                meta = p.get("meta", {}) or {}
                kw = meta.get("rank_math_focus_keyword", "")
                if kw and str(kw).strip():
                    continue
                new_kw = derive_keyword(p.get("title", {}).get("rendered", ""))
                try:
                    rr = requests.post(f"{url}/wp-json/wp/v2/{post_type}/{p['id']}", auth=(WP_USER, WP_PASS),
                                        json={"meta": {"rank_math_focus_keyword": new_kw}}, timeout=15)
                    if rr.status_code in (200, 201):
                        filled += 1
                except Exception:
                    pass
            if len(batch) < 100:
                break
            page_num += 1
    return filled


async def check_site(browser, url, log):
    result = {"url": url, "kw_filled": 0, "score": None, "warnings": None, "failed": None,
              "notfound_count": None, "redirect_count": None, "site_health": None, "error": None}
    try:
        result["kw_filled"] = backfill_keywords_rest(url, log)
    except Exception as e:
        log(f"  ⚠️ 키워드 백필 오류: {str(e)[:100]}")

    page = await browser.new_page(ignore_https_errors=True)
    try:
        await page.goto(f"{url}/wp-login.php", timeout=30000)
        await page.fill("#user_login", WP_USER)
        await page.fill("#user_pass", WP_PASS)
        await page.click("#wp-submit")
        await page.wait_for_load_state("networkidle", timeout=30000)

        # 404 모니터 확인
        await page.goto(f"{url}/wp-admin/admin.php?page=rank-math-404-monitor",
                         wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        body = await page.locator("body").inner_text()
        m = re.search(r'All \((\d+)\)', body) or re.search(r'Items \((\d+)\)', body) or re.search(r'\((\d+)\)\s*\n?\s*items', body, re.IGNORECASE)
        if m:
            result["notfound_count"] = int(m.group(1))
            if result["notfound_count"] >= NOTFOUND_AUTOCLEAR_THRESHOLD:
                clear_btn = page.locator("button", has_text=re.compile("Clear log|로그 지우기|Clear Log"))
                if await clear_btn.count() > 0:
                    await clear_btn.first.click()
                    await page.wait_for_timeout(1500)
                    confirm = page.locator("button", has_text=re.compile("OK|확인|Yes"))
                    if await confirm.count() > 0:
                        await confirm.first.click()
                        await page.wait_for_timeout(1500)
                    log(f"  🗑️ 404 로그 {result['notfound_count']}건 자동 정리")

        # 리디렉션 개수 확인
        await page.goto(f"{url}/wp-admin/admin.php?page=rank-math-redirections",
                         wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        body2 = await page.locator("body").inner_text()
        m2 = re.search(r'All \((\d+)\)', body2)
        if m2:
            result["redirect_count"] = int(m2.group(1))

        # SEO Analyzer 점수
        await page.goto(f"{url}/wp-admin/admin.php?page=rank-math-seo-analysis",
                         wait_until="domcontentloaded", timeout=30000)
        for _ in range(20):
            await page.wait_for_timeout(2000)
            body3 = await page.locator("body").inner_text()
            if "SEO SCORE" in body3 or "SEO 점수" in body3:
                break
        idx = body3.find("SEO SCORE")
        if idx < 0:
            idx = body3.find("SEO 점수")
        if idx > 0:
            m3 = re.search(r'(\d{1,3})/100', body3[max(0, idx - 20):idx])
            if m3:
                result["score"] = int(m3.group(1))

        # 사이트 헬스
        await page.goto(f"{url}/wp-admin/site-health.php", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        body4 = await page.locator("body").inner_text()
        if "양호" in body4 or "Good" in body4:
            result["site_health"] = "양호"
        elif "심각" in body4 or "Critical" in body4:
            result["site_health"] = "⚠️심각"

        flag = f" ⚠️리디렉션{result['redirect_count']}건 검토필요" if (result["redirect_count"] or 0) >= REDIRECT_WARN_THRESHOLD else ""
        log(f"✅ {url} | 점수:{result['score']} | 키워드백필:{result['kw_filled']} | "
            f"404:{result['notfound_count']} | 리디렉션:{result['redirect_count']} | "
            f"헬스:{result['site_health']}{flag}")
    except Exception as e:
        result["error"] = str(e)[:200]
        log(f"⚠️ {url} 오류: {result['error']}")
    finally:
        await page.close()
    return result


async def main():
    lines = []

    def log(m):
        print(m)
        lines.append(m)

    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for url in SITES:
            r = await check_site(browser, url, log)
            results.append(r)
        await browser.close()

    review_needed = [r for r in results if (r.get("redirect_count") or 0) >= REDIRECT_WARN_THRESHOLD]
    if review_needed:
        log("\n### 리디렉션 검토 필요 사이트")
        for r in review_needed:
            log(f"- {r['url']}: {r['redirect_count']}건")

    with open("daily_rankmath_report.md", "w", encoding="utf-8") as f:
        f.write("# 일일 Rank Math 점검 리포트\n\n```\n" + "\n".join(lines) + "\n```\n")


if __name__ == "__main__":
    asyncio.run(main())
