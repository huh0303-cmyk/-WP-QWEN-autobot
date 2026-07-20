import asyncio
from playwright.async_api import async_playwright

NAVER_ID = "westlake.ceo@gmail.com"
NAVER_PW = "Huh556423$"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        resp = await page.goto("https://sell.smartstore.naver.com/", timeout=30000, wait_until="domcontentloaded")
        print("초기 status:", resp.status if resp else None)
        print("초기 url:", page.url)
        await page.wait_for_timeout(2000)
        await page.screenshot(path="step1_initial.png", full_page=True)

        # 로그인 버튼/링크 찾기
        login_btn = page.locator("a", has_text="로그인")
        cnt = await login_btn.count()
        print("로그인 버튼 개수:", cnt)
        if cnt > 0:
            await login_btn.first.click()
            await page.wait_for_timeout(3000)
        print("로그인 페이지 url:", page.url)
        await page.screenshot(path="step2_loginpage.png", full_page=True)

        # 아이디/비번 입력
        id_input = page.locator("#id")
        pw_input = page.locator("#pw")
        if await id_input.count() > 0:
            await id_input.click()
            await page.keyboard.type(NAVER_ID, delay=50)
            await pw_input.click()
            await page.keyboard.type(NAVER_PW, delay=50)
            await page.wait_for_timeout(1000)
            login_submit = page.locator("#log\\.login")
            if await login_submit.count() > 0:
                await login_submit.click()
            await page.wait_for_timeout(4000)

        print("로그인 시도 후 url:", page.url)
        body = await page.locator("body").inner_text()
        print("본문 일부:", body[:500])
        await page.screenshot(path="step3_after_login.png", full_page=True)

        await browser.close()


asyncio.run(main())
