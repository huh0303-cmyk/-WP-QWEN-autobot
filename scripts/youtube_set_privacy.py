#!/usr/bin/env python3
"""Idempotently change one verified channel-owned video to the requested privacy."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]


def _load_vps_runtime() -> None:
    path = Path(os.environ.get("YOUTUBE_RUNTIME_PATH", "/etc/korea365/youtube-runtime.json"))
    if path.is_file():
        values = json.loads(path.read_text(encoding="utf-8"))
        os.environ.update({key: str(value) for key, value in values.items() if value})


def _first(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def get_service(channel_key: str):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    from automation_hub.youtube_registry import load_channels

    channel = next(item for item in load_channels() if item.channel_key == channel_key)
    profile = channel.secret_profile.upper()
    client_id = _first(f"YOUTUBE_OAUTH_CLIENT_ID_{profile}", "YOUTUBE_OAUTH_CLIENT_ID")
    client_secret = _first(f"YOUTUBE_OAUTH_CLIENT_SECRET_{profile}", "YOUTUBE_OAUTH_CLIENT_SECRET")
    refresh_token = _first(f"YOUTUBE_OAUTH_REFRESH_TOKEN_{profile}", "YOUTUBE_OAUTH_REFRESH_TOKEN")
    if not all((client_id, client_secret, refresh_token)):
        raise RuntimeError(f"Missing YouTube OAuth runtime for {channel_key}")
    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=None,
    )
    return build("youtube", "v3", credentials=credentials)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True)
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--privacy", choices=("public", "private"), default="public")
    parser.add_argument("--receipt", default="")
    args = parser.parse_args()
    _load_vps_runtime()

    from automation_hub.youtube_identity import expected_channel_id, verify_authenticated_channel

    youtube = get_service(args.channel)
    authenticated_channel = verify_authenticated_channel(youtube, args.channel)
    response = youtube.videos().list(part="snippet,status", id=args.video_id).execute()
    items = response.get("items", [])
    if len(items) != 1:
        raise RuntimeError(f"Video not found or inaccessible: {args.video_id}")
    video = items[0]
    if video.get("snippet", {}).get("channelId") != expected_channel_id(args.channel):
        raise RuntimeError("Video channel does not match the locked channel ID")

    before = video.get("status", {}).get("privacyStatus", "")
    description_updated = False
    if args.privacy == "public":
        snippet = video.get("snippet", {})
        old_description = str(snippet.get("description", ""))
        new_description = old_description.replace(
            "This sample is uploaded privately for the channel owner's review.",
            "Enjoy this original nature ambience from Cafe Healing.",
        ).replace(
            "This private sample is prepared for the channel owner's review before any public release.",
            "Enjoy this original nature ambience from Cafe Healing.",
        )
        if new_description != old_description:
            updated_snippet = {
                "title": snippet["title"],
                "description": new_description,
                "categoryId": snippet.get("categoryId", "22"),
            }
            for key in ("tags", "defaultLanguage", "defaultAudioLanguage"):
                if key in snippet:
                    updated_snippet[key] = snippet[key]
            youtube.videos().update(
                part="snippet", body={"id": args.video_id, "snippet": updated_snippet}
            ).execute()
            description_updated = True
    if before != args.privacy:
        current = video.get("status", {})
        status = {
            "privacyStatus": args.privacy,
            "selfDeclaredMadeForKids": bool(current.get("selfDeclaredMadeForKids", False)),
        }
        for key in ("license", "embeddable", "publicStatsViewable", "containsSyntheticMedia"):
            if key in current:
                status[key] = current[key]
        youtube.videos().update(part="status", body={"id": args.video_id, "status": status}).execute()

    verified = youtube.videos().list(part="snippet,status", id=args.video_id).execute().get("items", [])
    if len(verified) != 1:
        raise RuntimeError("Video disappeared during privacy verification")
    final = verified[0]
    final_privacy = final.get("status", {}).get("privacyStatus")
    if final.get("snippet", {}).get("channelId") != authenticated_channel or final_privacy != args.privacy:
        raise RuntimeError("Post-update channel/privacy verification failed")
    receipt = {
        "video_id": args.video_id,
        "channel_key": args.channel,
        "verified_channel_id": authenticated_channel,
        "privacy_before": before,
        "privacy_status": final_privacy,
        "public_url": f"https://youtu.be/{args.video_id}",
        "description_updated": description_updated,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
    calendar_rows_updated = []
    if os.environ.get("SHEET_ID", "").strip():
        try:
            from automation_hub.youtube_calendar import read_calendar, update_row
            from gsheets_direct import get_sheets_service

            sheets = get_sheets_service()
            for row in read_calendar(sheets, os.environ["SHEET_ID"]):
                if args.video_id in str(row.get("url", "")):
                    note = row.get("notes", "") + "\n[owner-immediate-public] 기존 영상 공개 전환 및 API 재검증 완료"
                    update_row(sheets, os.environ["SHEET_ID"], row, "공개완료", receipt["public_url"], note)
                    calendar_rows_updated.append(row.get("id", ""))
        except Exception as exc:
            receipt["calendar_update_error"] = f"{type(exc).__name__}: {str(exc)[:240]}"
    receipt["calendar_rows_updated"] = calendar_rows_updated
    if args.receipt:
        path = Path(args.receipt)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
