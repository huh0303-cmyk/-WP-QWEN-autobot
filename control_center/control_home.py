from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from flask import jsonify, render_template

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
            "status": "수익 OAuth 필요",
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
def build_youtube_ranking(bucket: int) -> dict:
    inventory = _read(ROOT / "config" / "london_social_account_inventory_2026-09-24.json", {})
    current_map, previous_map, updated_at = _youtube_stats_by_identity(bucket)
    rows = []
    for item in inventory.get("youtube", []):
        candidates = [_norm(item.get("name")), _norm(item.get("handle"))]
        current = next((current_map.get(k) for k in candidates if k and current_map.get(k)), {})
        previous = next((previous_map.get(k) for k in candidates if k and previous_map.get(k)), {})
        subs = current.get("subs") if isinstance(current, dict) else None
        views = current.get("views") if isinstance(current, dict) else None
        videos = current.get("videos") if isinstance(current, dict) else None
        timeline = opening_recent_info("", "youtube", item.get("channel_id", ""))
        rows.append({
            "name": current.get("title") or item.get("name") or item.get("channel_id"),
            "channel_id": item.get("channel_id", ""),
            "handle": current.get("handle") or item.get("handle") or "",
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
            "infrastructure": infrastructure_info("youtube"),
            "connected": isinstance(subs, (int, float)),
        })
    for item in inventory.get("unconfirmed", []):
        if str(item.get("platform") or "").lower() != "youtube":
            continue
        rows.append({
            "name": item.get("name") or "미확인 YouTube",
            "channel_id": "",
            "handle": item.get("handle") or "",
            "url": "",
            "category": item.get("group") or "additional",
            "subscribers": None, "subscriber_delta": None,
            "views": None, "view_delta": None,
            "videos": None, "video_delta": None,
            "revenue": _social_revenue("YouTube", item.get("handle") or "", ""),
            "opening_date": "", "recent_publish_date": "",
            "infrastructure": infrastructure_info("youtube"),
            "connected": False,
        })
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
        "updated_at": updated_at,
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
    history = _read(ROOT / "situation_room_history.json", {})
    latest = history.get("latest", {})
    previous = history.get("previous", {})
    audience_path = Path("/opt/korea365/data/account-audience-metrics.json")
    if not audience_path.exists():
        audience_path = ROOT / "data" / "account-audience-metrics.json"
    audience = _read(audience_path, {}).get("accounts", {})
    rows = []
    for item in policy.get("accounts", []):
        platform = str(item.get("platform") or "")
        pkey = platform.lower()
        hist_key = ROLE_TO_HISTORY.get(str(item.get("role") or ""))
        current = latest.get(pkey, {}).get(hist_key, {}) if hist_key else {}
        old = previous.get(pkey, {}).get(hist_key, {}) if hist_key else {}
        followers = current.get("count") if isinstance(current, dict) else None
        handle = str(item.get("handle") or "")
        audience_row = audience.get(handle, {}) if handle else {}
        yesterday_views = audience_row.get("views") if isinstance(audience_row, dict) else None
        rows.append({
            "platform": platform,
            "name": item.get("display_name") or item.get("role") or handle,
            "role": item.get("role") or "",
            "handle": handle,
            "url": item.get("url") or "",
            "followers": followers,
            "followers_delta": _delta(followers, old.get("count") if isinstance(old, dict) else None),
            "yesterday_views": yesterday_views,
            "views_delta": audience_row.get("delta") if isinstance(audience_row, dict) else None,
            "content_count": audience_row.get("content_count") if isinstance(audience_row, dict) else None,
            "content_delta": audience_row.get("content_delta") if isinstance(audience_row, dict) else None,
            "revenue": _social_revenue(platform, handle, ""),
            "opening_date": str(item.get("created_at") or item.get("opening_date") or "")[:10],
            "connected": isinstance(followers, (int, float)),
        })
    rows.sort(key=lambda r: (
        r["followers"] is None,
        -(r["followers"] or 0),
        -(r["yesterday_views"] or 0),
        str(r["platform"]),
        str(r["name"]).casefold(),
    ))
    rank = 0
    for row in rows:
        if row["followers"] is None:
            row["rank"] = None
        else:
            rank += 1
            row["rank"] = rank
    return {
        "generated_at": datetime.now(KST).isoformat(),
        "updated_at": history.get("updated_at", ""),
        "total": len(rows),
        "ranked": rank,
        "rows": rows,
    }

ACTIVE_SOCIAL_ROLES = {"korean_topik", "english", "japanese"}


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
            "infrastructure": item.get("infrastructure") or infrastructure_info("youtube"),
            "connected": item.get("connected", False),
        })
    for item in sns["rows"]:
        rows.append({
            "platform": item.get("platform"),
            "name": item.get("name"),
            "handle": item.get("handle") or "",
            "channel_id": "",
            "category": item.get("role") or "",
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
            "infrastructure": infrastructure_info(str(item.get("platform") or "").lower()),
            "connected": item.get("connected", False),
        })
    rows.sort(key=lambda r: (
        r["audience"] is None,
        -(r["audience"] or 0),
        -(r["views"] or 0),
        str(r["platform"]),
        str(r["name"]).casefold(),
    ))
    rank = 0
    for row in rows:
        if row["audience"] is None:
            row["rank"] = None
        else:
            rank += 1
            row["rank"] = rank
    youtube_total = len(youtube["rows"])
    sns_active_total = len(sns["rows"])
    return {
        "generated_at": datetime.now(KST).isoformat(),
        "ranking_date": (datetime.now(KST).date() - timedelta(days=1)).isoformat(),
        "total": len(rows),
        "ranked": rank,
        "youtube_total": youtube_total,
        "sns_active_total": sns_active_total,
        "target_total": 48,
        "target_youtube": 24,
        "count_confirmation_required": youtube_total != 24 or sns_active_total != 24,
        "rows": rows,
    }


def install(app):
    @app.get("/control-home")
    def control_home():
        return render_template("control_home.html"), 200, {"Cache-Control": "no-store"}

    @app.get("/api/control/youtube-ranking")
    def youtube_ranking():
        return jsonify(build_youtube_ranking(int(datetime.now().timestamp() // 300))), 200, {"Cache-Control": "no-store"}

    @app.get("/api/control/sns-ranking")
    def sns_ranking():
        return jsonify(build_sns_ranking(int(datetime.now().timestamp() // 300))), 200, {"Cache-Control": "no-store"}

    @app.get("/api/control/social-ranking")
    def social_ranking():
        return jsonify(build_social_ranking(int(datetime.now().timestamp() // 300))), 200, {"Cache-Control": "no-store"}
