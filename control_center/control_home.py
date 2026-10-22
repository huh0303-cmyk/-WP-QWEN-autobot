from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from flask import jsonify, render_template
import requests

from .blog_metadata import infrastructure_info, opening_recent_info

ROOT = Path(__file__).resolve().parents[1]
KST = timezone(timedelta(hours=9))


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _norm(value: object) -> str:
    return "".join(ch.lower() for ch in str(value or "") if ch.isalnum())


def _delta(current, previous):
    if isinstance(current, (int, float)) and isinstance(previous, (int, float)):
        return int(current - previous)
    return None


def _social_revenue(platform: str, handle: str, channel_id: str) -> dict:
    """Return only revenue states confirmed by the operations ledger.

    TOPIK is recorded as monetization-approved in situation_room_daily.py, but
    the YouTube revenue OAuth is not connected yet.  Keep the amount empty
    instead of inventing a zero or an estimate.
    """
    normalized_handle = _norm(handle)
    if platform == "YouTube" and (
        channel_id == "UCdA24IuR-JE7qButWv5jLqA"
        or normalized_handle in {"seoultopik", "seoultopik1"}
    ):
        return {
            "monetized": True,
            "amount": None,
            "delta": None,
            "currency": "USD",
            "status": "수익 데이터 권한 필요",
        }
    return {
        "monetized": False,
        "amount": None,
        "delta": None,
        "currency": "",
        "status": "미연결",
    }


def _youtube_stats_by_identity(bucket: int):
    del bucket
    history = _read(ROOT / "situation_room_history.json", {})
    latest = history.get("latest", {}).get("youtube", {})
    previous = history.get("previous", {}).get("youtube", {})
    current_map, previous_map = {}, {}
    for key, row in latest.items():
        if not isinstance(row, dict):
            continue
        for token in (key, row.get("title"), row.get("handle")):
            if _norm(token):
                current_map[_norm(token)] = row
    for key, row in previous.items():
        if not isinstance(row, dict):
            continue
        for token in (key, row.get("title"), row.get("handle")):
            if _norm(token):
                previous_map[_norm(token)] = row
    return current_map, previous_map, history.get("updated_at", "")


def _youtube_public_stats() -> tuple[dict[str, dict], str]:
    snapshot = _read(ROOT / "data" / "youtube_public_metrics.json", {})
    return snapshot.get("channels", {}), snapshot.get("checked_at_kst", "")


def _sns_probe_stats() -> dict[tuple[str, str], dict]:
    snapshot = _read(ROOT / "data" / "ceo_sns_probe.json", {})
    return {
        (str(row.get("platform") or "").lower(), str(row.get("brand") or "").upper()): row
        for row in snapshot.get("rows", [])
        if isinstance(row, dict)
    }


def _latest_social_publications() -> dict[tuple[str, str], dict]:
    snapshot = _read(ROOT / "data" / "social_publication_receipts.json", {})
    latest: dict[tuple[str, str], dict] = {}
    for row in snapshot.get("publications", []):
        if not isinstance(row, dict):
            continue
        key = (str(row.get("platform") or "").lower(), str(row.get("role") or ""))
        if not all(key):
            continue
        if key not in latest or str(row.get("published_at") or "") > str(latest[key].get("published_at") or ""):
            latest[key] = row
    return latest


ROLE_TO_PROBE_BRAND = {
    "korean_topik": "TOPIK",
    "english": "ENGLISH",
    "japanese": "LANGUAGE",
}


