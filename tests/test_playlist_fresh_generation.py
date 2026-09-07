from pathlib import Path
import sys

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import gemini_media_provider as provider
import youtube_playlist_maker as maker


def test_api_key_is_mandatory(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        provider._api_key()


def test_fresh_tracks_are_unique_and_never_drive_inputs(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(maker.base, "WORKDIR", str(tmp_path))
    monkeypatch.setattr(maker.base, "CHANNEL_KEY", "starbucks")
    monkeypatch.setenv("LYRIA_TRACK_COUNT", "20")
    monkeypatch.setenv("LYRIA_MAX_TRACKS", "20")
    monkeypatch.setenv("PLAYLIST_FRESH_AUDIO_SECONDS", "4200")

    def generate(prompt, path):
        calls.append(prompt)
        Path(path).write_bytes(b"audio")

    monkeypatch.setattr(maker, "generate_lyria_track", generate)
    monkeypatch.setattr(maker.base, "get_duration", lambda _path: 210.0)
    tracks = maker.generate_fresh_tracks()
    assert len(tracks) == 20
    assert len({track["id"] for track in tracks}) == 20
    assert len(set(calls)) == 20
    assert all(track["id"].startswith("fresh-lyria:") for track in tracks)


def test_thumbnail_is_generated_fresh_once(monkeypatch, tmp_path):
    calls = []

    def generate(prompt, path):
        calls.append(prompt)
        Image.new("RGB", (1920, 1080), "navy").save(path, format="PNG")

    monkeypatch.setattr(maker, "generate_thumbnail", generate)
    monkeypatch.setattr(maker.base, "CHANNEL_KEY", "healing")
    result = maker.fresh_image("Rainy forest", tmp_path)
    assert len(calls) == 1
    assert "no reproduction of an existing image" in calls[0]
    assert Path(result[0]).is_file()


def test_playlist_duration_and_metadata_policy(monkeypatch):
    assert maker.base.pick_duration_target() == (3000, 4200)
    assert all(value == (3000, 4200) for value in maker.base.HEALING_THEME_DURATION_SEC.values())
    monkeypatch.setattr(maker.base, "CHANNEL_KEY", "kpop")
    title, _description, _tags, fallback = maker.metadata("Tonight in Seoul", "", 60)
    assert "Original K-pop" in title
    assert fallback is False


def test_benchmark_thumbnail_uses_new_compact_type(monkeypatch, tmp_path):
    source = tmp_path / "source.png"
    output = tmp_path / "thumb.jpg"
    Image.new("RGB", (1920, 1080), "teal").save(source)
    result = maker.benchmark_thumbnail("starbucks", str(source), str(output), "Quiet Cafe")
    assert Path(result).is_file()
    with Image.open(result) as image:
        assert image.size == (1280, 720)


def test_intro_uses_local_ffmpeg_and_keeps_audio(monkeypatch):
    calls = []
    monkeypatch.setattr(maker.base, "run_ffmpeg", lambda command: calls.append(command))
    maker.make_intro_video("cover.png", "music.m4a", "video.mp4")
    assert calls[0][0] == "ffmpeg"
    assert "music.m4a" in calls[0]
    assert "-shortest" in calls[0]


def test_language_cycle_is_balanced():
    counts = {}
    for _ in range(40):
        chosen = maker.balanced_language(counts)
        counts[chosen] = counts.get(chosen, 0) + 1
    assert set(counts.values()) == {10}
