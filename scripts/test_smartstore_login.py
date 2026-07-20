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

        # "이메일/판매자 아이디로 로그인" 탭 클릭
        email_tab = page.locator("text=이메일/판매자 아이디로 로그인")
        if await email_tab.count() > 0:
            await email_tab.first.click()
            await page.wait_for_timeout(1500)
        await page.screenshot(path="step2b_email_tab.png", full_page=True)

        # 필드 덤프
        all_inputs = await page.locator("input").all()
        for i in all_inputs:
            iid = await i.get_attribute("id")
            name = await i.get_attribute("name")
            typ = await i.get_attribute("type")
            ph = await i.get_attribute("placeholder")
            print("필드:", iid, name, typ, ph)

        # 아이디/비번 입력
        id_input = page.locator('input[type=text], input[type=email]').first
        pw_input = page.locator('input[type=password]').first
        if await id_input.count() > 0:
            await id_input.click()
            await page.keyboard.type(NAVER_ID, delay=50)
            await pw_input.click()
            await page.keyboard.type(NAVER_PW, delay=50)
            await page.wait_for_timeout(1000)
            login_submit = page.locator('button[type=submit], button:has-text("로그인")')
            if await login_submit.count() > 0:
                await login_submit.first.click()
            await page.wait_for_timeout(4000)

        print("로그인 시도 후 url:", page.url)
        body = await page.locator("body").inner_text()
        print("본문 일부:", body[:500])
        await page.screenshot(path="step3_after_login.png", full_page=True)

        await browser.close()


asyncio.run(main())