def build_youtube_ranking(bucket: int) -> dict:
    inventory = _read(ROOT / "config" / "london_social_account_inventory_2026-09-24.json", {})
    current_map, previous_map, updated_at = _youtube_stats_by_identity(bucket)
    public_stats, public_updated_at = _youtube_public_stats()
    rows = []
    for item in inventory.get("youtube", []):
        candidates = [_norm(item.get("name")), _norm(item.get("handle"))]
        current = next((current_map.get(k) for k in candidates if k and current_map.get(k)), {})
        previous = next((previous_map.get(k) for k in candidates if k and previous_map.get(k)), {})
        public = public_stats.get(item.get("channel_id", ""), {})
        subs = public.get("subscribers") if public.get("subscribers") is not None else (current.get("subs") if isinstance(current, dict) else None)
        views = public.get("views") if public.get("views") is not None else (current.get("views") if isinstance(current, dict) else None)
        videos = public.get("videos") if public.get("videos") is not None else (current.get("videos") if isinstance(current, dict) else None)
        timeline = opening_recent_info("", "youtube", item.get("channel_id", ""))
        rows.append({
            "name": public.get("name") or item.get("name") or item.get("channel_id"),
            "channel_id": item.get("channel_id", ""),
            "handle": item.get("handle") or "",
            "url": f"https://www.youtube.com/channel/{item.get('channel_id')}" if item.get("channel_id") else "",
            "category": item.get("group") or "YouTube",
            "subscribers": subs,
            "subscriber_delta": _delta(subs, previous.get("subs") if isinstance(previous, dict) else None),
            "views": views,
            "view_delta": _delta(views, previous.get("views") if isinstance(previous, dict) else None),
            "videos": videos,
            "video_delta": _delta(videos, previous.get("videos") if isinstance(previous, dict) else None),
            "revenue": _social_revenue("YouTube", current.get("handle") or item.get("handle") or "", item.get("channel_id", "")),
            "opening_date": timeline.get("opening_date") or str(item.get("created_at") or "")[:10] or (str(current.get("created_at") or "")[:10] if isinstance(current, dict) else ""),
            "recent_publish_date": timeline.get("recent_publish_date") or str(item.get("recent_publish_date") or "")[:10],
            "last_post_url": timeline.get("recent_video_url") or "",
            "last_post_id": timeline.get("recent_video_id") or "",
            "infrastructure": infrastructure_info("youtube"),
            "connected": isinstance(subs, (int, float)),
        })
    # UC ID가 없는 계획 슬롯은 실제 채널 순위/개수에 포함하지 않는다.
    rows.sort(key=lambda r: (
        r["subscribers"] is None,
        -(r["subscribers"] or 0),
        -(r["views"] or 0),
        str(r["name"]).casefold(),
    ))
    rank = 0
    for row in rows:
        if row["subscribers"] is None:
            row["rank"] = None
        else:
            rank += 1
            row["rank"] = rank
    return {
        "generated_at": datetime.now(KST).isoformat(),
        "updated_at": public_updated_at or updated_at,
        "total": len(rows),
        "ranked": rank,
        "rows": rows,
    }


ROLE_TO_HISTORY = {
    "korean_topik": "TOPIK",
    "english": "ENGLISH",
    "japanese": "LANGUAGE",
}
def build_sns_ranking(bucket: int) -> dict:
    del bucket
    policy = _read(ROOT / "config" / "sns_six_channel_policy.json", {})
    active_roles = set(policy.get("active_roles", []))
    role_labels = {
        str(row.get("key") or ""): str(row.get("name") or row.get("key") or "")
        for row in policy.get("roles", []) if isinstance(row, dict)
    }
    history = _read(ROOT / "situation_room_history.json", {})
    latest = history.get("latest", {})
    previous = history.get("previous", {})
    audience_path = Path("/opt/korea365/data/account-audience-metrics.json")
    if not audience_path.exists():
        audience_path = ROOT / "data" / "account-audience-metrics.json"
    audience = _read(audience_path, {}).get("accounts", {})
    probe = _sns_probe_stats()
    publications = _latest_social_publications()
    rows = []
    for item in policy.get("accounts", []):
        platform = str(item.get("platform") or "")
        pkey = platform.lower()
        role = str(item.get("role") or "")
        active_role = role in active_roles
        hist_key = ROLE_TO_HISTORY.get(str(item.get("role") or ""))
        current = latest.get(pkey, {}).get(hist_key, {}) if hist_key else {}
        old = previous.get(pkey, {}).get(hist_key, {}) if hist_key else {}
        followers = current.get("count") if isinstance(current, dict) else None
        probe_row = probe.get((pkey, ROLE_TO_PROBE_BRAND.get(str(item.get("role") or ""), "")), {})
        if probe_row.get("followers") is not None:
            followers = probe_row.get("followers")
        handle = str(item.get("handle") or "")
        audience_row = audience.get(handle, {}) if handle else {}
        yesterday_views = audience_row.get("views") if isinstance(audience_row, dict) else None
        publication = publications.get((pkey, role), {})
        display_name = str(item.get("display_name") or role_labels.get(role) or role or handle)
        current_public_name = str(item.get("current_public_name") or "").strip()
        if current_public_name and current_public_name != display_name:
            display_name = f"{display_name} (현재: {current_public_name})"
        if not active_role:
            metric_status = "비활성 레거시 역할 · 순위 제외"
        elif not item.get("account_exists"):
            metric_status = "계정 미확인 · 순위 없음"
        elif not item.get("identity_verified"):
            metric_status = "계정 ID 확인 필요"
        elif isinstance(followers, (int, float)):
            metric_status = probe_row.get("status") or "조회 성공"
        else:
            metric_status = probe_row.get("status") or "API 인증 필요"
        rows.append({
            "platform": platform,
            "name": display_name,
            "role": role,
            "role_label": role_labels.get(role, role or "SNS 계정"),
            "active_role": active_role,
            "account_exists": bool(item.get("account_exists")),
            "identity_verified": bool(item.get("identity_verified")),
            "publish_connected": bool(item.get("publish_connected")),
            "handle": handle if item.get("identity_verified") else "",
            "url": (item.get("url") or "") if item.get("identity_verified") else "",
            "followers": followers,
            "followers_delta": _delta(followers, old.get("count") if isinstance(old, dict) else None),
            "yesterday_views": yesterday_views,
            "views_delta": audience_row.get("delta") if isinstance(audience_row, dict) else None,
            "content_count": audience_row.get("content_count") if isinstance(audience_row, dict) else None,
            "content_delta": audience_row.get("content_delta") if isinstance(audience_row, dict) else None,
            "revenue": _social_revenue(platform, handle, ""),
            "opening_date": str(item.get("created_at") or item.get("opening_date") or "")[:10],
            "recent_publish_date": publication.get("published_at") or str(item.get("recent_publish_date") or "")[:10],
            "last_post_url": publication.get("url") or "",
            "last_post_id": publication.get("post_id") or "",
            "connected": isinstance(followers, (int, float)),
            "metric_status": metric_status,
        })
    platform_order = {"Facebook": 0, "Threads": 1, "Instagram": 2, "TikTok": 3}
    rows.sort(key=lambda r: (
        platform_order.get(str(r["platform"]), 99),
        r["followers"] is None,
        -(r["followers"] or 0),
        -(r["yesterday_views"] or 0),
        str(r["name"]).casefold(),
    ))
    platform_rank: dict[str, int] = {}
    for row in rows:
        platform = str(row["platform"] or "")
        if not row["active_role"] or not row["identity_verified"] or row["followers"] is None:
            row["rank"] = None
        else:
            platform_rank[platform] = platform_rank.get(platform, 0) + 1
            row["rank"] = platform_rank[platform]
    return {
        "generated_at": datetime.now(KST).isoformat(),
        "updated_at": history.get("updated_at", ""),
        "total": len(rows),
        "ranked": sum(platform_rank.values()),
        "rows": rows,
    }

