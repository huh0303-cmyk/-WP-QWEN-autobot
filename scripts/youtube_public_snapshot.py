"""Snapshot public YouTube statistics for every confirmed London channel."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
KST = timezone(timedelta(hours=9))


def collect(api_key: str) -> dict:
    inventory = json.loads(
        (ROOT / "config" / "london_social_account_inventory_2026-09-24.json").read_text(encoding="utf-8")
    )
    channels = [row for row in inventory.get("youtube", []) if row.get("channel_id")]
    ids = [row["channel_id"] for row in channels]
    response = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "snippet,statistics", "id": ",".join(ids), "key": api_key},
        timeout=30,
    )
    response.raise_for_status()
    found = {row["id"]: row for row in response.json().get("items", [])}
    rows = {}
    for configured in channels:
        channel_id = configured["channel_id"]
        item = found.get(channel_id, {})
        stats = item.get("statistics", {})
        snippet = item.get("snippet", {})
        rows[channel_id] = {
            "name": snippet.get("title") or configured.get("name") or channel_id,
            "handle": configured.get("handle") or "",
            "subscribers": int(stats["subscriberCount"]) if stats.get("subscriberCount") is not None else None,
            "views": int(stats["viewCount"]) if stats.get("viewCount") is not None else None,
            "videos": int(stats["videoCount"]) if stats.get("videoCount") is not None else None,
            "connected": bool(item),
        }
    return {
        "checked_at_kst": datetime.now(KST).isoformat(),
        "source": "YouTube Data API v3 public statistics",
        "confirmed_channels": len(channels),
        "connected_channels": sum(1 for row in rows.values() if row["connected"]),
        "channels": rows,
    }


def main() -> None:
    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("YOUTUBE_API_KEY is required")
    result = collect(api_key)
    destination = ROOT / "data" / "youtube_public_metrics.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("confirmed_channels", "connected_channels", "source")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
