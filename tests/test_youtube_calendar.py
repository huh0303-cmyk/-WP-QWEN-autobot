import datetime as dt
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from automation_hub.youtube_calendar import KST, READY, channel_key, parse_calendar, select_due
from scripts.youtube_calendar_result import private_result, main as result_main
from scripts.roll_14day_content_calendar import HEADERS, wp_blogger_rows, youtube_rows
from automation_hub.youtube_registry import load_channels


def row(sid="CAL-1", name="MBB", when="2026-08-31 12:00 KST", status=READY, platform="YouTube Playlist"):
    return [sid, when, platform, name, "YouTube channel", "en", "keyword", "Exact calendar topic",
            "format", "source", "dependency", "gate", status, "", "notes"]


def parsed(*rows):
    return parse_calendar([HEADERS, *rows])


NOW = dt.datetime(2026, 8, 31, 12, tzinfo=KST)


def test_aliases_and_future_time():
    assert channel_key("MBB") == channel_key("플리-MBB") == "mbb"
    selected, _ = select_due(parsed(row(), row("CAL-2", "Healing", "2026-08-31 14:00 KST")), NOW, {"mbb", "healing"})
    assert [r["id"] for r in selected] == ["CAL-1"]
    assert selected[0]["topic"] == "Exact calendar topic"


def test_original_series_blocks_rolled_alias_even_on_different_day():
    selected, skipped = select_due(parsed(row("CAL-1", when="2026-09-02 12:00 KST"), row("ROLL-X", "플리-MBB")), NOW, {"mbb"})
    assert not selected
    assert skipped == [("ROLL-X", "original-calendar-series-exists")]


@pytest.mark.parametrize("status", ["자료수집", "실패", "비공개 업로드", "보류", "공개완료"])
def test_no_retry_or_duplicate_after_claim(status):
    selected, _ = select_due(parsed(row(status=status), row("CAL-2", "플리-MBB")), NOW, {"mbb"})
    assert not selected


def test_disabled_old_or_url_rows_do_not_dispatch():
    assert not select_due(parsed(row()), NOW, set())[0]
    assert not select_due(parsed(row(when="2026-08-30 12:00 KST")), NOW, {"mbb"})[0]
    r = row(); r[13] = "https://studio.youtube.com/video/abcdefghijk/edit"
    assert not select_due(parsed(r), NOW, {"mbb"})[0]


def test_unknown_channels_duplicate_ids_and_wrong_platform_fail_closed():
    for rows in [(row(name="English Survival"),), (row(), row()), (row(platform="YouTube Knowledge"),)]:
        with pytest.raises(ValueError):
            parsed(*rows)


def test_chronological_limit():
    selected, _ = select_due(parsed(row(), row("CAL-2", "Healing", "2026-08-31 12:00 KST")), NOW, {"mbb", "healing"}, 1)
    assert selected[0]["key"] == "mbb"


def test_private_result_requires_identity_and_private(tmp_path):
    path = tmp_path / "result.json"
    data = {"video_id": "abcdefghijk", "privacy_status": "private", "public_allowed": False,
            "channel_key": "mbb", "verified_channel_id": next(c.channel_id for c in load_channels() if c.channel_key == "mbb")}
    path.write_text(json.dumps(data))
    assert private_result(path, "mbb")[0].endswith("/abcdefghijk/edit")
    data["privacy_status"] = "public"; path.write_text(json.dumps(data))
    assert not private_result(path, "mbb")[0]
    assert not private_result(tmp_path / "missing", "mbb")[0]


def test_roll_does_not_duplicate_blogger_rows():
    first = wp_blogger_rows(NOW.date(), set())
    keys = {f"{r[1][:10]}|{r[2]}|{r[3]}" for r in first}
    assert len(first) == 54
    assert wp_blogger_rows(NOW.date(), keys) == []


def test_roll_recognizes_existing_legacy_youtube_alias():
    c = next(c for c in load_channels() if c.channel_key == "mbb")
    assert youtube_rows(dt.date(2026, 9, 13), [row(when="2026-09-13 12:00 KST")], [c.__dict__ if hasattr(c, "__dict__") else {"display_name": c.display_name, "channel_key": c.channel_key}]) == []


