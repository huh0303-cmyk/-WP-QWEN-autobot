import json

import pytest

from control_center import london_activity


def _isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("LONDON_ACTIVITY_DB", str(tmp_path / "activity.sqlite3"))
    monkeypatch.setenv("LONDON_ACTIVITY_JSONL", str(tmp_path / "activity.jsonl"))


def test_every_task_gets_request_and_attempt_history(monkeypatch, tmp_path):
    _isolated(monkeypatch, tmp_path)
    task_id = london_activity.create_task(
        "test task", platform="wordpress", target="example.com", assigned_role="codex"
    )
    london_activity.transition(task_id, "RUNNING", actor="codex")
    london_activity.record_attempt(
        task_id, actor="codex", provider="openai", action="draft", success=False, error="quota"
    )
    london_activity.record_failover(task_id, from_role="codex", to_role="claude", reason="quota")
    snapshot = london_activity.get_task(task_id)
    event_types = [row["event_type"] for row in snapshot["events"]]
    assert event_types == ["TASK_CREATED", "STATE_CHANGED", "ATTEMPT", "ASSIGNMENT_CHANGED", "FAILOVER"]
    assert snapshot["task"]["retry_count"] == 1
    assert snapshot["task"]["assigned_role"] == "claude"

    records = [json.loads(line) for line in (tmp_path / "activity.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [row["event_type"] for row in records] == event_types


def test_ai_cannot_self_certify_verified_complete(monkeypatch, tmp_path):
    _isolated(monkeypatch, tmp_path)
    task_id = london_activity.create_task("verify me")
    with pytest.raises(PermissionError):
        london_activity.transition(task_id, "VERIFIED_COMPLETE", actor="codex")


def test_private_review_and_human_approval_are_recorded(monkeypatch, tmp_path):
    _isolated(monkeypatch, tmp_path)
    task_id = london_activity.create_task("private video", platform="youtube", target="channel-x")
    evidence = [{"video_id": "abcdefghijk", "channel_id": "channel-x", "privacy_status": "private"}]
    london_activity.record_audit_result(
        task_id, passed=True, evidence=evidence, verified_state="VERIFIED_PRIVATE"
    )
    london_activity.transition(task_id, "REVIEW_REQUIRED", actor="orchestrator")
    london_activity.record_human_approval(task_id, approved=True)

    snapshot = london_activity.get_task(task_id)
    assert snapshot["task"]["state"] == "REVIEW_REQUIRED"
    assert "AUDIT_RESULT" in [row["event_type"] for row in snapshot["events"]]
    assert "HUMAN_APPROVAL" in [row["event_type"] for row in snapshot["events"]]


def test_deterministic_audit_can_create_verified_complete(monkeypatch, tmp_path):
    _isolated(monkeypatch, tmp_path)
    task_id = london_activity.create_task("public article", platform="wordpress", target="example.com")
    evidence = [{"public_url": "https://example.com/post", "http_status": 200}]
    london_activity.record_audit_result(task_id, passed=True, evidence=evidence)
    assert london_activity.get_task(task_id)["task"]["state"] == "VERIFIED_COMPLETE"
