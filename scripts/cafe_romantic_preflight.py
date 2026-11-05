#!/usr/bin/env python3
"""Read-only, no-paid-API preflight for the CAFE_ROMANTIC owner music and thumbnail pools."""
from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import sys
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from PIL import Image

EXPECTED_CHANNEL = "globalmusic"
EXPECTED_RIGHTS = "owner_paid_suno"
EXPECTED_GENRE = "romantic_acoustic"


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment value: {name}")
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


def list_children(service, folder_id: str, mime_query: str | None = None) -> list[dict]:
    q = f"'{folder_id}' in parents and trashed = false"
    if mime_query:
        q += f" and mimeType contains '{mime_query}'"
    rows = []
    token = None
    while True:
        page = service.files().list(
            q=q, pageSize=1000, pageToken=token,
            fields="nextPageToken,files(id,name,mimeType,size,md5Checksum)",
        ).execute()
        rows.extend(page.get("files", []))
        token = page.get("nextPageToken")
        if not token:
            return rows


def download(service, file_id: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    request = service.files().get_media(fileId=file_id)
    with path.open("wb") as handle:
        downloader = MediaIoBaseDownload(handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def duration_seconds(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def main() -> int:
    music_folder = required("MUSIC_SOURCE_FOLDER_ID_GLOBALMUSIC")
    thumbnail_folder = required("THUMBNAIL_FOLDER_ID_GLOBALMUSIC")
    if not os.getenv("PEXELS_API_KEY", "").strip():
        raise RuntimeError("PEXELS_API_KEY is missing; recurring free thumbnail rotation is not ready")

    work = Path("artifacts/cafe-romantic-preflight")
    audio_root = work / "audio"
    audio_root.mkdir(parents=True, exist_ok=True)
    drive = drive_service()

    music_files = list_children(drive, music_folder)
    manifests = [x for x in music_files if x.get("name") == "approved.json"]
    if len(manifests) != 1:
        raise RuntimeError(f"Expected one approved.json in Globalmusic Drive folder; found {len(manifests)}")
    manifest_path = work / "approved.json"
    download(drive, manifests[0]["id"], manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("version") != 1 or manifest.get("channel") != EXPECTED_CHANNEL:
        raise RuntimeError("Owner manifest version/channel mismatch")

    tracks = [
        row for row in manifest.get("tracks", [])
        if row.get("approved") is True
        and row.get("channel") == EXPECTED_CHANNEL
        and row.get("genre") == EXPECTED_GENRE
        and row.get("rights") == EXPECTED_RIGHTS
    ]
    language_counts = {
        language: sum(row.get("language") == language for row in tracks)
        for language in ("french", "japanese")
    }
    if language_counts["french"] < 10 or language_counts["japanese"] < 10:
        raise RuntimeError(f"Insufficient balanced approved tracks: {language_counts}")

    audio_files = [
        row for row in music_files
        if row.get("mimeType", "").startswith("audio/")
        or Path(row.get("name", "")).suffix.lower() in {".mp3", ".wav", ".m4a", ".aac", ".flac"}
    ]
    by_name = {}
    for row in audio_files:
        by_name.setdefault(row.get("name", ""), []).append(row)

    staged = []
    for track in tracks:
        name = track["file"]
        if Path(name).name != name:
            raise RuntimeError(f"Unsafe filename in owner manifest: {name}")
        candidates = by_name.get(name, [])
        matched = False
        for candidate in candidates:
            target = audio_root / name
            download(drive, candidate["id"], target)
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            if digest == track["sha256"]:
                seconds = duration_seconds(target)
                if seconds < 30 or seconds > 720:
                    raise RuntimeError(f"Invalid duration {seconds:.1f}s: {name}")
                staged.append({**track, "duration_seconds": seconds})
                matched = True
                break
            target.unlink(missing_ok=True)
        if not matched:
            raise RuntimeError(f"Drive file missing or SHA-256 mismatch: {name}")

    sys.path.insert(0, str(Path("scripts").resolve()))
    from playlist_owner_library import select_owner_tracks
    selected = select_owner_tracks(
        EXPECTED_CHANNEL, audio_root, manifest_path, duration_seconds, random.Random(42)
    )
    total_seconds = sum(row["duration"] for row in selected)
    selected_languages = {
        language: sum(row["language"] == language for row in selected)
        for language in ("french", "japanese")
    }
    if not 3000 <= total_seconds <= 4200:
        raise RuntimeError(f"Selected playlist duration outside 50–70 minutes: {total_seconds/60:.1f}")
    if selected_languages["french"] != selected_languages["japanese"]:
        raise RuntimeError(f"Selected mix is not language-balanced: {selected_languages}")

    thumbnail_files = list_children(drive, thumbnail_folder, "image")
    pexels = [x for x in thumbnail_files if x.get("name", "").lower().startswith("pexels_")]
    if not pexels:
        raise RuntimeError("No unused pexels_* image is staged in the Globalmusic thumbnail folder")
    first = work / "thumbnail_source"
    download(drive, pexels[0]["id"], first)
    with Image.open(first) as image:
        image.verify()
    with Image.open(first) as image:
        if image.width < 1280 or image.height < 720:
            raise RuntimeError(f"Pexels source is undersized: {image.size}")

    print(
        "CAFE_ROMANTIC_PREFLIGHT_PASS "
        f"approved_tracks={len(tracks)} "
        f"french={language_counts['french']} japanese={language_counts['japanese']} "
        f"selected_tracks={len(selected)} selected_minutes={total_seconds/60:.1f} "
        f"selected_languages={selected_languages} "
        f"unused_pexels_images={len(pexels)} "
        "paid_api_usage=disabled"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"CAFE_ROMANTIC_PREFLIGHT_FAILED: {exc}", file=sys.stderr)
        raise
