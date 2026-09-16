import json

from control_center import pm_orchestrator


def test_openai_is_primary_pm(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCHESTRATOR_STATE_DB", str(tmp_path / "pm.sqlite3"))
    monkeypatch.setattr(
        pm_orchestrator,
        "generate_text",
        lambda prompt, task_type="pm": (
            json.dumps({
                "status": "ready_for_audit",
                "summary": "implementation ready",
                "next_actions": [],
                "assignments": [],
                "risks": [],
                "needs_human_approval": False,
                "completion_evidence_required": ["external receipt"],
            }),
            {"provider": "openai", "model": "test", "attempts": []},
        ),
    )
    task_id = pm_orchestrator.submit_task("test", "test primary PM")
    result = pm_orchestrator.run_task(task_id)
    assert result["active_pm"] == "codex"
    assert result["decision"]["status"] == "ready_for_audit"


def test_claude_becomes_acting_pm(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCHESTRATOR_STATE_DB", str(tmp_path / "pm.sqlite3"))
    monkeypatch.setattr(
        pm_orchestrator,
        "generate_text",
        lambda prompt, task_type="pm": (
            json.dumps({
                "status": "review",
                "summary": "continued from handoff",
                "next_actions": ["continue existing task"],
                "assignments": [],
                "risks": [],
                "needs_human_approval": False,
                "completion_evidence_required": [],
            }),
            {"provider": "anthropic", "model": "test", "attempts": [{"provider": "openai", "result": "quota"}]},
        ),
    )
    task_id = pm_orchestrator.submit_task("test", "test Plan B")
    result = pm_orchestrator.run_task(task_id)
    assert result["active_pm"] == "claude"
    assert pm_orchestrator.status()["runtime"]["active_pm"] == "claude"


def test_pm_cannot_self_certify_verified_complete(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCHESTRATOR_STATE_DB", str(tmp_path / "pm.sqlite3"))
    monkeypatch.setattr(
        pm_orchestrator,
        "generate_text",
        lambda prompt, task_type="pm": (
            json.dumps({
                "status": "complete",
                "summary": "PM thinks it is complete",
                "next_actions": [],
                "assignments": [],
                "risks": [],
                "needs_human_approval": False,
                "completion_evidence_required": [],
            }),
            {"provider": "openai", "model": "test", "attempts": []},
        ),
    )
    task_id = pm_orchestrator.submit_task("test", "completion guard")
    pm_orchestrator.run_task(task_id)
    with pm_orchestrator._connect() as db:
        state = db.execute("SELECT state FROM pm_tasks WHERE task_id=?", (task_id,)).fetchone()[0]
    assert state != "verified_complete"
