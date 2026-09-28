"""Unified 68-card ranking for blog.korea365.org.

WordPress 25 general sites + 2 newsrooms, Blogspot 33, Naver 3 and Tistory 5
(27 + 33 + 3 + 5 = 68) combined into one list, ranked together by yesterday's
visitors. This module does not recompute any metric itself — it normalises
the rows already produced by each platform's existing collector
(get_site_data, get_blogger_data, get_tistory_data, get_naver_data) so the
same public counters, GSC-verified index counts and connector-failure
reasons stay the single source of truth instead of drifting into a second
implementation. A card with no confirmed visitor count is ranked last with
rank=None; it is never shown as 0.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
import csv
import io
import time
from typing import Callable

from flask import Response, jsonify, render_template

KST = timezone(timedelta(hours=9))

NO_VISITOR_TRACKING_REASON: dict[str, str] = {}


def _visitor_connector_status(row: dict, platform: str) -> dict[str, object]:
    if platform in NO_VISITOR_TRACKING_REASON or row.get("visitor_error"):
        return {
            "connected": False,
            "reason": row.get("visitor_error") or NO_VISITOR_TRACKING_REASON.get(platform, ""),
        }
    connected = bool(row["visitor_connected"]) if "visitor_connected" in row else row.get("today_visitors") is not None
    return {"connected": connected, "reason": "" if connected else "방문자 카운터 응답 없음 · 재확인 필요"}


def _connector_status(row: dict, platform: str) -> dict[str, object]:
    """Summarize per-metric connector health strictly from fields the collector already set."""
    return {
        "visitors": _visitor_connector_status(row, platform),
        "content": {"connected": row.get("total_posts") is not None, "reason": row.get("feed_error", "")},
        "index": {"connected": row.get("indexed") is not None, "reason": row.get("index_status", "")},
    }


def _card(row: dict, platform: str, kind: str) -> dict[str, object]:
    url = row.get("url") or (f"https://{row['domain']}" if row.get("domain") else "")
    return {
        "platform": platform,
        "kind": kind,
        "site_id": row.get("site_id"),
        "name": row.get("name") or row.get("domain") or url,
        "url": url,
        "admin_review_url": row.get("admin_review_url", ""),
        "yesterday_visitors": row.get("yesterday_visitors", row.get("today_visitors")),
        "yesterday_visitors_delta": row.get("yesterday_delta", row.get("today_delta")),
        "total_visitors": row.get("total_visitors"),
        "total_visitors_delta": row.get("total_delta"),
        "total_content": row.get("total_posts"),
        "total_content_delta": row.get("posts_delta"),
        "google_indexed": row.get("indexed"),
        "google_indexed_delta": row.get("indexed_delta"),
        "google_indexed_verified_via": "gsc" if row.get("index_checked_at") else None,
        "connector_status": _connector_status(row, platform),
        "checked_at": row.get("visitor_checked_at") or row.get("checked_at") or "",
    }


def build_ranking(
    get_site_data: Callable[[], list],
    get_blogger_data: Callable[[], list],
    get_tistory_data: Callable[[], list],
    get_naver_data: Callable[[], list],
) -> dict[str, object]:
    cards = []
    for row in get_site_data():
        kind = "news" if (row.get("cadence") or {}).get("kind") == "newsroom" else "wordpress"
        cards.append(_card(row, "wordpress", kind))
    for row in get_blogger_data():
        cards.append(_card(row, "blogspot", "blogspot"))
    for row in get_tistory_data():
        cards.append(_card(row, "tistory", "tistory"))
    for row in get_naver_data():
        cards.append(_card(row, "naver", "naver"))

    cards.sort(key=lambda c: (c["yesterday_visitors"] is None, -(c["yesterday_visitors"] or 0), c["name"] or ""))
    rank = 0
    for card in cards:
        if card["yesterday_visitors"] is None:
            card["rank"] = None
        else:
            rank += 1
            card["rank"] = rank

    platform_counts: dict[str, int] = {}
    for card in cards:
        platform_counts[card["platform"]] = platform_counts.get(card["platform"], 0) + 1

    return {
        "generated_at": datetime.now(KST).isoformat(),
        "timezone": "Asia/Seoul",
        "ranking_metric": "yesterday_visitors",
        "total_cards": len(cards),
        "ranked_cards": rank,
        "unranked_cards": len(cards) - rank,
        "platform_counts": platform_counts,
        "cards": cards,
    }


def install(app, get_site_data, get_blogger_data, get_tistory_data, get_naver_data):
    @lru_cache(maxsize=4)
    def cached_payload(five_minute_bucket: int):
        del five_minute_bucket
        return build_ranking(get_site_data, get_blogger_data, get_tistory_data, get_naver_data)

    @app.get("/blog-dashboard")
    def blog_korea365_dashboard():
        return render_template("blog_dashboard.html"), 200, {"Cache-Control": "no-store"}

    @app.get("/api/blog-korea365/ranking")
    def blog_korea365_ranking():
        payload = cached_payload(int(time.time() // 300))
        return jsonify(payload), 200, {"Cache-Control": "no-store"}

    @app.get("/api/blog-korea365/ranking.csv")
    def blog_korea365_ranking_csv():
        payload = cached_payload(int(time.time() // 300))
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["순위", "플랫폼", "사이트", "URL", "어제 방문자", "증감", "총 방문자", "증감", "총 콘텐츠", "증감", "Google 색인", "증감", "GSC 확인", "확인시각"])
        for card in payload["cards"]:
            writer.writerow([
                card.get("rank") or "", card.get("kind") if card.get("kind") == "news" else card.get("platform"),
                card.get("name") or "", card.get("url") or "",
                card.get("yesterday_visitors"), card.get("yesterday_visitors_delta"),
                card.get("total_visitors"), card.get("total_visitors_delta"),
                card.get("total_content"), card.get("total_content_delta"),
                card.get("google_indexed"), card.get("google_indexed_delta"),
                "GSC" if card.get("google_indexed_verified_via") == "gsc" else "",
                card.get("checked_at") or "",
            ])
        content = "\ufeff" + out.getvalue()
        return Response(content, mimetype="text/csv; charset=utf-8",
                        headers={"Content-Disposition": "attachment; filename=korea365-blog-ranking.csv",
                                 "Cache-Control": "no-store"})
