import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(ignore_https_errors=True)

        await page.goto("https://domeggook.com/main/member/mem_formLogin.php", timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        await page.fill("#idInput", "huh0303")
        await page.fill("#pwInput", "Huh556423!")
        await page.locator("input[type=submit]").first.click()
        await page.wait_for_timeout(3000)

        try:
            resp = await page.goto("https://speedgo.domeggook.com/", timeout=30000, wait_until="domcontentloaded")
            print("status:", resp.status if resp else None)
            print("url:", page.url)
            await page.wait_for_timeout(3000)
            body = await page.locator("body").inner_text()
            print(body[:3000])
            await page.screenshot(path="speedgo_result.png", full_page=True)
        except Exception as e:
            print("오류:", e)

        await browser.close()

asyncio.run(main())
