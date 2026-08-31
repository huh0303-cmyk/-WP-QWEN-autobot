import runpy
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


def test_calendar_overrides_cadence_and_claims_before_dispatch(monkeypatch, tmp_path):
    site = SimpleNamespace(url="https://example.com", content_type="news_en",
                           publish_mode="automatic", secret_name="TEST_WP")
    monkeypatch.setitem(sys.modules, "load_automation_hub_from_sheets",
                        SimpleNamespace(load_runtime_registry=lambda: SimpleNamespace(enabled=lambda _: [site])))
    monkeypatch.setenv("TEST_WP", "not-a-real-secret")
    monkeypatch.setenv("GH_DISPATCH_TOKEN", "test")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "out"))
    mod = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/publish_scheduler.py"))
    assert mod["TODAY_SITES"] == {site.url}
    header = ["schedule_id", "planned_at_kst", "platform", "channel_site", "destination_url",
              "language", "golden_keyword_candidate", "planned_title_direction", "content_format",
              "source_asset_plan", "dependency", "quality_gate", "current_status", "review_or_output_url", "notes"]
    row = ["CAL-test", mod["today"] + " 00:00 KST", "WordPress", "example", site.url,
           "en", "Exact sheet keyword", "", "", "", "", "", "황금키워드 검증대기", "", ""]
    service = Mock()
    service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {"values": [header, row]}
    assert len(mod["load_due_calendar_rows"](service)) == 1
    events = []
    service.spreadsheets.return_value.values.return_value.update.side_effect = lambda **kw: (events.append("claim") or Mock())
    monkeypatch.chdir(tmp_path)
    globals_ = mod["main"].__globals__
    monkeypatch.setitem(globals_, "get_sheets_service", lambda: service)
    def post(*args, **kwargs):
        events.append("dispatch")
        assert kwargs["json"]["inputs"]["publication_approved"] == "false"
        assert kwargs["json"]["inputs"]["force_keyword"] == "Exact sheet keyword"
        return SimpleNamespace(status_code=204)
    monkeypatch.setattr(globals_["requests"], "post", post)
    mod["main"]()
    assert events == ["claim", "dispatch"]
    mod["main"]()
    assert events == ["claim", "dispatch"]
    row[12] = "보류"
    assert mod["load_due_calendar_rows"](service) == []
