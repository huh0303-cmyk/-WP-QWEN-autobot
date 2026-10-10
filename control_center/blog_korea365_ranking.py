"""Unified 68-card ranking for blog.korea365.org.

WordPress 25 + Blogspot 33 are ranked together using one canonical metric:
Google Search Console Search Analytics clicks on the same confirmed date.
Impressions, CTR and average position are secondary. Visitor widgets, custom
visitor APIs, GA4 and platform counters are excluded from this unified ranking.
ACCESS_UNAVAILABLE is never converted to zero. Naver/Tistory remain visible
on the dashboard but are outside this 58-site GSC ranking.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
import csv
import io
import json
import time
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from flask import Response, jsonify, render_template

from .blog_metadata import (
    domain_info,
    editorial_metadata,
    hosting_info,
    infrastructure_info,
    opening_recent_info,
    revenue_info,
)

KST = timezone(timedelta(hours=9))

NO_VISITOR_TRACKING_REASON: dict[str, str] = {}


@lru_cache(maxsize=2)
def _gsc_metrics(five_minute_bucket: int) -> dict[str, dict[str, object]]:
    """Read the existing daily GSC/traffic manifest without inventing gaps."""
    del five_minute_bucket
    path = Path(__file__).resolve().parents[1] / "data" / "gsc_unified_ranking.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        # Collector records use "site" (canonical URL), not "domain".
        # Normalize both forms to the same URL key used by _card().
        indexed: dict[str, dict[str, object]] = {}
        for row in payload.get("records", []):
            raw = str(row.get("site") or row.get("url") or row.get("domain") or "").strip().lower()
            if not raw:
                continue
            key = raw.rstrip("/")
            indexed[key] = row
            # Accept older manifests keyed by bare host/domain too.
            host = (urlparse(raw).hostname or raw).lower().strip(".")
            indexed.setdefault(host, row)
        return indexed
    except (OSError, ValueError, TypeError):
        return {}


@lru_cache(maxsize=2)
def _gsc_properties(five_minute_bucket: int) -> dict[str, list[dict[str, str]]]:
    """Index the sanitized Search Console property inventory by exact host.

    URL Inspection evidence is stored in the core metrics report, while the
    canonical property/permission list is stored separately. The dashboard
    must use both so a verified property with no clicks is not labelled as
    completely disconnected.
    """
    del five_minute_bucket
    path = Path(__file__).resolve().parents[1] / "data" / "gsc_properties.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    indexed: dict[str, list[dict[str, str]]] = {}
    for item in payload.get("properties", []):
        if not isinstance(item, dict):
            continue
        site_url = str(item.get("siteUrl") or "")
        if site_url.startswith("sc-domain:"):
            host = site_url.removeprefix("sc-domain:").lower().strip(".")
        else:
            host = (urlparse(site_url).hostname or "").lower()
        if host:
            indexed.setdefault(host, []).append({
                "siteUrl": site_url,
                "permissionLevel": str(item.get("permissionLevel") or ""),
            })
    return indexed


def _gsc_property_for(url: str) -> dict[str, str]:
    host = (urlparse(url).hostname or "").lower()
    rows = _gsc_properties(int(time.time() // 300)).get(host, [])
    if not rows:
        return {}
    exact = url.rstrip("/") + "/"
    rows.sort(key=lambda item: (
        item.get("siteUrl") != exact,
        item.get("siteUrl", "").startswith("sc-domain:"),
        item.get("siteUrl", ""),
    ))
    return rows[0]


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
    visitor_status = _visitor_connector_status(row, platform)
    return {
        "visitors": visitor_status,
        "visitor_delta": {
            "connected": visitor_status["connected"] and row.get("yesterday_delta", row.get("today_delta")) is not None,
            "reason": "" if row.get("yesterday_delta", row.get("today_delta")) is not None else "직전 비교값 수집 필요",
        },
        "content": {"connected": row.get("total_posts") is not None, "reason": row.get("feed_error", "")},
        "index": {"connected": row.get("indexed") is not None, "reason": row.get("index_status", "")},
    }


def _card(row: dict, platform: str, kind: str) -> dict[str, object]:
    url = row.get("url") or (f"https://{row['domain']}" if row.get("domain") else "")
    domain = (url.split("://", 1)[-1].split("/", 1)[0] if url else "")
    topic, categories = editorial_metadata(row)
    revenue = revenue_info(domain, row)
    timeline = opening_recent_info(url, platform)
    infra = infrastructure_info(platform, kind)
    gsc_index = _gsc_metrics(int(time.time() // 300))
    gsc = gsc_index.get(url.rstrip("/").lower(), {})
    if not gsc and domain:
        gsc = gsc_index.get(domain.lower().strip("."), {})
    property_row = _gsc_property_for(url)
    if platform in {"wordpress", "blogspot"}:
        gsc_clicks = gsc.get("clicks")
        gsc_impressions = gsc.get("impressions")
        gsc_ctr = gsc.get("ctr")
        gsc_position = gsc.get("position")
        gsc_date = gsc.get("date", "")
        gsc_delta = gsc.get("delta")
        gsc_status = gsc.get("status", "ACCESS_UNAVAILABLE")
    else:
        gsc_clicks = row.get("gsc_clicks", gsc.get("gsc_clicks", gsc.get("clicks")))
        gsc_impressions = row.get("gsc_impressions", gsc.get("impressions"))
        gsc_ctr = row.get("gsc_ctr", gsc.get("ctr"))
        gsc_position = row.get("gsc_position", gsc.get("position"))
        gsc_date = row.get("gsc_date", gsc.get("date", ""))
        gsc_delta = row.get("gsc_delta")
        gsc_status = row.get("gsc_status", "connected" if gsc_clicks is not None else "disconnected")
    gsc_property = (
        row.get("gsc_property")
        or row.get("index_property")
        or gsc.get("gsc_property", "")
        or property_row.get("siteUrl", "")
    )
    gsc_permission = property_row.get("permissionLevel", "")
    gsc_connected = bool(
        row.get("gsc_connected")
        or gsc_property and gsc_permission != "siteUnverifiedUser"
    )
    return {
        "platform": platform,
        "kind": kind,
        "site_id": row.get("site_id"),
        "name": row.get("name") or row.get("domain") or url,
        "url": url,
        "admin_review_url": row.get("admin_review_url", ""),
        "topic": topic,
        "categories": categories,
        "revenue": revenue,
        "domain_info": domain_info(url, platform),
        "hosting_info": hosting_info(url, platform),
        "opening_date": timeline.get("opening_date", ""),
        "recent_publish_date": timeline.get("recent_publish_date", ""),
        "infrastructure": infra,
        "yesterday_visitors": row.get("yesterday_visitors", row.get("today_visitors")),
        "yesterday_visitors_delta": row.get("yesterday_delta", row.get("today_delta")),
        "total_visitors": row.get("total_visitors"),
        "total_visitors_delta": row.get("total_delta"),
        "total_content": row.get("total_posts"),
        "total_content_delta": row.get("posts_delta"),
        "google_indexed": row.get("indexed"),
        "google_indexed_delta": row.get("indexed_delta"),
        "google_indexed_verified_via": "gsc" if row.get("index_checked_at") else None,
        "gsc_clicks": gsc_clicks,
        "gsc_impressions": gsc_impressions,
        "gsc_ctr": gsc_ctr,
        "gsc_position": gsc_position,
        "gsc_date": gsc_date,
        "gsc_delta": gsc_delta,
        "gsc_status": gsc_status,
        "gsc_applicable": platform != "naver",
        "gsc_connected": gsc_connected,
        "gsc_property": gsc_property,
        "gsc_permission": gsc_permission,
        "gsc_status": (
            "api_unsupported" if platform == "naver"
            else "connected" if gsc_connected
            else "user_auth_required" if gsc_permission == "siteUnverifiedUser"
            else "disconnected"
        ),
        "gsc_data_status": str(gsc.get("status") or ("OK" if gsc_clicks is not None and gsc_impressions is not None else "ACCESS_UNAVAILABLE")),
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

    def ranking_key(card):
        applicable = card["platform"] in {"wordpress", "blogspot"}
        value = card.get("gsc_clicks")
        return (not applicable or value is None, -(value or 0), card.get("name") or "")
    cards.sort(key=ranking_key)
    rank = 0
    for row_number, card in enumerate(cards, 1):
        card["row_number"] = row_number
        applicable = card["platform"] in {"wordpress", "blogspot"}
        if not applicable or card.get("gsc_clicks") is None:
            card["rank"] = None
        else:
            rank += 1
            card["rank"] = rank

    platform_counts: dict[str, int] = {}
    for card in cards:
        platform_counts[card["platform"]] = platform_counts.get(card["platform"], 0) + 1

    today = datetime.now(KST).date()
    ranking_date = next((c.get("gsc_date") for c in cards if c.get("gsc_date")), "") or (today - timedelta(days=1)).isoformat()
    return {
        "generated_at": datetime.now(KST).isoformat(),
        "display_date": today.isoformat(),
        "ranking_date": ranking_date,
        "timezone": "Asia/Seoul",
        "ranking_metric": "gsc_clicks",
        "ranking_purpose": "WP25 + Blogspot33 unified GSC ranking",
        "ranking_policy": "Same confirmed GSC date; clicks primary; impressions/CTR/position secondary; visitor counters excluded; ACCESS_UNAVAILABLE is never zero.",
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
        writer.writerow(["순위", "플랫폼", "사이트", "URL", "사이트주제", "카테고리명", "수익", "수익증감", "수익통화", "도메인업체", "도메인결제일", "도메인만료일", "호스팅", "호스팅결제일", "호스팅만료일", "최근발행일", "개설일", "운영위치", "VPS만료일", "GSC 클릭", "GSC 노출", "GSC CTR(%)", "GSC 평균 게재순위", "GSC 기준일", "GSC 데이터 상태", "총 콘텐츠", "증감", "Google 색인", "증감", "GSC 확인", "확인시각"])
        for card in payload["cards"]:
            revenue = card.get("revenue") or {}
            domain_meta = card.get("domain_info") or {}
            hosting_meta = card.get("hosting_info") or {}
            infra = card.get("infrastructure") or {}
            writer.writerow([
                card.get("rank") or "", card.get("kind") if card.get("kind") == "news" else card.get("platform"),
                card.get("name") or "", card.get("url") or "", card.get("topic") or "",
                " · ".join(card.get("categories") or []),
                revenue.get("amount"), revenue.get("delta"), revenue.get("currency") or "",
                domain_meta.get("provider") or "", domain_meta.get("payment_date") or "", domain_meta.get("renewal_date") or "",
                hosting_meta.get("provider") or "", hosting_meta.get("payment_date") or "", hosting_meta.get("renewal_date") or "",
                card.get("recent_publish_date") or "", card.get("opening_date") or "",
                infra.get("label") or "", infra.get("vps_expiry") or "",
                card.get("gsc_clicks"), card.get("gsc_impressions"), card.get("gsc_ctr"),
                card.get("gsc_position"), card.get("gsc_date"), card.get("gsc_data_status"),
                card.get("total_content"), card.get("total_content_delta"),
                card.get("google_indexed"), card.get("google_indexed_delta"),
                "GSC" if card.get("google_indexed_verified_via") == "gsc" else "",
                card.get("checked_at") or "",
            ])
        content = "\ufeff" + out.getvalue()
        return Response(content, mimetype="text/csv; charset=utf-8",
                        headers={"Content-Disposition": "attachment; filename=korea365-blog-ranking.csv",
                                 "Cache-Control": "no-store"})
