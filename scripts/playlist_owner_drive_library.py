"""Owner music library on Google Drive: dedup by content checksum + 7-day no-repeat ledger.

Tracks live in the owner's Drive folder tree ("플리채널"/<genre folder>). Nothing is
generated or paid for here. A track is skipped when:
  * another file with the same md5Checksum was already seen (content duplicate), or
  * its checksum was used by a published/staged mix in the last COOLDOWN_DAYS days.
The ledger is a small JSON file kept in the library root folder on Drive.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import random
from pathlib import Path

COOLDOWN_DAYS = 7
MIN_SECONDS = 50 * 60
MAX_SECONDS = 70 * 60
LEDGER_NAME = "used_tracks_ledger.json"
ROOT_NAME = os.environ.get("PLAYLIST_LIBRARY_ROOT_NAME", "플리채널")
AUDIO_EXT = (".mp3", ".wav", ".m4a")
FOLDER_MIME = "application/vnd.google-apps.folder"

# channel -> Drive sub-folder names under the library root (owner's own genre folders)
CHANNEL_FOLDERS = {
    "kpop": ["K-pop"],
    "globalmusic": ["로맨틱글로벌음악"],
    "starbucks": ["스타벅스_카페음악"],
    "mbb": ["모짜르트_바흐_베트벤클래식"],
}


def _q(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _find_folder(service, name, parent=None):
    query = f"mimeType = '{FOLDER_MIME}' and name = '{_q(name)}' and trashed = false"
    if parent:
        query += f" and '{parent}' in parents"
    rows = service.files().list(q=query, fields="files(id,name)", pageSize=20,
                                supportsAllDrives=True, includeItemsFromAllDrives=True).execute().get("files", [])
    return rows


def _walk_audio(service, folder_id):
    """Yield audio files below folder_id (recursive) with md5Checksum."""
    stack, seen_folders = [folder_id], set()
    while stack:
        current = stack.pop()
        if current in seen_folders:
            continue
        seen_folders.add(current)
        token = None
        while True:
            resp = service.files().list(
                q=f"'{current}' in parents and trashed = false",
                fields="nextPageToken, files(id,name,mimeType,md5Checksum,size,shortcutDetails)",
                pageSize=1000, pageToken=token,
                supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
            for item in resp.get("files", []):
                if item["mimeType"] == FOLDER_MIME:
                    stack.append(item["id"])
                elif item["name"].lower().endswith(AUDIO_EXT) and item.get("md5Checksum"):
                    yield item
            token = resp.get("nextPageToken")
            if not token:
                break


def _load_ledger(service, root_id):
    rows = service.files().list(q=f"'{root_id}' in parents and name = '{LEDGER_NAME}' and trashed = false",
                                fields="files(id)", supportsAllDrives=True,
                                includeItemsFromAllDrives=True).execute().get("files", [])
    if not rows:
        return None, {}
    from googleapiclient.http import MediaIoBaseDownload
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, service.files().get_media(fileId=rows[0]["id"], supportsAllDrives=True))
    done = False
    while not done:
        _, done = downloader.next_chunk()
    try:
        return rows[0]["id"], json.loads(buffer.getvalue().decode("utf-8"))
    except ValueError:
        return rows[0]["id"], {}


def _save_ledger(service, root_id, file_id, ledger):
    from googleapiclient.http import MediaIoBaseUpload
    media = MediaIoBaseUpload(io.BytesIO(json.dumps(ledger, ensure_ascii=False, indent=1).encode("utf-8")),
                              mimetype="application/json")
    if file_id:
        service.files().update(fileId=file_id, media_body=media, supportsAllDrives=True).execute()
    else:
        service.files().create(body={"name": LEDGER_NAME, "parents": [root_id]}, media_body=media,
                               fields="id", supportsAllDrives=True).execute()


def select_library_tracks(service, channel, workdir, download, duration_fn, rng=None):
    """Return (rows, ledger_state). rows: dict(path,name,duration,md5). Fails closed."""
    rng = rng or random.Random()
    if channel not in CHANNEL_FOLDERS:
        raise RuntimeError(f"WAITING_OWNER_LIBRARY: no library folder mapped for {channel}")
    roots = _find_folder(service, ROOT_NAME)
    if not roots:
        raise RuntimeError(f"WAITING_OWNER_LIBRARY: Drive folder '{ROOT_NAME}' not visible to the runner account")
    root_id = roots[0]["id"]
    genre_ids = []
    for folder_name in CHANNEL_FOLDERS[channel]:
        found = _find_folder(service, folder_name, root_id)
        if not found:
            raise RuntimeError(f"WAITING_OWNER_LIBRARY: sub-folder '{folder_name}' not found under '{ROOT_NAME}'")
        genre_ids.append(found[0]["id"])
    ledger_id, ledger = _load_ledger(service, root_id)
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=COOLDOWN_DAYS)
    blocked = set()
    for md5, stamp in ledger.items():
        try:
            if dt.datetime.fromisoformat(stamp) > cutoff:
                blocked.add(md5)
        except ValueError:
            continue
    unique, seen = [], set()
    total_found = duplicates = cooling = 0
    for genre_id in genre_ids:
        for item in _walk_audio(service, genre_id):
            total_found += 1
            md5 = item["md5Checksum"].lower()
            if md5 in seen:
                duplicates += 1
                continue
            seen.add(md5)
            if md5 in blocked:
                cooling += 1
                continue
            unique.append(item)
    rng.shuffle(unique)
    print(f"OWNER_LIBRARY channel={channel} found={total_found} duplicates={duplicates} "
          f"cooldown7d={cooling} available={len(unique)}", flush=True)
    target = rng.randint(MIN_SECONDS, MAX_SECONDS)
    audio_root = Path(workdir) / "owner_library_audio"
    audio_root.mkdir(parents=True, exist_ok=True)
    chosen, total = [], 0.0
    for item in unique:
        if total >= target:
            break
        suffix = Path(item["name"]).suffix.lower()
        path = audio_root / f"{item['md5Checksum'].lower()}{suffix}"
        try:
            download(service, item["id"], str(path))
            seconds = float(duration_fn(str(path)))
        except Exception as exc:  # unreadable file: skip, never abort the whole mix
            print(f"OWNER_LIBRARY_SKIP {item['name']}: {exc}", flush=True)
            path.unlink(missing_ok=True)
            continue
        if not 30 <= seconds <= 15 * 60:
            path.unlink(missing_ok=True)
            continue
        chosen.append({"path": str(path), "name": item["name"], "duration": seconds,
                       "md5": item["md5Checksum"].lower()})
        total += seconds
    if total < MIN_SECONDS:
        raise RuntimeError(
            f"WAITING_FRESH_COMPOSITIONS: only {total/60:.0f} min of non-repeated tracks available for {channel} "
            f"(need {MIN_SECONDS//60}+). Add tracks to the Drive folder or compose new ones."
        )
    return chosen, (root_id, ledger_id, ledger, now)


def record_used(service, state, rows):
    """Write the 7-day ledger. Call only after the mix was built successfully."""
    root_id, ledger_id, ledger, now = state
    stamp = now.isoformat()
    for row in rows:
        ledger[row["md5"]] = stamp
    horizon = now - dt.timedelta(days=60)
    for key in [k for k, v in ledger.items() if v < horizon.isoformat()]:
        ledger.pop(key, None)
    _save_ledger(service, root_id, ledger_id, ledger)
