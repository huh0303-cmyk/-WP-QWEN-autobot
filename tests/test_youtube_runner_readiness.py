import datetime as dt
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from automation_hub.sheet_schema import YOUTUBE_CHANNEL_HEADER
from automation_hub.youtube_calendar import KST, READY, next_calendar_run, select_passed
from automation_hub.youtube_identity import verify_authenticated_channel
from automation_hub.youtube_readiness import (
    FORBIDDEN_MUTATION_SCOPES, UPLOAD_SCOPE, assert_access_scope, check_channel, credential_values,
    validate_sheet_registry,
)
from automation_hub.youtube_registry import load_channels
from scripts.youtube_calendar_result import private_result
from scripts.youtube_public_status_sync import is_public, review_video_id
from scripts import youtube_public_status_sync as public_sync


EXPECTED_KEYS = {
    "globalmusic", "healing", "starbucks", "mbb", "kpop",
    "nasa", "history", "invention", "silent_era", "retro_reels",
}


def parsed_row(key="mbb", when=None, status=READY, url="", notes=""):
    return {
        "id": "CAL-1", "key": key, "when": when or dt.datetime(2026, 9, 2, 12, tzinfo=KST),
        "status": status, "url": url, "notes": notes,
    }


def test_registry_is_the_exact_requested_ten_channels():
    channels = load_channels()
    assert {channel.channel_key for channel in channels} == EXPECTED_KEYS
    assert sum(channel.channel_type == "playlist" for channel in channels) == 5
    assert sum(channel.channel_type == "knowledge" for channel in channels) == 5


def test_sheet_registry_requires_exact_roster_identity_and_timezone():
    channels = load_channels()
    values = [YOUTUBE_CHANNEL_HEADER, *[channel.to_row() for channel in channels]]
    assert validate_sheet_registry(values, channels) == []
    broken = [list(row) for row in values]
    broken[1][15] = "2026-09-03T12:00:00"
    assert any("timezone" in error for error in validate_sheet_registry(broken, channels))
    assert any("roster mismatch" in error for error in validate_sheet_registry(values[:-1], channels))


def test_all_channel_readiness_never_reuses_global_refresh_token():
    channel = next(item for item in load_channels() if item.channel_key == "healing")
    env = {
        "YOUTUBE_OAUTH_CLIENT_ID": "client", "YOUTUBE_OAUTH_CLIENT_SECRET": "secret",
        "YOUTUBE_OAUTH_REFRESH_TOKEN": "wrong-global-token",
    }
    assert credential_values(channel, env, allow_runtime_alias=False)["refresh_token"] == ""
    assert credential_values(channel, env, allow_runtime_alias=True)["refresh_token"] == "wrong-global-token"


def test_readiness_requires_upload_scope_and_exact_readonly_identity():
    channel = next(item for item in load_channels() if item.channel_key == "mbb")
    env = {
        "YOUTUBE_OAUTH_CLIENT_ID": "client", "YOUTUBE_OAUTH_CLIENT_SECRET": "secret",
        "YOUTUBE_OAUTH_REFRESH_TOKEN": "refresh",
    }
    service = Mock()
    service.channels.return_value.list.return_value.execute.return_value = {"items": [{"id": channel.channel_id}]}
    with patch("automation_hub.youtube_readiness.verify_upload_scope") as upload_scope, patch(
        "automation_hub.youtube_readiness.build_youtube_service", return_value=service,
    ):
        result = check_channel(channel, env=env)
    upload_scope.assert_called_once()
    assert result.ready and result.upload_scope_ready and result.verified_channel_id == channel.channel_id


def test_upload_scope_verification_fails_closed_on_narrow_or_unverifiable_token():
    credentials = Mock(granted_scopes=["https://www.googleapis.com/auth/youtube.readonly"], token="access")
    with pytest.raises(RuntimeError, match="did not grant"):
        assert_access_scope(credentials, UPLOAD_SCOPE)
    credentials.granted_scopes = [UPLOAD_SCOPE, next(iter(FORBIDDEN_MUTATION_SCOPES))]
    with pytest.raises(RuntimeError, match="forbidden mutation scopes"):
        assert_access_scope(credentials, UPLOAD_SCOPE)
    credentials.granted_scopes = None
    with patch("requests.get", side_effect=TimeoutError):
        with pytest.raises(RuntimeError, match="Could not verify"):
            assert_access_scope(credentials, UPLOAD_SCOPE)
    response = Mock(status_code=200)
    response.json.return_value = {"scope": UPLOAD_SCOPE}
    with patch("requests.get", return_value=response):
        assert_access_scope(credentials, UPLOAD_SCOPE)


def test_identity_fails_closed_for_zero_wrong_or_multiple_channels():
    channel = next(item for item in load_channels() if item.channel_key == "nasa")
    for ids in ([], ["UC0000000000000000000000"], [channel.channel_id, "UC0000000000000000000000"]):
        service = Mock()
        service.channels.return_value.list.return_value.execute.return_value = {"items": [{"id": item} for item in ids]}
        with pytest.raises(RuntimeError, match="OAuth channel mismatch"):
            verify_authenticated_channel(service, channel.channel_key)


def test_past_window_becomes_pass_and_next_run_comes_from_calendar():
    now = dt.datetime(2026, 9, 2, 12, 30, tzinfo=KST)
    old = parsed_row(when=now - dt.timedelta(minutes=30))
    claimed = parsed_row(when=now - dt.timedelta(days=1), notes="[yt-calendar:CAL-X:token]")
    assert select_passed([old, claimed], now) == [old]
    future = parsed_row(when=now + dt.timedelta(days=2, minutes=17))
    later = parsed_row(when=now + dt.timedelta(days=3, minutes=9))
    assert next_calendar_run([later, future], "mbb", now) == future["when"]