def build_social_ranking(bucket: int) -> dict:
    youtube = build_youtube_ranking(bucket)
    sns = build_sns_ranking(bucket)
    rows = []
    for item in youtube["rows"]:
        rows.append({
            "platform": "YouTube",
            "name": item.get("name"),
            "handle": item.get("handle") or "",
            "channel_id": item.get("channel_id") or "",
            "category": item.get("category") or "YouTube",
            "active_role": True,
            "account_exists": True,
            "identity_verified": True,
            "publish_connected": False,
            "url": (
                f"https://www.youtube.com/@{item.get('handle')}"
                if item.get("handle") and item.get("channel_id")
                else item.get("url") or ""
            ),
            "audience": item.get("subscribers"),
            "audience_delta": item.get("subscriber_delta"),
            "views": item.get("views"),
            "views_delta": item.get("view_delta"),
            # A YouTube snapshot delta is the available daily view count.  Keep
            # cumulative views separate so the UI never labels it as yesterday.
            "yesterday_views": item.get("view_delta"),
            "yesterday_views_delta": None,
            "content_count": item.get("videos"),
            "content_count_delta": item.get("video_delta"),
            "revenue": item.get("revenue") or {},
            "opening_date": item.get("opening_date") or "",
            "recent_publish_date": item.get("recent_publish_date") or "",
            "last_post_url": item.get("last_post_url") or "",
            "last_post_id": item.get("last_post_id") or "",
            "infrastructure": item.get("infrastructure") or infrastructure_info("youtube"),
            "connected": item.get("connected", False),
            "metric_status": "조회 성공" if item.get("connected", False) else "YouTube 공개 API 갱신 필요",
            "views_status": "조회 성공" if item.get("connected", False) else "YouTube 공개 API 갱신 필요",
        })
    for item in sns["rows"]:
        rows.append({
            "platform": item.get("platform"),
            "name": item.get("name"),
            "handle": item.get("handle") or "",
            "channel_id": "",
            "category": item.get("role_label") or item.get("role") or "",
            "active_role": bool(item.get("active_role")),
            "account_exists": bool(item.get("account_exists")),
            "identity_verified": bool(item.get("identity_verified")),
            "publish_connected": bool(item.get("publish_connected")),
            "url": item.get("url") or "",
            "audience": item.get("followers"),
            "audience_delta": item.get("followers_delta"),
            "views": item.get("yesterday_views"),
            "views_delta": item.get("views_delta"),
            "yesterday_views": item.get("yesterday_views"),
            "yesterday_views_delta": item.get("views_delta"),
            "content_count": item.get("content_count"),
            "content_count_delta": item.get("content_delta"),
            "revenue": item.get("revenue") or {},
            "opening_date": item.get("opening_date") or "",
            "recent_publish_date": item.get("recent_publish_date") or "",
            "last_post_url": item.get("last_post_url") or "",
            "last_post_id": item.get("last_post_id") or "",
            "infrastructure": infrastructure_info(str(item.get("platform") or "").lower()),
            "connected": item.get("connected", False),
            "metric_status": item.get("metric_status") or "플랫폼 API 인증 필요",
            "views_status": "인사이트 API 인증 필요",
        })
    platform_order = {"YouTube": 0, "Facebook": 1, "Threads": 2, "Instagram": 3, "TikTok": 4}
    rows.sort(key=lambda r: (
        platform_order.get(str(r["platform"]), 99),
        r["audience"] is None,
        -(r["audience"] or 0),
        -(r["views"] or 0),
        str(r["name"]).casefold(),
    ))
    platform_rank: dict[str, int] = {}
    for row_number, row in enumerate(rows, 1):
        row["row_number"] = row_number
        platform = str(row["platform"] or "")
        if not row.get("active_role") or not row.get("identity_verified") or row["audience"] is None:
            row["rank"] = None
        else:
            platform_rank[platform] = platform_rank.get(platform, 0) + 1
            row["rank"] = platform_rank[platform]
    youtube_total = len(youtube["rows"])
    sns_account_total = len(sns["rows"])
    sns_active_total = sum(bool(row.get("active_role")) for row in sns["rows"])
    now = datetime.now(KST)
    return {
        "generated_at": now.isoformat(),
        "display_date": now.date().isoformat(),
        "ranking_date": (now.date() - timedelta(days=1)).isoformat(),
        "total": len(rows),
        "ranked": sum(platform_rank.values()),
        "youtube_total": youtube_total,
        "sns_active_total": sns_active_total,
        "target_total": 47,
        "target_youtube": 23,
        "target_sns": 24,
        "target_active_sns": 16,
        "sns_account_total": sns_account_total,
        "count_confirmation_required": youtube_total != 23 or sns_account_total != 24,
        "rows": rows,
    }



