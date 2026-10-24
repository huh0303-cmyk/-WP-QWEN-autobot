#!/usr/bin/env python3
"""Privatize lower-view duplicate Japanese Survival Shorts, keeping the highest-view copy."""
import json, os
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

CHANNEL_ID = "UCOWoNH_d6p45ywQ6W0Z1Jng"
# Duplicate groups confirmed from the channel's recent Shorts listing.
GROUPS = {
    "高い vs 低い": ["ZmWrRKSI9Qo", "K4hdomfDbsk"],
    "太陽 • 月 (Oct 20-21)": ["TVzpGZKfDTk", "qUbaTDn3Rgg"],
    "水 • コーヒー": ["fMRfZJ3IvnU", "_CxJYICGdvA", "tDJZWEM6OvM", "N6Ybf-Vmq_s"],
    "熱い vs 冷たい": ["1CBYlntI1Js", "Hs2MNvElLcs"],
}
def env(name, fallback=None):
    value = os.getenv(name) or (os.getenv(fallback) if fallback else None)
    if not value:
        raise RuntimeError(f"Missing required environment secret: {name}")
    return value

creds = Credentials(
    token=None,
    refresh_token=env("YOUTUBE_OAUTH_REFRESH_TOKEN_LANGUAGE_JA"),
    token_uri="https://oauth2.googleapis.com/token",
    client_id=env("YOUTUBE_OAUTH_CLIENT_ID"),
    client_secret=env("YOUTUBE_OAUTH_CLIENT_SECRET"),
    scopes=["https://www.googleapis.com/auth/youtube.force-ssl"],
)
yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
channels = yt.channels().list(part="id", mine=True).execute().get("items", [])
if len(channels) != 1 or channels[0]["id"] != CHANNEL_ID:
    raise RuntimeError(f"Wrong authenticated channel; expected {CHANNEL_ID}, got {[c.get('id') for c in channels]}")
report = []
for label, ids in GROUPS.items():
    rows = yt.videos().list(part="id,snippet,status,statistics", id=",".join(ids), maxResults=50).execute().get("items", [])
    by_id = {r["id"]: r for r in rows}
    missing = sorted(set(ids) - set(by_id))
    if missing:
        raise RuntimeError(f"Could not verify all videos for {label}: missing {missing}; no changes made for this group")
    for v in rows:
        if v.get("snippet", {}).get("channelId") != CHANNEL_ID:
            raise RuntimeError(f"Video {v['id']} is not owned by Japanese Survival; aborting")
    ranked = sorted(rows, key=lambda v: int(v.get("statistics", {}).get("viewCount", 0)), reverse=True)
    keep = ranked[0]
    group_report = {"group": label, "kept": {"id": keep["id"], "title": keep["snippet"].get("title"), "views": int(keep.get("statistics", {}).get("viewCount", 0)), "privacy": keep.get("status", {}).get("privacyStatus")}, "private_candidates": []}
    for v in ranked[1:]:
        status = v.get("status", {})
        views = int(v.get("statistics", {}).get("viewCount", 0))
        if status.get("privacyStatus") != "private":
            body = {k: status[k] for k in ("license", "embeddable", "publicStatsViewable", "selfDeclaredMadeForKids", "containsSyntheticMedia") if k in status}
            body["privacyStatus"] = "private"
            yt.videos().update(part="status", body={"id": v["id"], "status": body}).execute()
        group_report["private_candidates"].append({"id": v["id"], "title": v["snippet"].get("title"), "views": views, "result": "private"})
    report.append(group_report)
print(json.dumps({"channel": CHANNEL_ID, "checked_at": datetime.now(timezone.utc).isoformat(), "groups": report}, ensure_ascii=False, indent=2))
