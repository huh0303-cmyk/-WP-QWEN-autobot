#!/usr/bin/env python3
"""Collect public Blogger Total Pageviews widget counts for the Control dashboard feed."""
import concurrent.futures
import datetime as dt
import json
from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from daily_dashboard import scrape_widget_pageviews  # noqa: E402

KST = dt.timezone(dt.timedelta(hours=9))
PORTFOLIO = ROOT / "config" / "blogger_portfolio.json"
OUTPUTS = [ROOT / "data" / "blogger_total_pageviews.json", ROOT / "docs" / "blogger-total-pageviews.json"]


def collect(blog):
    key = str(blog.get("site_key") or blog.get("title") or blog.get("blogspot") or "unknown")
    url = str(blog.get("blogspot") or "").rstrip("/")
    row = {"site_key": key, "title": blog.get("title") or key, "url": url,
           "total_pageviews": None, "status": "WIDGET_SCRAPE_FAILED", "source": "public_blogger_widget"}
    if not url:
        row["status"] = "BLOG_URL_MISSING"
        return row
    try:
        row["total_pageviews"] = scrape_widget_pageviews(url)
        row["status"] = "OK_WIDGET_ESTIMATE"
    except (requests.RequestException, ValueError, TypeError) as exc:
        row["status"] = str(exc) if str(exc).startswith("TOTAL_PAGEVIEWS_") else "WIDGET_SCRAPE_FAILED"
    return row


def main():
    config = json.loads(PORTFOLIO.read_text(encoding="utf-8"))
    blogs = config.get("channels", [])
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(collect, blogs))
    payload = {"generated_at": dt.datetime.now(KST).isoformat(),
               "source": "Public Blogger Total Pageviews widget; approximate dashboard signal, not analytics-grade",
               "total_blogs": len(rows), "successful": sum(r["total_pageviews"] is not None for r in rows),
               "failed": sum(r["total_pageviews"] is None for r in rows), "blogs": rows}
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    for path in OUTPUTS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(json.dumps({"total_blogs": payload["total_blogs"], "successful": payload["successful"], "failed": payload["failed"], "output": [str(p.relative_to(ROOT)) for p in OUTPUTS]}, ensure_ascii=False))
    if not payload["successful"]:
        raise SystemExit("No Blogger pageview widgets were readable; refusing to publish an all-failed snapshot")


if __name__ == "__main__":
    main()