def build_blogger_pageviews() -> dict:
    """Read the Blogger API pageview snapshot generated by the daily dashboard collector."""
    remote_url = "https://raw.githubusercontent.com/huh0303-cmyk/-WP-QWEN-autobot/main/docs/dashboard.json"
    payload = {}
    try:
        response = requests.get(remote_url, params={"refresh": int(datetime.now().timestamp() // 300)}, timeout=8)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        payload = _read(ROOT / "docs" / "dashboard.json", {})
    result = payload.get("blogger_pageviews") if isinstance(payload, dict) else None
    if not isinstance(result, dict):
        return {
            "generated_at": payload.get("generated_at", "") if isinstance(payload, dict) else "",
            "blogs": [],
            "status": "PAGEVIEWS_SNAPSHOT_UNAVAILABLE",
        }
    result.setdefault("status", "OK")
    return result


def install(app):
    @app.get("/control-home")
    def control_home():
        return render_template("control_home.html"), 200, {"Cache-Control": "no-store"}

    @app.get("/api/control/blogger-pageviews")
    def blogger_pageviews():
        result = build_blogger_pageviews()
        return jsonify(result), (200 if result.get("blogs") else 503), {"Cache-Control": "no-store"}

    @app.get("/api/control/youtube-ranking")
    def youtube_ranking():
        return jsonify(build_youtube_ranking(int(datetime.now().timestamp() // 300))), 200, {"Cache-Control": "no-store"}

    @app.get("/api/control/sns-ranking")
    def sns_ranking():
        return jsonify(build_sns_ranking(int(datetime.now().timestamp() // 300))), 200, {"Cache-Control": "no-store"}

    @app.get("/api/control/social-ranking")
    def social_ranking():
        return jsonify(build_social_ranking(int(datetime.now().timestamp() // 300))), 200, {"Cache-Control": "no-store"}
