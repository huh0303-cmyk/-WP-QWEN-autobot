import runpy
from pathlib import Path
from unittest.mock import Mock
import pytest


@pytest.mark.parametrize("public", [False, True])
def test_only_exact_public_calendar_source_can_dispatch(monkeypatch, tmp_path, public):
    mod = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/blogger_daily_scheduler.py"))
    g = mod["main"].__globals__
    site = {"site_id": "blogger_test", "url": "https://test.blogspot.com", "keyword_rules": {"source_site_id": "wp_test"}}
    wp = {"wp_test": {"url": "https://example.com"}}
    monkeypatch.setitem(g, "load_sites", lambda: ([site], wp))
    monkeypatch.setitem(g, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setenv("SHEET_ID", "sheet")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GH_DISPATCH_TOKEN", "test")
    header = ["schedule_id", "planned_at_kst", "platform", "destination_url", "golden_keyword_candidate", "current_status", "review_or_output_url"]
    when = mod["TODAY"] + " 00:00 KST"
    values = [header, ["CAL-WP", when, "WordPress", "https://example.com", "same topic", "검수중", "https://example.com/wp-admin/post.php?post=42&action=edit"],
              ["CAL-B", when, "Blogger", site["url"], "same topic", "WP 선행대기", ""]]
    service = Mock()
    service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {"values": values}
    monkeypatch.setitem(g, "get_sheets_service", lambda: service)
    response = Mock()
    response.json.return_value = {"status": "publish" if public else "draft"}
    get = Mock(return_value=response)
    post = Mock(return_value=Mock(status_code=204))
    monkeypatch.setattr(g["requests"], "get", get)
    monkeypatch.setattr(g["requests"], "post", post)
    mod["main"]()
    assert get.call_args.args[0] == "https://example.com/wp-json/wp/v2/posts/42"
    if public:
        assert post.call_args.kwargs["json"]["inputs"]["source_wp_url"] == "https://example.com/?p=42"
        assert post.call_args.kwargs["json"]["inputs"]["publish_now"] == "false"
    else:
        post.assert_not_called()
        service.spreadsheets.return_value.values.return_value.update.assert_not_called()
