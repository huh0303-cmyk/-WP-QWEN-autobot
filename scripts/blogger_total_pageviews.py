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


async def extract_widget_total(page):
    """Read the Stats widget's dedicated counter element, never a chart/axis number.

    Blogger injects the real counter into an element whose id ends in
    '_totalCount'. If absent or ambiguous, fail closed rather than report an
    unrelated but plausible-looking number.
    """
    async def read_counters():
        counters = page.locator("[id$='_totalCount']")
        values = []
        for i in range(await counters.count()):
            node = counters.nth(i)
            try:
                if not await node.is_visible():
                    continue
                raw = (await node.inner_text(timeout=1500)).strip()
                if re.fullmatch(r"[\\d,]+", raw):
                    values.append(int(raw.replace(",", "")))
            except Exception:
                continue
        return sorted(set(values))

    values = await read_counters()
    if not values:
        await page.wait_for_timeout(2500)
        values = await read_counters()
    if len(values) == 1:
        return values[0]
    if len(values) > 1:
        raise ValueError("TOTAL_PAGEVIEWS_COUNTER_AMBIGUOUS")
    raise ValueError("TOTAL_PAGEVIEWS_COUNTER_NOT_FOUND")


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
    selected_key = __import__("os").environ.get("PAGEVIEWS_SITE_KEY", "").strip().lower()
    channels = config.get("channels", [])
    if selected_key:
        channels = [b for b in channels if selected_key in str(b.get("site_key") or b.get("title") or b.get("blogspot") or "").lower()
                    or selected_key in str(b.get("blogspot") or "").lower()]
        if not channels:
            raise SystemExit("No Blogger portfolio entry matched PAGEVIEWS_SITE_KEY=" + selected_key)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        semaphore = asyncio.Semaphore(2)
        rows = await asyncio.gather(*(collect_one(browser, b, semaphore, checked_at) for b in channels))
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
    today = now.date().isoformat()
    for row in rows:
        url_key = str(row.get("url", "")).rstrip("/").lower()
        target = existing.get(url_key)
        if target is None:
            target = {"key": row["site_key"], "site_key": row["site_key"], "url": row["url"], "title": row["title"], "history": []}
            pageviews.setdefault("blogs", []).append(target)
            existing[url_key] = target
        target["title"] = row["title"]
        if row["total_pageviews"] is not None:
            history = target.setdefault("history", [])
            prior = next((h for h in reversed(history) if h.get("date", "") < today and h.get("total_pageviews") is not None), None)
            daily = None
            if prior is not None and int(row["total_pageviews"]) >= int(prior["total_pageviews"]):
                daily = int(row["total_pageviews"]) - int(prior["total_pageviews"])
            elif prior is not None:
                row["status"] = "COUNTER_DECREASE_REVIEW"
            # One snapshot per date: repeat runs cannot fabricate zero-change days.
            history = [h for h in history if h.get("date") != today]
            history.append({"date": today, "total_pageviews": int(row["total_pageviews"]), "daily_pageviews": daily})
            target["history"] = history[-60:]
            target["total_pageviews"] = int(row["total_pageviews"])
            target["daily_pageviews"] = daily
            target["status"] = row["status"]
            target["source"] = row["source"]
            target["checked_at"] = checked_at
        else:
            # Preserve last-known good totals, but never label a failed refresh as healthy.
            target["last_attempt_at"] = checked_at
            target["last_attempt_status"] = row["status"]
            target["status"] = row["status"]
    pageviews["generated_at"] = checked_at
    pageviews["source"] = payload["source"]
    pageviews["successful"] = payload["successful"]
    pageviews["failed"] = payload["failed"]
    dashboard["generated_at"] = dashboard.get("generated_at") or checked_at
    DASHBOARD.write_text(json.dumps(dashboard, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"total_blogs": payload["total_blogs"], "successful": payload["successful"], "failed": payload["failed"]}, ensure_ascii=False))
    for row in rows:
        print(("PAGEVIEWS_OK " + row["site_key"] + " " + str(row["total_pageviews"])) if row["total_pageviews"] is not None else ("PAGEVIEWS_FAIL " + row["site_key"] + " " + row["status"]))
    if not payload["successful"]:
        print("WARNING: no counters could be verified; last-known good totals were preserved and failure states recorded.")


if __name__ == "__main__":
    asyncio.run(run())
