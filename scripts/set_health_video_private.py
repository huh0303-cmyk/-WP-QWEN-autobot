#!/usr/bin/env python3
"""Set exactly two previously uploaded Health Clinic videos to Private and verify status."""
import json
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

CLIENT_ID = os.getenv("YOUTUBE_OAUTH_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("YOUTUBE_OAUTH_CLIENT_SECRET", "").strip()
TARGETS = [
    {
        "channel": "Health Clinic USA",
        "token_env": "HEALTH_CLINIC_YOUTUBE_REFRESH_TOKEN_EN",
        "video_id": "7qUEOZk8rB0",
        "channel_id": "UC91BpNSb4nUwD6jrpthK7FQ",
    },
    {
        "channel": "Health Clinic Japan",
        "token_env": "HEALTH_CLINIC_YOUTUBE_REFRESH_TOKEN_JP",
        "video_id": "eQsq_5utuHc",
        "channel_id": "UCC_PcHMv-Uxpr00Pjw_J2Wg",
    },
]

def service_for(target):
    refresh_token = os.getenv(target["token_env"], "").strip()
    if not CLIENT_ID or not CLIENT_SECRET or not refresh_token:
        raise RuntimeError(f"Missing required OAuth configuration for {target['channel']}.")
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/youtube.force-ssl"],
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds, cache_discovery=False)

def main():
    receipts = []
    for target in TARGETS:
        yt = service_for(target)
        channels = yt.channels().list(part="id", mine=True).execute().get("items", [])
        actual_channels = [row.get("id", "") for row in channels]
        if actual_channels != [target["channel_id"]]:
            raise RuntimeError(
                f"Exact-channel check failed for {target['channel']}: "
                f"expected {target['channel_id']}, got {actual_channels}."
            )
        rows = yt.videos().list(part="snippet,status", id=target["video_id"]).execute().get("items", [])
        if len(rows) != 1:
            raise RuntimeError(f"Video {target['video_id']} was not returned to the authorized channel.")
        row = rows[0]
        if row.get("snippet", {}).get("channelId") != target["channel_id"]:
            raise RuntimeError(f"Video {target['video_id']} belongs to a different channel; refusing update.")
        before = row.get("status", {}).get("privacyStatus", "unknown")
        if before != "private":
            yt.videos().update(
                part="status",
                body={"id": target["video_id"], "status": {"privacyStatus": "private"}},
            ).execute()
        verified = yt.videos().list(part="snippet,status", id=target["video_id"]).execute().get("items", [])
        if len(verified) != 1 or verified[0].get("status", {}).get("privacyStatus") != "private":
            raise RuntimeError(f"Privacy verification failed for {target['video_id']}.")
        receipts.append({
            "channel": target["channel"],
            "channel_id": target["channel_id"],
            "video_id": target["video_id"],
            "privacy_before": before,
            "privacy_after": "private",
            "verified": True,
        })
        print(json.dumps(receipts[-1], ensure_ascii=False))
    print("VERIFIED_PRIVATE=" + json.dumps(receipts, ensure_ascii=False))

if __name__ == "__main__":
    main()