def test_malformed_or_non_private_receipts_are_rejected(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    assert "unreadable" in private_result(bad, "mbb")[1]
    public = tmp_path / "public.json"
    public.write_text(json.dumps({"video_id": "abcdefghijk", "privacy_status": "public"}), encoding="utf-8")
    assert not private_result(public, "mbb")[0]


def test_public_transition_one_off_is_permanently_locked():
    workflow = (ROOT / ".github/workflows/_one-off-mbb-set-public-19.yml").read_text(encoding="utf-8")
    script = (ROOT / "scripts/_set_mbb_video_public_19.py").read_text(encoding="utf-8")
    schedule_patch = (ROOT / "scripts/_patch_publish_at.py").read_text(encoding="utf-8")
    assert "if: ${{ false }}" in workflow
    assert "privacyStatus" not in script and "videos().update" not in script
    assert "publishAt" not in schedule_patch and "videos().update" not in schedule_patch


def test_uploaders_require_private_unscheduled_api_receipt():
    playlist = (ROOT / "scripts/youtube_publish_approved.py").read_text(encoding="utf-8")
    knowledge = (ROOT / "scripts/curio_upload.py").read_text(encoding="utf-8")
    for source in (playlist, knowledge):
        assert 'response_status.get("privacyStatus") != "private"' in source
        assert 'response_status.get("publishAt")' in source
    assert "scopes=[UPLOAD_SCOPE]" in knowledge
    assert "assert_access_scope(creds, UPLOAD_SCOPE)" in knowledge
    assert "assert_access_scope(creds, UPLOAD_SCOPE)" in playlist
    assert "youtube.force-ssl" not in knowledge


@pytest.mark.parametrize("module_name", ["scripts.youtube_publish_approved", "scripts.curio_upload"])
def test_uploader_rejects_non_private_api_response(module_name, tmp_path):
    import importlib

    module = importlib.import_module(module_name)
    video = tmp_path / "video.mp4"
    video.write_bytes(b"test-video")

    def fake_service(response):
        request = Mock()
        request.next_chunk.return_value = (None, response)
        service = Mock()
        service.videos.return_value.insert.return_value = request
        return service

    private = {"id": "abcdefghijk", "status": {"privacyStatus": "private"}}
    assert module.upload_to_youtube(fake_service(private), str(video), "", "title", "description") == "abcdefghijk"
    public = {"id": "abcdefghijk", "status": {"privacyStatus": "public"}}
    with pytest.raises(RuntimeError, match="private unscheduled"):
        module.upload_to_youtube(fake_service(public), str(video), "", "title", "description")
    scheduled = {"id": "abcdefghijk", "status": {"privacyStatus": "private", "publishAt": "2026-09-03T00:00:00Z"}}
    with pytest.raises(RuntimeError, match="private unscheduled"):
        module.upload_to_youtube(fake_service(scheduled), str(video), "", "title", "description")


def test_readiness_workflow_covers_all_ten_profiles_and_sheet():
    text = (ROOT / ".github/workflows/youtube-readiness.yml").read_text(encoding="utf-8")
    for channel in load_channels():
        assert f"YOUTUBE_OAUTH_REFRESH_TOKEN_{channel.secret_profile}" in text
    assert "--all --sheet" in text
    assert "public_allowed" not in text


def test_human_publication_sync_is_read_only_and_records_only_confirmed_public():
    url = "https://studio.youtube.com/video/abcdefghijk/edit"
    assert review_video_id(url) == "abcdefghijk"
    assert review_video_id("https://youtube.com/watch?v=abcdefghijk") == ""
    service = Mock()
    channel_id = "UC0000000000000000000000"
    service.videos.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "abcdefghijk", "snippet": {"channelId": channel_id},
                   "status": {"privacyStatus": "public"}}],
    }
    assert is_public(service, "abcdefghijk", channel_id)
    assert not is_public(service, "abcdefghijk", "UC1111111111111111111111")
    source = (ROOT / "scripts/youtube_public_status_sync.py").read_text(encoding="utf-8")
    assert "videos().update" not in source
    assert "videos().insert" not in source
    workflow = (ROOT / ".github/workflows/youtube-public-status-sync.yml").read_text(encoding="utf-8")
    assert "youtube_public_status_sync.py" in workflow
    assert "contents: read" in workflow


def test_public_status_sync_isolates_one_broken_channel(monkeypatch):
    monkeypatch.setenv("SHEET_ID", "sheet")
    rows = [
        {"key": "mbb", "status": "비공개 업로드", "url": "https://studio.youtube.com/video/abcdefghijk/edit", "notes": ""},
        {"key": "nasa", "status": "비공개 업로드", "url": "https://studio.youtube.com/video/lmnopqrstuv/edit", "notes": ""},
    ]
    def build(channel, **_kwargs):
        if channel.channel_key == "mbb":
            raise RuntimeError("revoked")
        return Mock()
    with patch.object(public_sync, "get_sheets_service", return_value=Mock()), patch.object(
        public_sync, "read_calendar", return_value=rows,
    ), patch.object(public_sync, "build_youtube_service", side_effect=build), patch.object(
        public_sync, "verify_authenticated_channel",
    ), patch.object(public_sync, "is_public", return_value=True), patch.object(
        public_sync, "update_row",
    ) as update, patch.object(public_sync, "try_append_run_log", return_value=True) as log:
        assert public_sync.main() == 1
    assert update.call_count == 1
    assert update.call_args.args[2]["key"] == "nasa"
    assert {call.kwargs["status"] for call in log.call_args_list} == {"status_sync_failed", "public_confirmed"}
