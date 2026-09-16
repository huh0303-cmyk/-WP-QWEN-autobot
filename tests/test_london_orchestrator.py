import json

from control_center import london_activity, london_orchestrator, orchestrator


def _isolated(monkeypatch, tmp_path):
    db = tmp_path / "london.sqlite3"
    monkeypatch.setenv("LONDON_ACTIVITY_DB", str(db))
    monkeypatch.setenv("ORCHESTRATOR_STATE_DB", str(db))
    monkeypatch.setenv("CONTROL_OPERATIONS_DB", str(db))
    monkeypatch.setenv("LONDON_ACTIVITY_JSONL", str(tmp_path / "activity.jsonl"))
    monkeypatch.setenv("ORCHESTRATOR_COOLDOWN_SECONDS", "30")
    return db


def test_openai_failure_falls_to_claude_and_records_failover(monkeypatch, tmp_path):
    _isolated(monkeypatch, tmp_path)

    def fail(model, prompt):
        raise orchestrator.ProviderUnavailable("quota exhausted")

    def claude_ok(model, prompt):
        return json.dumps({
            "status": "READY_FOR_AUDIT",
            "summary": "continued under Plan B",
            "next_actions": [],
            "assignments": [],
            "risks": [],
            "needs_human_approval": False,
            "completion_evidence_required": ["external proof"],
        })

    monkeypatch.setitem(orchestrator.CALLERS, "openai", fail)
    monkeypatch.setitem(orchestrator.CALLERS, "anthropic", claude_ok)
    task_id = london_orchestrator.submit_task("PM failover", "prove Plan B")
    result = london_orchestrator.run_task(task_id)
    assert result["active_pm"] == "claude"
    assert result["state"] == "READY_FOR_AUDIT"
    events = london_activity.get_task(task_id)["events"]
    assert any(row["event_type"] == "FAILOVER" for row in events)
    assert any(row["event_type"] == "ATTEMPT" and row["success"] == 0 for row in events)


def test_all_providers_failed_enters_safe_hold(monkeypatch, tmp_path):
    _isolated(monkeypatch, tmp_path)

    def fail(model, prompt):
        raise orchestrator.ProviderUnavailable("provider unavailable")

    for name in orchestrator.CALLERS:
        monkeypatch.setitem(orchestrator.CALLERS, name, fail)
    task_id = london_orchestrator.submit_task("All down", "prove SAFE HOLD")
    result = london_orchestrator.run_task(task_id)
    assert result["active_pm"] == "safe_hold"
    assert london_activity.get_task(task_id)["task"]["state"] == "BLOCKED"


def test_publication_mirror_task_is_not_sent_to_llm(monkeypatch, tmp_path):
    _isolated(monkeypatch, tmp_path)
    london_activity.create_task(
        "publication mirror",
        requested_by="operations",
        assigned_role="vps/github",
        payload={"pm_managed": False},
    )
    assert london_orchestrator.next_work_task_id() == ""
