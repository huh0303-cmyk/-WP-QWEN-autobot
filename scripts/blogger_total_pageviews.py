#!/usr/bin/env python3
"""Render Blogger pages and copy their visible Total Pageviews into the Control dashboard JSON."""
import asyncio
import datetime as dt
import json
import re
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO = ROOT / "config" / "blogger_portfolio.json"
FEEDS = [ROOT / "data" / "blogger_total_pageviews.json", ROOT / "docs" / "blogger-total-pageviews.json"]
DASHBOARD = ROOT / "docs" / "dashboard.json"
KST = dt.timezone(dt.timedelta(hours=9))


def parse_visible_total(text):
    normalized = re.sub(r"[ \t]+", " ", text or "")
    start = re.search(r"Total\s+Pageviews", normalized, re.I)
    if not start:
        raise ValueError("TOTAL_PAGEVIEWS_WIDGET_NOT_FOUND")
    end = re.search(r"\bArchive\b", normalized[start.end():], re.I)
    block = normalized[start.end():start.end() + end.start()] if end else normalized[start.end():start.end() + 1000]
    numbers = re.findall(r"(?<![\w.])\d[\d,]*(?![\w.])", block)
    if not numbers:
        raise ValueError("TOTAL_PAGEVIEWS_NUMBER_NOT_FOUND")
    # Do not choose the last number: chart labels can be larger than the counter.
    return int(numbers[0].replace(",", ""))


async def extract_widget_total(page):
    # Inspect the smallest DOM ancestor containing the widget title, not the whole page.
    title = page.get_by_text(re.compile(r"Total\s+Pageviews", re.I)).first
    for depth in range(1, 8):
        try:
            node = title.locator(f"xpath=ancestor::*[{depth}]")
            text = await node.inner_text(timeout=2000)
            if len(text) > 1800 or not re.search(r"Total\s+Pageviews", text, re.I):
                continue
            value = parse_visible_total(text)
            return value
        except Exception:
            continue
    raise ValueError("TOTAL_PAGEVIEWS_WIDGET_CONTAINER_NOT_FOUND")


async def collect_one(browser, blog, semaphore, checked_at):
    key = str(blog.get("site_key") or blog.get("title") or blog.get("blogspot") or "unknown")
    url = str(blog.get("blogspot") or "").rstrip("/")
    row = {"site_key": key, "title": blog.get("title") or key, "url": url,
           "total_pageviews": None, "status": "WIDGET_SCRAPE_FAILED", "source": "rendered_public_blogger_widget",
           "checked_at": checked_at}
    if not url:
        row["status"] = "BLOG_URL_MISSING"
        return row
    async with semaphore:
        page = await browser.new_page(user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
        try:
            for attempt in range(3):
                response = await page.goto(url + "/", wait_until="domcontentloaded", timeout=30000)
                if response and response.status == 429 and attempt < 2:
                    await page.wait_for_timeout(5000 * (attempt + 1))
                    continue
                await page.wait_for_timeout(1800)
                if response and response.status >= 400:
                    row["status"] = "HTTP_" + str(response.status)
                else:
                    row["total_pageviews"] = await extract_widget_total(page)
                    row["status"] = "OK_WIDGET_ESTIMATE"
                break
        except Exception as exc:
            msg = str(exc)
            row["status"] = msg if msg.startswith("TOTAL_PAGEVIEWS_") else "WIDGET_RENDER_FAILED"
        finally:
            await page.close()
    return row


async def run():
    config = json.loads(PORTFOLIO.read_text(encoding="utf-8"))
    now = dt.datetime.now(KST)
    checked_at = now.isoformat()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        semaphore = asyncio.Semaphore(2)
        rows = await asyncio.gather(*(collect_one(browser, b, semaphore, checked_at) for b in config.get("channels", [])))
        await browser.close()
    payload = {"generated_at": checked_at,
               "source": "Rendered public Blogger Total Pageviews widget; approximate dashboard signal, not analytics-grade",
               "total_blogs": len(rows), "successful": sum(r["total_pageviews"] is not None for r in rows),
               "failed": sum(r["total_pageviews"] is None for r in rows), "blogs": rows}
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    for path in FEEDS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    # Control's live page reads docs/dashboard.json, so merge observed totals there directly.
    dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8")) if DASHBOARD.exists() else {}
    pageviews = dashboard.setdefault("blogger_pageviews", {"blogs": []})
    existing = {str(x.get("url", "")).rstrip("/").lower(): x for x in pageviews.get("blogs", [])}
    for row in rows:
        url_key = str(row.get("url", "")).rstrip("/").lower()
        target = existing.get(url_key)
        if target is None:
            target = {"key": row["site_key"], "site_key": row["site_key"], "url": row["url"], "title": row["title"], "history": []}
            pageviews.setdefault("blogs", []).append(target)
            existing[url_key] = target
        target["title"] = row["title"]
        target["checked_at"] = checked_at
        if row["total_pageviews"] is not None:
            target["total_pageviews"] = row["total_pageviews"]
            target["status"] = "OK_WIDGET_ESTIMATE"
            target["source"] = row["source"]
        elif target.get("total_pageviews") is None:
            target["status"] = row["status"]
    pageviews["generated_at"] = checked_at
    pageviews["source"] = payload["source"]
    dashboard["generated_at"] = dashboard.get("generated_at") or checked_at
    DASHBOARD.write_text(json.dumps(dashboard, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"total_blogs": payload["total_blogs"], "successful": payload["successful"], "failed": payload["failed"]}, ensure_ascii=False))
    for row in rows:
        print(("PAGEVIEWS_OK " + row["site_key"] + " " + str(row["total_pageviews"])) if row["total_pageviews"] is not None else ("PAGEVIEWS_FAIL " + row["site_key"] + " " + row["status"]))
    if not payload["successful"]:
        raise SystemExit("No rendered Blogger pageview widgets were readable; dashboard totals were preserved")


if __name__ == "__main__":
    asyncio.run(run())
