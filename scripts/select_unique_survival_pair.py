#!/usr/bin/env python3
"""Choose a reviewed, unused adjective pair across the requested language channels."""
from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parents[1]
PAIR_PATH = ROOT / "config" / "survival_adjective_pairs.json"
CHANNEL_PATH = ROOT / "config" / "survival_language_channels.json"


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[^\w]+", "", value, flags=re.UNICODE)


def service_for(code: str):
    suffix = f"LANGUAGE_{code.upper()}"
    client_id = os.getenv(f"YOUTUBE_OAUTH_CLIENT_ID_{suffix}") or os.getenv("YOUTUBE_OAUTH_CLIENT_ID", "")
    client_secret = os.getenv(f"YOUTUBE_OAUTH_CLIENT_SECRET_{suffix}") or os.getenv("YOUTUBE_OAUTH_CLIENT_SECRET", "")
    refresh = os.getenv(f"YOUTUBE_OAUTH_REFRESH_TOKEN_{suffix}", "")
    if not all((client_id, client_secret, refresh)):
        raise RuntimeError(f"Missing YouTube OAuth credentials for language={code}")
    credentials = Credentials(
        token=None, refresh_token=refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id, client_secret=client_secret, scopes=None,
    )
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


def channel_metadata(service, expected_channel: str) -> list[str]:
    mine = service.channels().list(part="id,contentDetails", mine=True).execute().get("items", [])
    if len(mine) != 1 or mine[0].get("id") != expected_channel:
        actual = [row.get("id", "") for row in mine]
        raise RuntimeError(f"Exact-channel check failed; expected={expected_channel}, actual={actual}")
    uploads = mine[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    video_ids, page_token = [], None
    while True:
        page = service.playlistItems().list(
            part="contentDetails", playlistId=uploads, maxResults=50, pageToken=page_token
        ).execute()
        video_ids.extend(row["contentDetails"]["videoId"] for row in page.get("items", []))
        page_token = page.get("nextPageToken")
        if not page_token:
            break
    metadata = []
    for offset in range(0, len(video_ids), 50):
        rows = service.videos().list(
            part="snippet", id=",".join(video_ids[offset:offset + 50])
        ).execute().get("items", [])
        for row in rows:
            snippet = row.get("snippet", {})
            metadata.append(" ".join([
                snippet.get("title", ""),
                snippet.get("description", ""),
                " ".join(snippet.get("tags", [])),
            ]).casefold())
    return metadata



def pair_is_used(pair: dict, language_code: str, normalized_history: list[str]) -> bool:
    """Return true when this exact lesson already appears in one uploaded item."""
    pair_id = norm(pair.get("id", ""))
    words = [norm(word) for word in pair.get(language_code, []) if norm(word)]
    for row in normalized_history:
        # Keep each video's metadata together: do not accidentally combine one
        # word from one old upload with the other word from a different upload.
        if (pair_id and pair_id in row) or (len(words) >= 2 and all(word in row for word in words)):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--languages", default="all")
    args = parser.parse_args()
    registry = json.loads(CHANNEL_PATH.read_text(encoding="utf-8"))["languages"]
    by_code = {row["language_code"]: row for row in registry if row.get("upload_enabled", True)}
    codes = list(by_code) if args.languages == "all" else [v.strip() for v in args.languages.split(",") if v.strip()]
    invalid = sorted(set(codes) - set(by_code))
    if invalid:
        raise RuntimeError(f"Unknown/unregistered languages: {invalid}")

    catalog = json.loads(PAIR_PATH.read_text(encoding="utf-8"))["pairs"]
    # Low-value standalone beginner noun pairs (sun/moon, book/phone,
    # water/coffee) are retired from the daily Shorts curriculum. The format
    # is now adjective contrasts only; do not silently cycle the noun subset.
    catalog = [pair for pair in catalog if pair.get("category", "adjective") != "noun"]
    if not catalog:
        raise RuntimeError("No reviewed adjective lessons remain in the vocabulary catalog.")

    used_metadata = {}
    for code in codes:
        svc = service_for(code)
        rows = channel_metadata(svc, by_code[code]["channel_id"])
        used_metadata[code] = [norm(item) for item in rows]
        print(f"HISTORY_CHECK_OK language={code} uploads_scanned={len(rows)}", flush=True)

    for pair in catalog:
        # Search all ten channels, and keep title/description/tags from each
        # video as one record so only a complete localized pair or stable ID
        # marks that lesson as used.
        used = any(pair_is_used(pair, code, used_metadata[code]) for code in codes)
        if not used:
            print(f"SELECTED_PAIR_ID={pair['id']}", flush=True)
            github_output = os.getenv("GITHUB_OUTPUT")
            if github_output:
                with open(github_output, "a", encoding="utf-8") as stream:
                    stream.write(f"pair_id={pair['id']}\n")
            return 0

    raise RuntimeError("No unused reviewed adjective pair remains across the requested channels; expand the reviewed catalog instead of repeating content.")


if __name__ == "__main__":
    raise SystemExit(main())
