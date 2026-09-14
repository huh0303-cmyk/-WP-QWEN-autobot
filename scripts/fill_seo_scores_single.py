import asyncio
import os
import requests
from playwright.async_api import async_playwright

WP_USER = "huh0303@gmail.com"
WP_PASS = os.environ["WP_ADMIN_PASSWORD"]
SITE_URL = os.environ["SITE_URL"].rstrip("/")


def get_all_post_ids():
    ids = []
    page = 1
    while True:
        r = requests.get(f"{SITE_URL}/wp-json/wp/v2/posts",
                          auth=(WP_USER, WP_PASS),
                          params={"per_page": 100, "page": page, "status": "publish",
                                  "_fields": "id,title"}, timeout=30)
        if r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        ids.extend([(p["id"], p["title"]["rendered"]) for p in batch])
        if len(batch) < 100:
            break
        page += 1
    return ids


async def process_post(page, post_id, title, log):
    edit_url = f"{SITE_URL}/wp-admin/post.php?post={post_id}&action=edit"
    try:
        await page.goto(edit_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)

        canvas = None
        for f in page.frames:
            if f.url.startswith("blob:"):
                canvas = f
                break
        if canvas is None:
            log(f"  ⚠️ [{post_id}] iframe 못찾음 — 스킵: {title[:40]}")
            return False

        title_el = canvas.locator(".editor-post-title__input")
        if await title_el.count() == 0:
            log(f"  ⚠️ [{post_id}] 제목필드 못찾음 — 스킵: {title[:40]}")
            return False

        await title_el.click(timeout=15000)
        await page.keyboard.press("End")
        await page.keyboard.type(" ")
        await page.keyboard.press("Backspace")
        await page.wait_for_timeout(2000)

        save_btn = page.locator("button.editor-post-publish-button__button")
        if await save_btn.count() == 0:
            log(f"  ⚠️ [{post_id}] 저장버튼 못찾음 — 스킵: {title[:40]}")
            return False
        await save_btn.first.click(timeout=15000)
        await page.wait_for_timeout(3000)
        log(f"  ✅ [{post_id}] 저장완료: {title[:40]}")
        return True
    except Exception as e:
        log(f"  ⚠️ [{post_id}] 오류: {str(e)[:100]} — {title[:40]}")
        return False


async def main():
    lines = []

    def log(m):
        print(m, flush=True)
        lines.append(m)

    posts = get_all_post_ids()
    log(f"{SITE_URL} — 총 {len(posts)}건 처리 시작")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(ignore_https_errors=True)
        await page.goto(f"{SITE_URL}/wp-login.php", timeout=30000)
        await page.fill("#user_login", WP_USER)
        await page.fill("#user_pass", WP_PASS)
        await page.click("#wp-submit")
        await page.wait_for_load_state("networkidle", timeout=30000)
        log(f"로그인 완료: {page.url}")

        ok = 0
        for idx, (pid, title) in enumerate(posts, 1):
            success = await process_post(page, pid, title, log)
            if success:
                ok += 1
            if idx % 10 == 0:
                log(f"  진행: {idx}/{len(posts)}")

        log(f"\n완료: {ok}/{len(posts)} 성공")
        await browser.close()

    safe_name = SITE_URL.replace("https://", "").replace("/", "_")
    with open(f"seo_fill_{safe_name}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


asyncio.run(main())
