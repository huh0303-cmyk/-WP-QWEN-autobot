import hashlib
import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from playlist_owner_library import select_owner_tracks


def make_library(tmp_path, channel="kpop", count=30):
    root = tmp_path / "audio"
    root.mkdir()
    rows = []
    for index in range(count):
        name = f"track-{index:02d}.mp3"
        content = f"unique audio {index}".encode()
        (root / name).write_bytes(content)
        rows.append({"file": name, "sha256": hashlib.sha256(content).hexdigest(),
                     "channel": channel, "approved": True,
                     "genre": "korean_acoustic_pop" if channel == "kpop" else "romantic_acoustic",
                     "language": ("french", "japanese")[index % 2],
                     "rights": "owner_paid_suno"})
    manifest = tmp_path / "approved.json"
    manifest.write_text(json.dumps({"version": 1, "tracks": rows}), encoding="utf-8")
    return root, manifest, rows


def test_shuffled_mix_varies_length_and_never_repeats_hash(tmp_path):
    root, manifest, _ = make_library(tmp_path)
    duration = lambda path: 170 + int(Path(path).stem[-2:]) % 6 * 10
    first = select_owner_tracks("kpop", root, manifest, duration, random.Random(1))
    second = select_owner_tracks("kpop", root, manifest, duration, random.Random(2))
    assert 3000 <= sum(x["duration"] for x in first) <= 4200
    assert 3000 <= sum(x["duration"] for x in second) <= 4200
    assert len({x["sha256"] for x in first}) == len(first)
    assert [x["sha256"] for x in first] != [x["sha256"] for x in second]


def test_romantic_mix_keeps_french_and_japanese_balanced(tmp_path):
    root, manifest, _ = make_library(tmp_path, "globalmusic", 32)
    chosen = select_owner_tracks("globalmusic", root, manifest,
                                 lambda _: 180, random.Random(3))
    counts = {lang: sum(x["language"] == lang for x in chosen)
              for lang in ("french", "japanese")}
    assert len(set(counts.values())) == 1
    assert 3000 <= sum(x["duration"] for x in chosen) <= 4200


def test_changed_audio_and_unreviewed_genre_fail_closed(tmp_path):
    root, manifest, rows = make_library(tmp_path, count=17)
    rows[0]["genre"] = "unknown"
    manifest.write_text(json.dumps({"version": 1, "tracks": rows}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="WAITING_OWNER_LIBRARY"):
        select_owner_tracks("kpop", root, manifest, lambda _: 180, random.Random(3))
    rows[0]["genre"] = "korean_acoustic_pop"
    manifest.write_text(json.dumps({"version": 1, "tracks": rows}), encoding="utf-8")
    (root / rows[0]["file"]).write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="audio hash changed"):
        select_owner_tracks("kpop", root, manifest, lambda _: 180, random.Random(3))
