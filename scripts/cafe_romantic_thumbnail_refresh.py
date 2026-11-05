#!/usr/bin/env python3
"""One-time, exact-channel CAFE_ROMANTIC thumbnail refresh; no paid generation APIs."""
from __future__ import annotations

import datetime as dt
import os
import sys
import time

import requests
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from PIL import Image, ImageChops, ImageStat

EXPECTED_CHANNEL_ID = "UCbJfEtsffpgI5MsKkB7BYvQ"
THUMBNAIL_NAME = os.getenv("THUMBNAIL_FILE_NAME", "cafe_romantic_thumbnail_2026-11-05.jpg")
MAX_VIDEO_AGE_DAYS = 120


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required GitHub environment value: {name}")
    return value


def drive_service():
    creds = Credentials(
        token=None,
        refresh_token=required("GOOGLE_OAUTH_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=required("GOOGLE_OAUTH_CLIENT_ID"),
        client_secret=required("GOOGLE_OAUTH_CLIENT_SECRET"),
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def youtube_service():
    creds = Credentials(
        token=None,
        refresh_token=required("YOUTUBE_OAUTH_REFRESH_TOKEN_GLOBALMUSIC"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=required("YOUTUBE_OAUTH_CLIENT_ID_GLOBALMUSIC"),
        client_secret=required("YOUTUBE_OAUTH_CLIENT_SECRET_GLOBALMUSIC"),
        scopes=None,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def download_thumbnail(service, folder_id: str, destination: Path) -> None:
    query = (
        f"'{folder_id}' in parents and "
        f"name = '{THUMBNAIL_NAME}' and trashed = false"
    )
    rows = service.files().list(
        q=query, fields="files(id,name,mimeType,size)", pageSize=10
    ).execute().get("files", [])
    if len(rows) != 1:
        raise RuntimeError(
            f"Expected exactly one Drive thumbnail named {THUMBNAIL_NAME}; found {len(rows)}"
        )
    row = rows[0]
    if row.get("mimeType") != "image/jpeg":
        raise RuntimeError(f"Thumbnail must be JPEG; received {row.get('mimeType')}")
    if int(row.get("size", 0)) > 2_000_000:
        raise RuntimeError("Thumbnail exceeds YouTube's 2 MB image limit")
    request = service.files().get_media(fileId=row["id"])
    with destination.open("wb") as handle:
        downloader = MediaIoBaseDownload(handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    with Image.open(destination) as image:
        image.verify()
    with Image.open(destination) as image:
        if image.format != "JPEG" or image.size != (1280, 720):
            raise RuntimeError(f"Expected 1280x720 JPEG, received {image.format} {image.size}")
    print(f"THUMBNAIL_SOURCE_VERIFIED name={row['name']} bytes={destination.stat().st_size}")


def latest_public_video(service) -> dict:
    channels = service.channels().list(part="id,contentDetails", mine=True).execute().get("items", [])
    if len(channels) != 1 or channels[0].get("id") != EXPECTED_CHANNEL_ID:
        actual = [item.get("id") for item in channels]
        raise RuntimeError(f"Exact-channel identity check failed: expected={EXPECTED_CHANNEL_ID}, actual={actual}")
    uploads = channels[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    page = service.playlistItems().list(
        part="contentDetails", playlistId=uploads, maxResults=50
    ).execute()
    ids = [item["contentDetails"]["videoId"] for item in page.get("items", [])]
    if not ids:
        raise RuntimeError("No uploaded videos found on the authenticated CAFE_ROMANTIC channel")
    rows = []
    for start in range(0, len(ids), 50):
        rows.extend(service.videos().list(
            part="snippet,status", id=",".join(ids[start:start + 50])
        ).execute().get("items", []))
    public = [
        row for row in rows
        if row.get("snippet", {}).get("channelId") == EXPECTED_CHANNEL_ID
        and row.get("status", {}).get("privacyStatus") == "public"
    ]
    if not public:
        raise RuntimeError("No public video found; refusing to update an unverified target")
    public.sort(key=lambda row: row.get("snippet", {}).get("publishedAt", ""), reverse=True)
    target = public[0]
    published = dt.datetime.fromisoformat(
        target["snippet"]["publishedAt"].replace("Z", "+00:00")
    )
    age = (dt.datetime.now(dt.timezone.utc) - published).days
    if age > MAX_VIDEO_AGE_DAYS:
        raise RuntimeError(f"Latest public video is {age} days old; target requires manual review")
    print(
        "TARGET_VIDEO "
        f"id={target['id']} "
        f"title={target['snippet'].get('title','')!r} "
        f"published_at={target['snippet']['publishedAt']} "
        f"age_days={age} "
        f"privacy={target['status']['privacyStatus']}"
    )
    return target


def main() -> int:
    workdir = Path("artifacts/cafe-romantic-thumbnail")
    workdir.mkdir(parents=True, exist_ok=True)
    image_path = workdir / "cafe_romantic_thumbnail.jpg"
    drive = drive_service()
    download_thumbnail(drive, required("THUMBNAIL_FOLDER_ID_GLOBALMUSIC"), image_path)

    youtube = youtube_service()
    target = latest_public_video(youtube)
    response = youtube.thumbnails().set(
        videoId=target["id"],
        media_body=MediaFileUpload(str(image_path), mimetype="image/jpeg", resumable=True),
    ).execute()
    # thumbnails.set may return only kind/etag, not the thumbnail resource itself.
    # Verify the actual CDN image against our submitted file instead of assuming
    # the response object contains high/standard/maxres fields.
    print(f"THUMBNAIL_SET_API_ACCEPTED response_keys={','.join(sorted(response.keys()))}")
    last_diff = None
    for attempt in range(1, 7):
        verify = youtube.videos().list(part="snippet,status", id=target["id"]).execute().get("items", [])
        if len(verify) != 1 or verify[0].get("snippet", {}).get("channelId") != EXPECTED_CHANNEL_ID:
            raise RuntimeError("Thumbnail update read-back failed: video/channel identity changed")
        thumbnails = verify[0].get("snippet", {}).get("thumbnails", {})
        thumb = thumbnails.get("maxres") or thumbnails.get("standard") or thumbnails.get("high")
        if not thumb or not thumb.get("url"):
            raise RuntimeError("Thumbnail read-back returned no usable thumbnail URL")
        cdn = requests.get(thumb["url"], params={"refresh": str(int(time.time()))}, timeout=30)
        cdn.raise_for_status()
        cdn_path = workdir / "youtube_thumbnail_readback.jpg"
        cdn_path.write_bytes(cdn.content)
        with Image.open(image_path) as submitted:
            submitted_rgb = submitted.convert("RGB").resize((320, 180))
        with Image.open(cdn_path) as actual:
            actual_rgb = actual.convert("RGB").resize((320, 180))
        last_diff = ImageStat.Stat(ImageChops.difference(submitted_rgb, actual_rgb).convert("L")).mean[0]
        print(f"THUMBNAIL_READBACK attempt={attempt} mean_pixel_difference={last_diff:.2f}")
        if last_diff < 45:
            print(
                "THUMBNAIL_UPDATE_VERIFIED "
                f"channel_id={EXPECTED_CHANNEL_ID} "
                f"video_id={target['id']} "
                f"video_url=https://www.youtube.com/watch?v={target['id']} "
                f"thumbnail_keys={','.join(sorted(thumbnails.keys()))}"
            )
            return 0
        time.sleep(3)
    raise RuntimeError(f"Thumbnail CDN read-back did not match submitted image; mean difference={last_diff:.2f}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"CAFE_ROMANTIC_THUMBNAIL_REFRESH_FAILED: {exc}", file=sys.stderr)
        raise