def test_repeated_upload_claim_cannot_upload(monkeypatch):
    monkeypatch.setenv("SCHEDULE_ID", "CAL-1"); monkeypatch.setenv("CLAIM_TOKEN", "token")
    monkeypatch.setenv("SHEET_ID", "sheet"); monkeypatch.setenv("CHANNEL_KEY", "mbb")
    monkeypatch.setenv("GITHUB_RUN_ID", "123"); monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    r = parsed(row(status="자료수집"))[0]
    r["notes"] = "[yt-calendar:CAL-1:token] [yt-worker:123] [yt-upload:123]"
    with patch("scripts.youtube_calendar_result.get_sheets_service"), patch("scripts.youtube_calendar_result.read_calendar", return_value=[r]), patch.object(sys, "argv", ["result", "upload-start"]):
        with pytest.raises(RuntimeError, match="already attempted"):
            result_main()


def test_active_workflows_keep_non_calendar_routes_locked():
    for name in ["generate-youtube-playlist.yml", "curio-longform-daily.yml"]:
        text = (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")
        assert "inputs.schedule_id != '' && inputs.claim_token != ''" in text
        assert "youtube_calendar_result.py upload-start" in text
        assert "youtube_calendar_result.py finish" in text
    for name in ["topik-quiz-daily.yml", "curio-scheduler.yml", "daily_multilang_quiz.yml"]:
        assert "if: ${{ false }}" in (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")


def test_dispatch_claims_before_http_and_forwards_calendar(monkeypatch):
    from scripts import youtube_calendar_dispatch as dispatch_module
    monkeypatch.setenv("SHEET_ID", "sheet"); monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GH_DISPATCH_TOKEN", "test-token"); monkeypatch.setenv("DRY_RUN", "false")
    c = next(c for c in load_channels() if c.channel_key == "mbb")
    values = [["channel_key", "channel_type", "display_name", "channel_id", "secret_profile", "workflow", "enabled"],
              [c.channel_key, c.channel_type, c.display_name, c.channel_id, c.secret_profile, c.workflow, "ON"]]
    service = Mock(); service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {"values": values}
    r = parsed(row(when=dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")))[0]
    events = []
    def claim(*args):
        events.append("claim")
        assert args[3] == "자료수집"
    def post(*args, **kwargs):
        events.append("post")
        inputs = kwargs["json"]["inputs"]
        assert inputs["topic"] == "Exact calendar topic"
        assert inputs["schedule_id"] == "CAL-1"
        assert inputs["publish_delay_hours"] == ""
        assert inputs["claim_token"]
        return Mock()
    with patch.object(dispatch_module, "get_sheets_service", return_value=service), patch.object(dispatch_module, "read_calendar", return_value=[r]), patch.object(dispatch_module, "update_row", side_effect=claim), patch.object(dispatch_module.requests, "post", side_effect=post):
        assert dispatch_module.main() == 0
    assert events == ["claim", "post"]


def test_dry_run_has_no_writes_or_dispatch(monkeypatch):
    from scripts import youtube_calendar_dispatch as dispatch_module
    monkeypatch.setenv("SHEET_ID", "sheet"); monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("DRY_RUN", "true")
    service = Mock(); service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {"values": [
        ["channel_key", "channel_type", "display_name", "channel_id", "secret_profile", "workflow", "enabled"]]}
    with patch.object(dispatch_module, "get_sheets_service", return_value=service), patch.object(dispatch_module, "read_calendar", return_value=[]), patch.object(dispatch_module, "update_row") as write, patch.object(dispatch_module.requests, "post") as post:
        assert dispatch_module.main() == 0
    write.assert_not_called(); post.assert_not_called()


def test_private_email_has_editor_link_and_is_not_marked_on_failure():
    from scripts.youtube_calendar_result import notify_review
    r = parsed(row())[0]
    url = "https://studio.youtube.com/video/abcdefghijk/edit"
    with patch("scripts.publishing_completion_notify.send_email", return_value=False), patch("scripts.youtube_calendar_result.update_row") as write:
        with pytest.raises(RuntimeError, match="email was not sent"):
            notify_review(Mock(), "sheet", r, url, "")
        write.assert_not_called()
    with patch("scripts.publishing_completion_notify.send_email", return_value=True) as send, patch("scripts.youtube_calendar_result.update_row") as write:
        notify_review(Mock(), "sheet", r, url, "")
        assert url in send.call_args.args[1]
        assert "[review-email-sent:CAL-1]" in write.call_args.args[-1]
        send.reset_mock()
        notify_review(Mock(), "sheet", r, url, "[review-email-sent:CAL-1]")
        send.assert_not_called()
