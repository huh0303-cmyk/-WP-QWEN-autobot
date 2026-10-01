#!/usr/bin/env python3
"""Build a private, deduplicated catalog of the owner's downloaded Suno audio.

The output is operational input and must stay outside Git.  The script reads
the embedded Suno song UUID, groups byte-identical files by SHA-256, and uses
the owner's Suno song page metadata as review evidence.  It does not approve a
track merely from its filename and it never uploads audio.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import subprocess

import requests


SUNO_ID = re.compile(rb"id=([0-9a-fA-F-]{36})")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _duration(path: Path) -> float:
    value = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        text=True,
    ).strip()
    return round(float(value), 3)


def _suno_id(path: Path) -> str | None:
    match = SUNO_ID.search(path.read_bytes())
    return match.group(1).decode("ascii").lower() if match else None


def _decode(value: str) -> str:
    return json.loads(f'"{value}"')


def _string(body: str, key: str) -> str:
    match = re.search(
        rf'\\"{re.escape(key)}\\":\\"(.*?)\\"(?=,|\}})',
        body,
        re.S,
    )
    return _decode(match.group(1)) if match else ""


def _boolean(body: str, key: str) -> bool | None:
    match = re.search(rf'\\"{re.escape(key)}\\":(true|false)', body)
    return match.group(1) == "true" if match else None


def _metadata(song_id: str) -> dict:
    url = f"https://suno.com/song/{song_id}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    page = response.text
    clip = re.search(r'\\"clip\\":\{(.*?)\\"is_liked\\":', page, re.S)
    body = clip.group(1) if clip else page
    persona = re.search(
        r'\\"persona\\":\{.*?\\"name\\":\\"(.*?)\\"(?=,|\})',
        body,
        re.S,
    )
    return {
        "suno_url": url,
        "suno_title": _string(body, "title"),
        "tags": _string(body, "tags"),
        "persona": _decode(persona.group(1)) if persona else "",
        "has_vocal": _boolean(body, "has_vocal"),
        "make_instrumental": _boolean(body, "make_instrumental"),
        "model": _string(body, "major_model_version"),
        "metadata_status": "verified",
    }


def _suggestions(row: dict) -> list[str]:
    text = " ".join((row["file"], row.get("suno_title", ""),
                     row.get("tags", ""), row.get("persona", ""))).lower()
    result = []
    korean = bool(re.search(r"[가-힣]", text)) or "k-pop" in text or "korean" in text
    japanese = bool(re.search(r"[ぁ-ゟ゠-ヿ一-龯]", text)) or "japanese" in text or "j-pop" in text
    french = any(value in text for value in (
        "french", "chanson", "amour", "coeur", "cœur", "paris", "doucement",
        "avec toi", "mon ", "reste ", "nuit", "soleil", "jardin",
    ))
    instrumental = row.get("make_instrumental") is True or any(value in text for value in (
        "instrumental", "jazz quartet", "solo grand piano", "piano trio",
        "vibraphone", "cafe jazz", "coffee shop",
    ))
    if korean and not instrumental:
        result.append("kpop")
    if (french or japanese) and not instrumental:
        result.append("globalmusic")
    if instrumental and any(value in text for value in (
        "jazz", "piano", "vibraphone", "bossa", "cafe", "coffee", "lobby",
    )):
        result.append("starbucks")
    return result


def build(root: Path, workers: int) -> dict:
    paths = sorted(
        (path for path in root.iterdir() if path.is_file()
         and path.suffix.lower() in {".mp3", ".wav"}),
        key=lambda path: path.name.casefold(),
    )
    hashed: dict[str, dict] = {}
    for path in paths:
        digest = _sha256(path)
        row = hashed.setdefault(digest, {
            "file": path.name,
            "sha256": digest,
            "duplicates": [],
            "suno_id": _suno_id(path),
        })
        if row["file"] != path.name:
            row["duplicates"].append(path.name)

    by_id: dict[str, dict] = {}
    ids = sorted({row["suno_id"] for row in hashed.values() if row["suno_id"]})
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_metadata, song_id): song_id for song_id in ids}
        for future in as_completed(futures):
            song_id = futures[future]
            try:
                by_id[song_id] = future.result()
            except Exception as exc:  # keep inventory useful when one page is transiently unavailable
                by_id[song_id] = {
                    "suno_url": f"https://suno.com/song/{song_id}",
                    "metadata_status": "unavailable",
                    "metadata_error": f"{type(exc).__name__}: {str(exc)[:180]}",
                }

    rows = []
    for row in hashed.values():
        row.update(by_id.get(row["suno_id"], {}))
        row["duration_seconds"] = _duration(root / row["file"])
        row["suggested_channels"] = _suggestions(row)
        rows.append(row)
    rows.sort(key=lambda row: row["file"].casefold())
    return {
        "version": 1,
        "source": str(root),
        "rights_basis": "owner_confirmed_paid_suno_downloads_2026-10-01",
        "approval_status": "suggestions_only_pending_channel_manifest_selection",
        "file_count": len(paths),
        "unique_audio_count": len(rows),
        "unique_suno_id_count": len(ids),
        "tracks": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    catalog = build(args.root.resolve(), max(1, min(args.workers, 16)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "file_count": catalog["file_count"],
        "unique_audio_count": catalog["unique_audio_count"],
        "unique_suno_id_count": catalog["unique_suno_id_count"],
        "suggested_counts": {
            channel: sum(channel in row["suggested_channels"] for row in catalog["tracks"])
            for channel in ("globalmusic", "kpop", "starbucks")
        },
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
