"""Select reviewed owner audio for one playlist without repeats or guessed genres.

The private manifest and audio files stay outside Git. A manifest row must name
one channel, one reviewed genre and its exact SHA-256. This module never scans
the desktop for a random unreviewed replacement.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Callable


GENRE_BY_CHANNEL = {
    "globalmusic": "romantic_acoustic",
    "kpop": "korean_acoustic_pop",
    "starbucks": "instrumental_cafe",
}
ROMANTIC_LANGUAGES = ("french", "japanese")
MIN_SECONDS = 50 * 60
MAX_SECONDS = 70 * 60


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _verified_rows(channel: str, root: Path, manifest: Path,
                   duration_fn: Callable[[str], float]) -> list[dict]:
    if channel not in GENRE_BY_CHANNEL:
        raise RuntimeError(f"WAITING_OWNER_LIBRARY: no reviewed local genre for {channel}")
    if not manifest.is_file():
        raise RuntimeError("WAITING_OWNER_LIBRARY: private reviewed manifest is missing")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("tracks"), list):
        raise RuntimeError("WAITING_OWNER_LIBRARY: unsupported reviewed manifest")
    root = root.resolve()
    rows, seen = [], set()
    for entry in data["tracks"]:
        if entry.get("channel") != channel or entry.get("approved") is not True:
            continue
        if entry.get("genre") != GENRE_BY_CHANNEL[channel]:
            continue
        if entry.get("rights") not in {"owner_paid_suno", "verified_commercial_export"}:
            continue
        if (entry["rights"] == "verified_commercial_export"
                and not entry.get("rights_evidence")):
            continue
        relative = entry.get("file", "")
        if not isinstance(relative, str) or Path(relative).name != relative:
            raise RuntimeError("WAITING_OWNER_LIBRARY: unsafe audio file name")
        path = (root / relative).resolve()
        if path.parent != root or not path.is_file() or path.suffix.lower() not in {".mp3", ".wav"}:
            raise RuntimeError(f"WAITING_OWNER_LIBRARY: reviewed audio missing: {relative}")
        digest = _digest(path)
        if digest != entry.get("sha256", "").lower():
            raise RuntimeError(f"WAITING_OWNER_LIBRARY: audio hash changed: {relative}")
        if digest in seen:
            continue
        seconds = float(duration_fn(str(path)))
        if not 30 <= seconds <= 12 * 60:
            raise RuntimeError(f"WAITING_OWNER_LIBRARY: invalid audio duration: {relative}")
        language = entry.get("language", "")
        if channel == "globalmusic" and language not in ROMANTIC_LANGUAGES:
            continue
        rows.append({"path": str(path), "sha256": digest, "name": path.name,
                     "duration": seconds, "language": language,
                     "rights": entry["rights"], "genre": entry["genre"]})
        seen.add(digest)
    return rows


def select_owner_tracks(channel: str, root: Path, manifest: Path,
                        duration_fn: Callable[[str], float],
                        rng: random.Random | None = None) -> list[dict]:
    """Return a shuffled, genre-reviewed mix of 50–70 minutes, or fail closed."""
    rng = rng or random.Random()
    rows = _verified_rows(channel, root, manifest, duration_fn)
    target = rng.randint(MIN_SECONDS, MAX_SECONDS)
    if channel == "globalmusic":
        groups = {lang: [r for r in rows if r["language"] == lang]
                  for lang in ROMANTIC_LANGUAGES}
        for group in groups.values():
            rng.shuffle(group)
        ordered = []
        while all(groups.values()):
            languages = list(ROMANTIC_LANGUAGES)
            rng.shuffle(languages)
            ordered.extend(groups[lang].pop() for lang in languages)
    else:
        ordered = list(rows)
        rng.shuffle(ordered)
    selected, total = [], 0.0
    blocks = ([ordered[i:i + 2] for i in range(0, len(ordered), 2)]
              if channel == "globalmusic" else [[row] for row in ordered])
    for block in blocks:
        block_seconds = sum(row["duration"] for row in block)
        if total + block_seconds > MAX_SECONDS:
            continue
        selected.extend(block)
        total += block_seconds
        if total >= target and total >= MIN_SECONDS:
            break
    if total < MIN_SECONDS:
        raise RuntimeError(f"WAITING_OWNER_LIBRARY: reviewed {channel} audio totals only {total / 60:.1f} min")
    return selected
