#!/usr/bin/env python3
"""Publish generated adjective Shorts with exact-channel verification and receipts."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "artifacts" / "youtube" / "language-adjectives"


def env_for(code: str, name: str) -> str:
    suffix = f"LANGUAGE_{code.upper()}"
    value = os.environ.get(f"YOUTUBE_OAUTH_{name}_{suffix}") or os.environ.get(f"YOUTUBE_OAUTH_{name}")
    if not value:
        raise RuntimeError(f"Missing YOUTUBE_OAUTH_{name}_{suffix}")
    return value


def youtube_service(code: str):
    credentials = Credentials(
        token=None,
        refresh_token=env_for(code, "REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=env_for(code, "CLIENT_ID"),
        client_secret=env_for(code, "CLIENT_SECRET"),
        scopes=None,
    )
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


def authenticated_channel_id(service) -> str:
    result = service.channels().list(part="id", mine=True).execute().get("items", [])
    if len(result) != 1:
        raise RuntimeError(f"Expected exactly one authenticated YouTube channel, received {len(result)}")
    return result[0]["id"]


def verified_video(service, video_id: str, expected_channel_id: str, expected_privacy: str,
                   expected_publish_at: str | None = None) -> dict:
    rows = service.videos().list(part="snippet,status,processingDetails", id=video_id).execute().get("items", [])
    if len(rows) != 1:
        raise RuntimeError(f"Uploaded video {video_id} is not readable")
    video = rows[0]
    actual_channel = video.get("snippet", {}).get("channelId")
    actual_privacy = video.get("status", {}).get("privacyStatus")
    if actual_channel != expected_channel_id:
        raise RuntimeError(f"Wrong-channel upload blocked: expected {expected_channel_id}, got {actual_channel}")
    if actual_privacy != expected_privacy:
        raise RuntimeError(f"Privacy verification failed: expected {expected_privacy}, got {actual_privacy}")
    if expected_publish_at:
        actual_publish_at = video.get("status", {}).get("publishAt")
        if not actual_publish_at:
            raise RuntimeError(f"Scheduled publish time missing for {video_id}")
        expected = dt.datetime.fromisoformat(expected_publish_at.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
        actual = dt.datetime.fromisoformat(actual_publish_at.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
        if actual != expected:
            raise RuntimeError(f"Scheduled publish time mismatch for {video_id}: expected {expected.isoformat()}, got {actual.isoformat()}")
    return video


def wait_for_verified_video(service, video_id: str, expected_channel_id: str, expected_privacy: str,
                            expected_publish_at: str | None = None) -> dict:
    """Allow YouTube's videos.list index to catch up after insert.

    Never repeat an upload on an ambiguous verification result: that can create
    duplicate public videos. Retry only the read, then fail closed.
    """
    last_error = None
    for attempt in range(8):
        try:
            return verified_video(service, video_id, expected_channel_id, expected_privacy, expected_publish_at)
        except RuntimeError as exc:
            message = str(exc)
            if "is not readable" not in message:
                raise
            last_error = exc
            if attempt < 7:
                time.sleep(2)
    raise RuntimeError(f"Uploaded video {video_id} still not readable after bounded checks: {last_error}")


def make_old_video_private(service, video_id: str, expected_channel_id: str) -> dict:
    rows = service.videos().list(part="snippet,status", id=video_id).execute().get("items", [])
    if len(rows) != 1 or rows[0].get("snippet", {}).get("channelId") != expected_channel_id:
        raise RuntimeError("Replacement target does not belong to the exact authenticated channel")
    old_status = rows[0].get("status", {})
    body_status = {
        key: old_status[key]
        for key in ("license", "embeddable", "publicStatsViewable", "selfDeclaredMadeForKids")
        if key in old_status
    }
    body_status["privacyStatus"] = "private"
    service.videos().update(part="status", body={"id": video_id, "status": body_status}).execute()
    last_error = None
    for _ in range(8):
        try:
            verified_video(service, video_id, expected_channel_id, "private")
            break
        except RuntimeError as exc:
            last_error = exc
            time.sleep(2)
    else:
        raise RuntimeError(f"Old video privacy did not converge to private: {last_error}")
    return {"video_id": video_id, "privacy_status": "private"}


def publish_one(manifest_path: Path, privacy: str, publish_at: str | None = None) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    code = manifest["language_code"]
    expected_channel = manifest["channel_id"]
    receipt_path = manifest_path.with_name("publication_receipt.json")
    service = youtube_service(code)
    mine = authenticated_channel_id(service)
    if mine != expected_channel:
        raise RuntimeError(f"Authenticated channel mismatch for {code}: expected {expected_channel}, got {mine}")
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        verified_video(service, receipt["video_id"], expected_channel, privacy, publish_at)
        return receipt
    video_path = Path(manifest["video_path"])
    if not video_path.exists():
        raise FileNotFoundError(video_path)
    status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}
    if publish_at:
        if privacy != "private":
            raise RuntimeError("YouTube scheduled videos must be uploaded as private")
        status["publishAt"] = publish_at
    request = service.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": manifest["title"][:100],
                "description": manifest["description"],
                "tags": manifest["tags"],
                "categoryId": "27",
                "defaultLanguage": code if code != "zh" else "zh-Hans",
            },
            "status": status,
        },
        media_body=MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True, chunksize=8 * 1024 * 1024),
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response["id"]
    video = wait_for_verified_video(service, video_id, expected_channel, privacy, publish_at)
    receipt = {
        "published_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "language_code": code,
        "channel_id": expected_channel,
        "video_id": video_id,
        "url": f"https://www.youtube.com/shorts/{video_id}",
        "privacy_status": video["status"]["privacyStatus"],
        "processing_status": video.get("processingDetails", {}).get("processingStatus"),
        "pair_id": manifest["pair_id"],
        "scheduled_publish_at": video.get("status", {}).get("publishAt"),
    }
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest["publication_status"] = "verified_public" if privacy == "public" else f"verified_{privacy}"
    manifest["publication_receipt"] = str(receipt_path.resolve())
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--languages", default="all")
    parser.add_argument("--privacy", choices=("public", "private", "unlisted"), default="public")
    parser.add_argument("--publish-at", help="Schedule publication time as an ISO-8601 timestamp; uploads privately")
    parser.add_argument("--replace-video-id", help="With exactly one language, make this old video private after the corrected upload is public")
    parser.add_argument("--replace-video-ids", help="Comma-separated language:oldVideoId map for a corrected batch")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    root = Path(args.output_root).resolve() / args.date
    batch = json.loads((root / "batch_manifest.json").read_text(encoding="utf-8"))
    codes = batch["completed_languages"] if args.languages == "all" else [v.strip() for v in args.languages.split(",") if v.strip()]
    if args.replace_video_id and len(codes) != 1:
        raise RuntimeError("--replace-video-id requires exactly one language")
    replace_map = {}
    if args.replace_video_ids:
        for item in args.replace_video_ids.split(","):
            code, separator, video_id = item.strip().partition(":")
            if not separator or code not in codes or not video_id:
                raise RuntimeError(f"Invalid replacement mapping: {item}")
            replace_map[code] = video_id
    if args.replace_video_id:
        replace_map[codes[0]] = args.replace_video_id
    receipts = []
    for code in codes:
        print(f"PUBLISH {code}", flush=True)
        receipts.append(publish_one(root / code / "manifest.json", args.privacy, args.publish_at))
    for code, old_video_id in replace_map.items():
        service = youtube_service(code)
        expected_channel = json.loads((root / code / "manifest.json").read_text(encoding="utf-8"))["channel_id"]
        receipt = next(row for row in receipts if row["language_code"] == code)
        receipt["replaced_old_video"] = make_old_video_private(service, old_video_id, expected_channel)
    summary = {"date": args.date, "privacy": args.privacy, "count": len(receipts), "receipts": receipts}
    (root / "publication_batch_receipt.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
