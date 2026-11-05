import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation_hub.youtube_github_runtime import free_only_channel_allowed


def _set_mozart_free_env(monkeypatch):
    values = {
        "PLAYLIST_FREE_ONLY_CHANNEL": "mbb",
        "PLAYLIST_MUSIC_SOURCE": "approved_bank",
        "PLAYLIST_IMAGE_SOURCE": "pexels_api",
        "PLAYLIST_PAID_API_ENABLED": "false",
        "AUTO_TOPIC": "false",
        "GOOGLE_OAUTH_CLIENT_ID": "google-client",
        "GOOGLE_OAUTH_CLIENT_SECRET": "google-secret",
        "GOOGLE_OAUTH_REFRESH_TOKEN": "google-refresh",
        "MUSIC_SOURCE_FOLDER_ID_MBB": "music-folder",
        "THUMBNAIL_FOLDER_ID_MBB": "thumbnail-folder",
        "PEXELS_API_KEY": "pexels-free-key",
        "YOUTUBE_OAUTH_CLIENT_ID_MBB": "youtube-client",
        "YOUTUBE_OAUTH_CLIENT_SECRET_MBB": "youtube-secret",
        "YOUTUBE_OAUTH_REFRESH_TOKEN_MBB": "youtube-refresh",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    for key in ("GEMINI_API_KEY", "OPENAI_API_KEY", "LYRIA_API_KEY"):
        monkeypatch.delenv(key, raising=False)


def test_mozart_free_only_exception_requires_all_free_sources_and_channel_credentials(monkeypatch):
    _set_mozart_free_env(monkeypatch)
    assert free_only_channel_allowed("mbb")


def test_mozart_free_only_exception_rejects_paid_generation_keys(monkeypatch):
    _set_mozart_free_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "must-not-be-used")
    assert not free_only_channel_allowed("mbb")


def test_mozart_free_only_exception_rejects_wrong_channel_or_music_source(monkeypatch):
    _set_mozart_free_env(monkeypatch)
    assert not free_only_channel_allowed("globalmusic")
    monkeypatch.setenv("PLAYLIST_MUSIC_SOURCE", "owner_local")
    assert not free_only_channel_allowed("mbb")


def test_mozart_free_only_exception_requires_fresh_free_thumbnail_provider(monkeypatch):
    _set_mozart_free_env(monkeypatch)
    monkeypatch.delenv("PEXELS_API_KEY")
    assert not free_only_channel_allowed("mbb")
