#!/usr/bin/env python3
"""Stage an explicitly reviewed subset of the private Suno catalog.

The selection and resulting manifest contain private local filenames and stay
outside Git.  This command validates hashes and channel metadata before copying
only the allowlisted audio into a VPS-ready folder.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil


GENRE = {
    "globalmusic": "romantic_acoustic",
    "kpop": "korean_acoustic_pop",
}


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def stage(catalog_path: Path, selection_path: Path, source_root: Path,
          output_root: Path) -> dict:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    if catalog.get("version") != 1 or selection.get("version") != 1:
        raise RuntimeError("unsupported private catalog or selection version")
    by_name = {row["file"]: row for row in catalog.get("tracks", [])}
    if len(by_name) != len(catalog.get("tracks", [])):
        raise RuntimeError("catalog file names are not unique")

    audio_root = output_root / "audio"
    audio_root.mkdir(parents=True, exist_ok=True)
    manifest_rows, seen_hashes = [], set()
    language_counts = {"french": 0, "japanese": 0}
    totals = {channel: 0.0 for channel in GENRE}
    for chosen in selection.get("tracks", []):
        channel = chosen.get("channel")
        if channel not in GENRE:
            raise RuntimeError(f"unsupported selected channel: {channel}")
        name = chosen.get("file", "")
        if Path(name).name != name or name not in by_name:
            raise RuntimeError(f"unsafe or missing catalog file: {name}")
        row = by_name[name]
        digest = row.get("sha256", "")
        if digest in seen_hashes:
            raise RuntimeError(f"duplicate selected recording: {name}")
        source = (source_root / name).resolve()
        if source.parent != source_root.resolve() or not source.is_file():
            raise RuntimeError(f"selected source is missing: {name}")
        if _digest(source) != digest:
            raise RuntimeError(f"selected source hash changed: {name}")
        language = chosen.get("language", "")
        if channel == "globalmusic":
            if language not in language_counts:
                raise RuntimeError(f"invalid romantic language: {name}")
            language_counts[language] += 1
        elif language != "korean":
            raise RuntimeError(f"invalid K-pop language: {name}")
        review_basis = chosen.get("review_basis", "").strip()
        if not review_basis:
            raise RuntimeError(f"missing review basis: {name}")
        shutil.copy2(source, audio_root / name)
        duration = float(row["duration_seconds"])
        totals[channel] += duration
        manifest_rows.append({
            "channel": channel,
            "file": name,
            "sha256": digest,
            "approved": True,
            "genre": GENRE[channel],
            "language": language,
            "rights": "owner_paid_suno",
            "duration_seconds": duration,
            "review_basis": review_basis,
            "suno_id": row.get("suno_id"),
        })
        seen_hashes.add(digest)

    if language_counts["french"] != language_counts["japanese"]:
        raise RuntimeError(f"romantic language counts are not equal: {language_counts}")
    for channel, seconds in totals.items():
        if not 50 * 60 <= seconds <= 70 * 60:
            raise RuntimeError(f"{channel} reviewed total is {seconds / 60:.1f} min")
    manifest = {
        "version": 1,
        "rights_basis": "owner_confirmed_paid_suno_downloads_2026-10-01",
        "language_counts": language_counts,
        "channel_minutes": {key: round(value / 60, 2) for key, value in totals.items()},
        "tracks": manifest_rows,
    }
    (output_root / "approved.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    result = stage(args.catalog, args.selection, args.source_root.resolve(),
                   args.output_root.resolve())
    print(json.dumps({
        "approved_track_count": len(result["tracks"]),
        "language_counts": result["language_counts"],
        "channel_minutes": result["channel_minutes"],
        "output_root": str(args.output_root.resolve()),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
