#!/usr/bin/env python3
"""Collect public/account-authorized social metrics for the London Project dashboard.

Uses official APIs only. It does not scrape HTML pages or attempt to bypass login,
rate limits, or platform permissions. Per-account credentials are supplied via the
GitHub Actions secret SOCIAL_METRICS_AUTH_JSON; no tokens are written to output.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "docs" / "social_inventory.json"
OUTPUT_PATH = ROOT / "docs" / "social_metrics.json"
HISTORY_DIR = ROOT / "data" / "social_metrics_history"
KST = timezone(timedelta(hours=9))
TIMEOUT = 20
META_VERSION = os.environ.get("META_GRAPH_API_VERSION", "v23.0").strip() or "v23.0"


def now_kst() -> datetime:
    return datetime.now(KST)


def iso_now() -> str:
    return now_kst().isoformat(timespec="seconds")


def date_part(value: Any) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date().isoformat()
    except (TypeError, ValueError):
        return str(value)[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", str(value)) else None


def as_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def account_key(row: dict[str, Any]) -> str:
    handle = str(row.get("handle") or "").strip().lstrip("@").lower()
    identity = handle or str(row.get("url") or "").strip().lower()
    return f"{row.get('platform', '').lower()}|{identity}"


def auth_for(auth_config: dict[str, Any], platform: str, row: dict[str, Any]) -> dict[str, Any]:
    # Config accepts either handle or full URL as account key. Handle lookup is case-insensitive.
    section = auth_config.get(platform, auth_config.get(platform.lower(), {}))
    if not isinstance(section, dict):
        return {}
    handle = str(row.get("handle") or "").strip().lstrip("@")
    url = str(row.get("url") or "").strip()
    for candidate in (handle, url, handle.lower(), url.lower()):
        entry = section.get(candidate) if candidate else None
        if isinstance(entry, dict):
            return entry
    return {}


def get_json(url: str, *, params: dict[str, Any] | None = None,
             headers: dict[str, str] | None = None, method: str = "GET",
             body: dict[str, Any] | None = None) -> dict[str, Any]:
    # Do not log URLs or request params: provider APIs may put access tokens in params.
    response = requests.request(method, url, params=params, headers=headers, json=body, timeout=TIMEOUT)
    try:
        data = response.json()
    except ValueError:
        data = {}
    if not response.ok:
        error = data.get("error", {}) if isinstance(data, dict) else {}
        message = error.get("message") if isinstance(error, dict) else None
        raise RuntimeError(f"HTTP {response.status_code}: {str(message or 'API request failed')[:180]}")
    if isinstance(data, dict) and isinstance(data.get("error"), dict):
        error = data["error"]
        code = error.get("code") or error.get("type") or "API_ERROR"
        message = str(error.get("message") or "")
        # TikTok v2 includes an error object with code="ok" on successful responses.
        if str(code).lower() not in {"ok", "0", "none"} or message:
            raise RuntimeError(f"{code}: {message or 'API request failed'}"[:220])
    return data if isinstance(data, dict) else {}


def base_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": account_key(row),
        "platform": row.get("platform", ""),
        "name": row.get("name", ""),
        "handle": row.get("handle", ""),
        "url": row.get("url", ""),
        "followers": None,
        "following": None,
        "subscribers": None,
        "total_views": None,
        "total_likes": None,
        "content_count": None,
        "account_created_at": None,
        "creation_date_note": "해당 플랫폼 공식 API에서 개설일을 제공하지 않음",
        "last_publish": date_part(row.get("last_publish")),
        "latest_content_views": None,
        "latest_content_likes": None,
        "latest_content_comments": None,
        "last_stats_checked_at": iso_now(),
        "last_successful_at": None,
        "data_source": None,
        "status": "not_checked",
        "error": "",
    }


def fetch_youtube(rows: list[dict[str, Any]], api_key: str) -> dict[str, dict[str, Any]]:
    channels = []
    for row in rows:
        match = re.search(r"/channel/(UC[A-Za-z0-9_-]{20,})", str(row.get("url") or ""))
        if match:
            channels.append((row, match.group(1)))
    if not channels:
        return {}
    if not api_key:
        return {account_key(row): {"status": "auth_needed", "error": "GitHub Secret YOUTUBE_API_KEY 없음"} for row, _ in channels}

    ids = [channel_id for _, channel_id in channels]
    collected: dict[str, dict[str, Any]] = {}
    latest_video_ids: dict[str, str] = {}
    for offset in range(0, len(ids), 50):
        batch = ids[offset:offset + 50]
        data = get_json("https://www.googleapis.com/youtube/v3/channels",
                        params={"part": "snippet,statistics,contentDetails", "id": ",".join(batch), "key": api_key})
        found = {item["id"]: item for item in data.get("items", []) if item.get("id")}
        for row, channel_id in channels[offset:offset + 50]:
            key = account_key(row)
            item = found.get(channel_id)
            if not item:
                collected[key] = {"status": "api_error", "error": "YouTube API에서 채널 ID를 찾지 못함"}
                continue
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            metrics = {
                "status": "ok",
                "followers": as_int(stats.get("subscriberCount")),
                "subscribers": as_int(stats.get("subscriberCount")),
                "total_views": as_int(stats.get("viewCount")),
                "content_count": as_int(stats.get("videoCount")),
                "account_created_at": date_part(snippet.get("publishedAt")),
                "creation_date_note": "YouTube Data API channels.snippet.publishedAt",
                "data_source": "YouTube Data API v3",
                "last_successful_at": iso_now(),
                "error": "",
            }
            uploads = (item.get("contentDetails", {}).get("relatedPlaylists") or {}).get("uploads")
            if uploads:
                try:
                    latest = get_json("https://www.googleapis.com/youtube/v3/playlistItems",
                                      params={"part": "snippet,contentDetails", "playlistId": uploads,
                                              "maxResults": 1, "key": api_key})
                    items = latest.get("items", [])
                    if items:
                        details = items[0].get("contentDetails", {})
                        metrics["last_publish"] = date_part(details.get("videoPublishedAt") or items[0].get("snippet", {}).get("publishedAt"))
                        video_id = details.get("videoId") or (items[0].get("snippet", {}).get("resourceId") or {}).get("videoId")
                        if video_id:
                            latest_video_ids[key] = video_id
                except Exception as exc:
                    metrics["last_publish_error"] = str(exc)[:180]
            collected[key] = metrics

    # Latest-item engagement is fetched in batches to keep YouTube quota use low.
    video_ids = list(latest_video_ids.values())
    key_by_video = {video_id: key for key, video_id in latest_video_ids.items()}
    for offset in range(0, len(video_ids), 50):
        batch = video_ids[offset:offset + 50]
        try:
            data = get_json("https://www.googleapis.com/youtube/v3/videos",
                            params={"part": "statistics", "id": ",".join(batch), "key": api_key})
            for item in data.get("items", []):
                key = key_by_video.get(item.get("id"))
                if not key or key not in collected:
                    continue
                stats = item.get("statistics", {})
                collected[key].update({
                    "latest_content_views": as_int(stats.get("viewCount")),
                    "latest_content_likes": as_int(stats.get("likeCount")),
                    "latest_content_comments": as_int(stats.get("commentCount")),
                })
        except Exception as exc:
            # Keep account-level statistics even if the optional latest-video metrics fail.
            for key in key_by_video.values():
                if key in collected:
                    collected[key]["latest_content_error"] = str(exc)[:180]
    return collected

def fetch_facebook(row: dict[str, Any], auth: dict[str, Any]) -> dict[str, Any]:
    token = str(auth.get("access_token") or "").strip()
    page_id = str(auth.get("page_id") or auth.get("id") or "").strip()
    if not page_id:
        match = re.search(r"[?&]id=(\d+)", str(row.get("url") or ""))
        page_id = match.group(1) if match else ""
    if not token or not page_id:
        return {"status": "auth_needed", "error": "해당 Facebook 페이지의 page_id/access_token 등록 필요"}
    base = f"https://graph.facebook.com/{META_VERSION}/{page_id}"
    data = get_json(base, params={"fields": "name,followers_count,fan_count", "access_token": token})
    latest_post = {}
    post_count = None
    try:
        posts = get_json(base + "/published_posts", params={
            "fields": "created_time,permalink_url,shares,likes.summary(true),comments.summary(true)",
            "limit": 1, "summary": "true", "access_token": token,
        })
        post_count = as_int((posts.get("summary") or {}).get("total_count"))
        if posts.get("data"):
            latest_post = posts["data"][0]
    except Exception:
        # The Page profile metrics can still be used if post-list permission is narrower.
        pass
    return {
        "status": "ok", "followers": as_int(data.get("followers_count", data.get("fan_count"))),
        "total_likes": as_int(data.get("fan_count")), "content_count": post_count,
        "last_publish": date_part(latest_post.get("created_time")) or None,
        "latest_content_likes": as_int((latest_post.get("likes") or {}).get("summary", {}).get("total_count")),
        "latest_content_comments": as_int((latest_post.get("comments") or {}).get("summary", {}).get("total_count")),
        "data_source": f"Meta Graph API {META_VERSION}", "last_successful_at": iso_now(),
        "account_created_at": date_part(data.get("created_time")),
        "creation_date_note": "API에서 제공되지 않으면 첫 게시일만 표시",
        "error": "",
    }


def fetch_instagram(row: dict[str, Any], auth: dict[str, Any]) -> dict[str, Any]:
    token = str(auth.get("access_token") or "").strip()
    user_id = str(auth.get("user_id") or auth.get("ig_user_id") or auth.get("id") or "").strip()
    if not token or not user_id:
        return {"status": "auth_needed", "error": "Instagram Business/Creator user_id와 access_token 등록 필요"}
    base = f"https://graph.facebook.com/{META_VERSION}/{user_id}"
    data = get_json(base, params={"fields": "username,name,followers_count,follows_count,media_count", "access_token": token})
    latest_post: dict[str, Any] = {}
    try:
        media = get_json(base + "/media", params={
            "fields": "timestamp,permalink,like_count,comments_count", "limit": 1, "access_token": token,
        })
        if media.get("data"):
            latest_post = media["data"][0]
    except Exception:
        pass
    return {
        "status": "ok", "followers": as_int(data.get("followers_count")),
        "following": as_int(data.get("follows_count")), "content_count": as_int(data.get("media_count")),
        "last_publish": date_part(latest_post.get("timestamp")) or None,
        "latest_content_likes": as_int(latest_post.get("like_count")),
        "latest_content_comments": as_int(latest_post.get("comments_count")),
        "data_source": f"Instagram Graph API / Meta {META_VERSION}",
        "last_successful_at": iso_now(),
        "creation_date_note": "Instagram Graph API는 계정 개설일을 제공하지 않음",
        "error": "",
    }


def fetch_threads(row: dict[str, Any], auth: dict[str, Any]) -> dict[str, Any]:
    token = str(auth.get("access_token") or "").strip()
    user_id = str(auth.get("user_id") or auth.get("id") or "").strip()
    if not token or not user_id:
        return {"status": "auth_needed", "error": "Threads user_id와 access_token 등록 필요"}
    root = f"https://graph.threads.net/v1.0/{user_id}"
    values: dict[str, Any] = {}
    try:
        insights = get_json(root + "/threads_insights", params={
            "metric": "followers_count,views,likes,replies,reposts,quotes", "access_token": token,
        })
        for item in insights.get("data", []):
            name = item.get("name") or item.get("metric")
            total = item.get("total_value") or {}
            value = total.get("value")
            if isinstance(value, (int, float)):
                values[name] = int(value)
    except Exception as exc:
        values["_insights_error"] = str(exc)[:180]
    latest_post: dict[str, Any] = {}
    content_count = None
    try:
        media = get_json(root + "/threads", params={
            "fields": "id,timestamp,permalink,views,likes,replies,reposts,quotes", "limit": 100, "access_token": token,
        })
        items = media.get("data", [])
        if items:
            latest_post = max(items, key=lambda x: str(x.get("timestamp") or ""))
            content_count = len(items)
        # Continue pages only to count public posts fully, with a defensive ceiling.
        next_url = (media.get("paging") or {}).get("next")
        while next_url and content_count is not None and content_count < 10000:
            page = get_json(next_url)
            batch = page.get("data", [])
            content_count += len(batch)
            next_url = (page.get("paging") or {}).get("next")
            if not batch:
                break
    except Exception as exc:
        values["_media_error"] = str(exc)[:180]
    if not values and not latest_post:
        raise RuntimeError(values.get("_insights_error") or values.get("_media_error") or "Threads API에서 측정값을 반환하지 않음")
    return {
        "status": "ok", "followers": as_int(values.get("followers_count")),
        "total_views": as_int(values.get("views")), "content_count": content_count,
        "last_publish": date_part(latest_post.get("timestamp")) or None,
        "latest_content_views": as_int(latest_post.get("views")),
        "latest_content_likes": as_int(latest_post.get("likes")),
        "latest_content_comments": as_int(latest_post.get("replies")),
        "data_source": "Threads Graph API", "last_successful_at": iso_now(),
        "creation_date_note": "Threads API는 계정 개설일을 제공하지 않음",
        "error": values.get("_insights_error", "") or values.get("_media_error", ""),
    }


def fetch_tiktok(row: dict[str, Any], auth: dict[str, Any]) -> dict[str, Any]:
    token = str(auth.get("access_token") or "").strip()
    if not token:
        return {"status": "auth_needed", "error": "TikTok OAuth access_token 등록 필요 (HTML 크롤링은 사용하지 않음)"}
    profile = get_json("https://open.tiktokapis.com/v2/user/info/",
                       params={"fields": "open_id,username,display_name,follower_count,following_count,likes_count,video_count"},
                       headers={"Authorization": f"Bearer {token}"})
    user = profile.get("data", {}).get("user", {})
    latest: dict[str, Any] = {}
    try:
        video_data = get_json("https://open.tiktokapis.com/v2/video/list/",
                              params={"fields": "id,create_time,view_count,like_count,comment_count,share_count,video_description"},
                              headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                              method="POST", body={"max_count": 1})
        videos = video_data.get("data", {}).get("videos", [])
        if videos:
            latest = videos[0]
    except Exception:
        pass
    if not user:
        raise RuntimeError("TikTok API returned no user data")
    return {
        "status": "ok", "followers": as_int(user.get("follower_count")),
        "following": as_int(user.get("following_count")), "total_likes": as_int(user.get("likes_count")),
        "content_count": as_int(user.get("video_count")),
        "last_publish": date_part(latest.get("create_time")) or None,
        "latest_content_views": as_int(latest.get("view_count")),
        "latest_content_likes": as_int(latest.get("like_count")),
        "latest_content_comments": as_int(latest.get("comment_count")),
        "data_source": "TikTok API v2 (OAuth)", "last_successful_at": iso_now(),
        "creation_date_note": "TikTok API는 계정 개설일을 제공하지 않음",
        "error": "",
    }


def read_previous() -> dict[str, dict[str, Any]]:
    try:
        raw = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        return {item.get("key"): item for item in raw.get("accounts", []) if item.get("key")}
    except (OSError, ValueError, TypeError):
        return {}


def collect() -> dict[str, Any]:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    rows = inventory.get("accounts", [])
    try:
        auth_config = json.loads(os.environ.get("SOCIAL_METRICS_AUTH_JSON", "{}") or "{}")
        if not isinstance(auth_config, dict):
            raise ValueError("SOCIAL_METRICS_AUTH_JSON must be a JSON object")
    except ValueError as exc:
        raise SystemExit(f"Invalid SOCIAL_METRICS_AUTH_JSON: {exc}")
    previous = read_previous()
    results: dict[str, dict[str, Any]] = {}
    youtube_rows = [row for row in rows if row.get("platform") == "YouTube" and row.get("exists", True)]
    try:
        results.update(fetch_youtube(youtube_rows, os.environ.get("YOUTUBE_API_KEY", "").strip()))
    except Exception as exc:
        safe = str(exc)[:180]
        for row in youtube_rows:
            results.setdefault(account_key(row), {"status": "api_error", "error": safe})

    platform_fetchers = {
        "Facebook": fetch_facebook,
        "Instagram": fetch_instagram,
        "Threads": fetch_threads,
        "TikTok": fetch_tiktok,
    }
    for row in rows:
        platform = row.get("platform", "")
        if platform == "YouTube":
            continue
        if not row.get("exists", True) or not row.get("url"):
            results[account_key(row)] = {"status": "not_created_or_unverified", "error": "등록부에서 계정 미생성/미확인으로 표시"}
            continue
        fetcher = platform_fetchers.get(platform)
        if not fetcher:
            results[account_key(row)] = {"status": "unsupported", "error": "현재 메트릭 수집기 미지원 플랫폼"}
            continue
        try:
            results[account_key(row)] = fetcher(row, auth_for(auth_config, platform, row))
        except Exception as exc:
            results[account_key(row)] = {"status": "api_error", "error": str(exc)[:220]}

    output_rows = []
    statuses: dict[str, dict[str, int]] = {}
    now = iso_now()
    for row in rows:
        item = base_record(row)
        key = item["key"]
        fresh = results.get(key, {"status": "not_checked", "error": "수집 결과 없음"})
        old = previous.get(key, {})
        # Preserve last successful values if today's API call fails; mark the row stale instead of fabricating zeroes.
        successful = fresh.get("status") == "ok"
        if successful:
            item.update(fresh)
            item["last_stats_checked_at"] = now
            item["last_successful_at"] = fresh.get("last_successful_at") or now
        else:
            keep = ("followers", "following", "subscribers", "total_views", "total_likes", "content_count",
                    "account_created_at", "creation_date_note", "last_publish", "latest_content_views",
                    "latest_content_likes", "latest_content_comments", "data_source", "last_successful_at")
            for field in keep:
                if old.get(field) is not None:
                    item[field] = old[field]
            item["status"] = "stale" if old.get("last_successful_at") else fresh.get("status", "api_error")
            item["error"] = fresh.get("error", "")
            item["last_stats_checked_at"] = now
        item.setdefault("status", fresh.get("status", "not_checked"))
        item["error"] = str(item.get("error") or "")[:220]
        platform = item["platform"]
        statuses.setdefault(platform, {}).setdefault(item["status"], 0)
        statuses[platform][item["status"]] += 1
        output_rows.append(item)

    output = {
        "generated_at_kst": now,
        "timezone": "Asia/Seoul",
        "source_policy": "YouTube Data API v3 and authenticated official platform APIs; no HTML scraping or login bypass",
        "total_accounts": len(output_rows),
        "platform_status_counts": statuses,
        "accounts": output_rows,
    }
    return output


def main() -> None:
    result = collect()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    stamp = now_kst().date().isoformat()
    history_path = HISTORY_DIR / f"{stamp}.json"
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    history_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "generated_at_kst": result["generated_at_kst"],
        "total_accounts": result["total_accounts"],
        "platform_status_counts": result["platform_status_counts"],
        "source_policy": result["source_policy"],
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
