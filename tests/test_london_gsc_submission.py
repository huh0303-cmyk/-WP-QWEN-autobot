from __future__ import annotations

from scripts import london_gsc_dispatch as dispatch
from scripts import london_four_agent_pipeline as pipeline


def test_dispatch_only_public_and_only_once(monkeypatch):
    calls = []
    monkeypatch.setenv("GH_TOKEN", "test-token")
    monkeypatch.setattr(dispatch.requests, "post", lambda *a, **kw: calls.append(kw) or type("R", (), {"status_code": 204})())
    state = {"run_id": "lgpt-20260928-120000-abcdef", "site_id": "wp_test",
             "receipt": {"status": "draft", "url": "https://example.com/post/"}}
    assert dispatch.queue_submission(state, "https://example.com")["status"] == "failed"
    assert not calls
    state["receipt"]["status"] = "published"
    assert dispatch.queue_submission(state, "https://example.com")["status"] == "queued"
    assert dispatch.queue_submission(state, "https://example.com")["status"] == "queued"
    assert len(calls) == 1


def test_published_rerun_uses_existing_receipt(monkeypatch, tmp_path):
    monkeypatch.setattr(pipeline, "STATE_DIR", tmp_path)
    run_id = "lgpt-20260928-120000-abcdef"
    pipeline._write_state({"run_id": run_id, "site_id": "wp_test", "publish_mode": "publish",
                           "stage_status": {"publish": "ok"},
                           "receipt": {"status": "published", "post_id": "123", "url": "https://example.com/post/"}})
    monkeypatch.setattr(pipeline, "_publish_wordpress_via_worker", lambda *a: (_ for _ in ()).throw(AssertionError("duplicate")))
    assert pipeline.stage_publish(run_id)["post_id"] == "123"
