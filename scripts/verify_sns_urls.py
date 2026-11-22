import json, sys, re
from playwright.sync_api import sync_playwright
lock = json.load(open("config/SNS_SIX_BRAND_IDENTITY_LOCK_2026-11-21.json", encoding="utf-8"))
rows = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(locale="ko-KR", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36")
    for br in lock["brands"]:
        for plat, url in (("instagram", "https://www.instagram.com/%s/"), ("threads", "https://www.threads.com/@%s")):
            h = br[plat]["handle"]
            pg = ctx.new_page()
            try:
                r = pg.goto(url % h, wait_until="domcontentloaded", timeout=25000)
                pg.wait_for_timeout(2500)
                og = pg.eval_on_selector('meta[property="og:title"]', "e=>e.content") if pg.query_selector('meta[property="og:title"]') else ""
                rows.append((br["key"], plat, h, r.status if r else None, pg.url, (og or pg.title())[:80]))
            except Exception as e:
                rows.append((br["key"], plat, h, "ERR", "", str(e)[:80]))
            pg.close()
    b.close()
for r in rows: print(" | ".join(map(str, r)))
