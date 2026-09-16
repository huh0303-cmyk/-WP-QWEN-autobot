import json
import os
import runpy
import sqlite3
from pathlib import Path


def test_activity_report_keeps_success_and_failure(monkeypatch, tmp_path):
    db_path = tmp_path / "control.sqlite3"
    out_json = tmp_path / "report.json"
    out_md = tmp_path / "report.md"
    db = sqlite3.connect(db_path)
    db.executescript("""
        CREATE TABLE london_tasks (
            task_id TEXT PRIMARY KEY, parent_task_id TEXT, correlation_id TEXT, title TEXT,
            platform TEXT, target TEXT, requested_by TEXT, assigned_role TEXT, state TEXT,
            acceptance_criteria TEXT, payload TEXT, result TEXT, evidence TEXT, error TEXT,
            retry_count INTEGER, created REAL, updated REAL, started REAL, finished REAL
        );
        CREATE TABLE london_events (
            event_id INTEGER PRIMARY KEY, task_id TEXT, correlation_id TEXT, actor TEXT,
            event_type TEXT, from_state TEXT, to_state TEXT, detail TEXT, evidence TEXT,
            success INTEGER, created REAL
        );
    """)
    base = ("", "", "t", "wordpress", "x", "u", "codex", "[]", "{}", "{}", "[]", "", 0, 1.0, 2.0, 1.0, 2.0)
    db.execute("INSERT INTO london_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("ok",) + base[:7] + ("VERIFIED_COMPLETE",) + base[7:])
    db.execute("INSERT INTO london_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", ("bad",) + base[:7] + ("FAILED",) + base[7:])
    db.commit()
    db.close()

    monkeypatch.setenv("CONTROL_OPERATIONS_DB", str(db_path))
    monkeypatch.setenv("LONDON_ACTIVITY_REPORT_JSON", str(out_json))
    monkeypatch.setenv("LONDON_ACTIVITY_REPORT_MD", str(out_md))
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts" / "london_project_activity_report.py"), run_name="__main__")
    report = json.loads(out_json.read_text(encoding="utf-8"))
    assert report["state_counts"]["VERIFIED_COMPLETE"] == 1
    assert report["state_counts"]["FAILED"] == 1
    assert "FAILED: 1" in out_md.read_text(encoding="utf-8")
