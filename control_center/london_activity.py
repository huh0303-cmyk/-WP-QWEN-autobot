from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

FINAL_VERIFIED_STATE = "VERIFIED_COMPLETE"
ALLOWED_STATES = {
    "REQUESTED", "PLANNED", "ASSIGNED", "RUNNING", "READY_FOR_AUDIT",
    "AUDITING", "VERIFIED_PRIVATE", "REVIEW_REQUIRED", "VERIFIED_COMPLETE",
    "REWORK_REQUIRED", "BLOCKED", "FAILED", "NEEDS_ATTENTION", "CANCELLED",
}


def _db_path() -> str:
    return (
        os.environ.get("LONDON_ACTIVITY_DB", "").strip()
        or os.environ.get("CONTROL_OPERATIONS_DB", "").strip()
        or str(ROOT / "data" / "control-operations.sqlite3")
    )


def _jsonl_path() -> Path:
    explicit = os.environ.get("LONDON_ACTIVITY_JSONL", "").strip()
    return Path(explicit) if explicit else ROOT / "data" / "london_project_activity.jsonl"


def _connect() -> sqlite3.Connection:
    path = Path(_db_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS london_tasks (
            task_id TEXT PRIMARY KEY,
            parent_task_id TEXT NOT NULL DEFAULT '',
            correlation_id TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            platform TEXT NOT NULL DEFAULT '',
            target TEXT NOT NULL DEFAULT '',
            requested_by TEXT NOT NULL DEFAULT 'chairman',
            assigned_role TEXT NOT NULL DEFAULT '',
            state TEXT NOT NULL DEFAULT 'REQUESTED',
            acceptance_criteria TEXT NOT NULL DEFAULT '[]',
            payload TEXT NOT NULL DEFAULT '{}',
            result TEXT NOT NULL DEFAULT '{}',
            evidence TEXT NOT NULL DEFAULT '[]',
            error TEXT NOT NULL DEFAULT '',
            retry_count INTEGER NOT NULL DEFAULT 0,
            created REAL NOT NULL,
            updated REAL NOT NULL,
            started REAL NOT NULL DEFAULT 0,
            finished REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS london_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            correlation_id TEXT NOT NULL DEFAULT '',
            actor TEXT NOT NULL,
            event_type TEXT NOT NULL,
            from_state TEXT NOT NULL DEFAULT '',
            to_state TEXT NOT NULL DEFAULT '',
            detail TEXT NOT NULL DEFAULT '{}',
            evidence TEXT NOT NULL DEFAULT '[]',
            success INTEGER,
            created REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_london_events_task ON london_events(task_id, event_id);
        CREATE INDEX IF NOT EXISTS idx_london_events_created ON london_events(created);
        """
    )
    return db


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _append_jsonl(record: dict[str, Any]) -> None:
    path = _jsonl_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = _dump(record) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())


def _event(*, task_id: str, correlation_id: str, actor: str, event_type: str,
           from_state: str = "", to_state: str = "", detail: dict[str, Any] | None = None,
           evidence: list[dict[str, Any]] | None = None, success: bool | None = None) -> int:
    now = time.time()
    detail = detail or {}
    evidence = evidence or []
    with _connect() as db:
        cur = db.execute(
            """INSERT INTO london_events(
                task_id,correlation_id,actor,event_type,from_state,to_state,detail,evidence,success,created
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (task_id, correlation_id, actor, event_type, from_state, to_state,
             _dump(detail), _dump(evidence), None if success is None else int(success), now),
        )
        event_id = int(cur.lastrowid)
    _append_jsonl({
        "event_id": event_id,
        "project": "london-project",
        "task_id": task_id,
        "correlation_id": correlation_id,
        "actor": actor,
        "event_type": event_type,
        "from_state": from_state,
        "to_state": to_state,
        "detail": detail,
        "evidence": evidence,
        "success": success,
        "created": now,
    })
    return event_id


def create_task(title: str, *, platform: str = "", target: str = "", requested_by: str = "chairman",
                assigned_role: str = "", acceptance_criteria: list[str] | None = None,
                payload: dict[str, Any] | None = None, parent_task_id: str = "",
                correlation_id: str = "", task_id: str = "") -> str:
    task_id = task_id or str(uuid.uuid4())
    correlation_id = correlation_id or task_id
    now = time.time()
    with _connect() as db:
        db.execute(
            """INSERT INTO london_tasks(
                task_id,parent_task_id,correlation_id,title,platform,target,requested_by,assigned_role,
                state,acceptance_criteria,payload,created,updated
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (task_id, parent_task_id, correlation_id, title.strip(), platform, target, requested_by,
             assigned_role, "REQUESTED", _dump(acceptance_criteria or []), _dump(payload or {}), now, now),
        )
    _event(task_id=task_id, correlation_id=correlation_id, actor=requested_by,
           event_type="TASK_CREATED", to_state="REQUESTED",
           detail={"title": title, "platform": platform, "target": target, "assigned_role": assigned_role})
    return task_id


def transition(task_id: str, to_state: str, *, actor: str, detail: dict[str, Any] | None = None,
               evidence: list[dict[str, Any]] | None = None, result: dict[str, Any] | None = None,
               error: str = "", verified_by_audit: bool = False) -> None:
    to_state = to_state.upper()
    if to_state not in ALLOWED_STATES:
        raise ValueError(f"Unknown London Project state: {to_state}")
    if to_state == FINAL_VERIFIED_STATE and not verified_by_audit:
        raise PermissionError("VERIFIED_COMPLETE may only be written by deterministic audit")

    now = time.time()
    with _connect() as db:
        row = db.execute("SELECT * FROM london_tasks WHERE task_id=?", (task_id,)).fetchone()
        if not row:
            raise KeyError(task_id)
        old = str(row["state"])
        started = float(row["started"] or 0)
        if not started and to_state in {"RUNNING", "READY_FOR_AUDIT", "AUDITING"}:
            started = now
        terminal = to_state in {"VERIFIED_COMPLETE", "FAILED", "CANCELLED"}
        finished = now if terminal else float(row["finished"] or 0)
        merged_evidence = json.loads(row["evidence"] or "[]") + (evidence or [])
        db.execute(
            """UPDATE london_tasks SET state=?,result=?,evidence=?,error=?,updated=?,started=?,finished=?
               WHERE task_id=?""",
            (to_state, _dump(result or json.loads(row["result"] or "{}")), _dump(merged_evidence),
             error[:4000], now, started, finished, task_id),
        )
        correlation_id = str(row["correlation_id"])
    _event(task_id=task_id, correlation_id=correlation_id, actor=actor,
           event_type="STATE_CHANGED", from_state=old, to_state=to_state,
           detail=detail or {}, evidence=evidence or [],
           success=True if to_state == "VERIFIED_COMPLETE" else False if to_state == "FAILED" else None)


def assign(task_id: str, role: str, *, actor: str = "codex", detail: dict[str, Any] | None = None) -> None:
    now = time.time()
    with _connect() as db:
        row = db.execute("SELECT correlation_id,assigned_role FROM london_tasks WHERE task_id=?", (task_id,)).fetchone()
        if not row:
            raise KeyError(task_id)
        old_role = str(row["assigned_role"] or "")
        db.execute("UPDATE london_tasks SET assigned_role=?,updated=? WHERE task_id=?", (role, now, task_id))
        correlation_id = str(row["correlation_id"])
    _event(task_id=task_id, correlation_id=correlation_id, actor=actor,
           event_type="ASSIGNMENT_CHANGED", detail={"from": old_role, "to": role, **(detail or {})})


def record_attempt(task_id: str, *, actor: str, provider: str = "", action: str = "",
                   success: bool, detail: dict[str, Any] | None = None, error: str = "") -> None:
    now = time.time()
    with _connect() as db:
        row = db.execute("SELECT correlation_id,retry_count FROM london_tasks WHERE task_id=?", (task_id,)).fetchone()
        if not row:
            raise KeyError(task_id)
        retries = int(row["retry_count"] or 0) + (0 if success else 1)
        db.execute("UPDATE london_tasks SET retry_count=?,error=?,updated=? WHERE task_id=?",
                   (retries, error[:4000], now, task_id))
        correlation_id = str(row["correlation_id"])
    _event(task_id=task_id, correlation_id=correlation_id, actor=actor,
           event_type="ATTEMPT", detail={"provider": provider, "action": action, "error": error, **(detail or {})},
           success=success)


def record_evidence(task_id: str, *, actor: str, evidence: dict[str, Any]) -> None:
    with _connect() as db:
        row = db.execute("SELECT correlation_id,evidence FROM london_tasks WHERE task_id=?", (task_id,)).fetchone()
        if not row:
            raise KeyError(task_id)
        items = json.loads(row["evidence"] or "[]")
        items.append(evidence)
        db.execute("UPDATE london_tasks SET evidence=?,updated=? WHERE task_id=?", (_dump(items), time.time(), task_id))
        correlation_id = str(row["correlation_id"])
    _event(task_id=task_id, correlation_id=correlation_id, actor=actor,
           event_type="EVIDENCE_ADDED", evidence=[evidence])


def record_failover(task_id: str, *, from_role: str, to_role: str, reason: str,
                    actor: str = "orchestrator") -> None:
    assign(task_id, to_role, actor=actor, detail={"reason": reason, "failover": True})
    with _connect() as db:
        row = db.execute("SELECT correlation_id FROM london_tasks WHERE task_id=?", (task_id,)).fetchone()
    _event(task_id=task_id, correlation_id=str(row["correlation_id"]), actor=actor,
           event_type="FAILOVER", detail={"from": from_role, "to": to_role, "reason": reason})


def record_human_approval(task_id: str, *, approved: bool, actor: str = "chairman",
                          detail: dict[str, Any] | None = None) -> None:
    with _connect() as db:
        row = db.execute("SELECT correlation_id FROM london_tasks WHERE task_id=?", (task_id,)).fetchone()
        if not row:
            raise KeyError(task_id)
        correlation_id = str(row["correlation_id"])
    _event(task_id=task_id, correlation_id=correlation_id, actor=actor,
           event_type="HUMAN_APPROVAL", detail={"approved": bool(approved), **(detail or {})},
           success=bool(approved))


def record_audit_result(task_id: str, *, passed: bool, evidence: list[dict[str, Any]],
                        actor: str = "deterministic_audit_engine",
                        detail: dict[str, Any] | None = None,
                        verified_state: str = "VERIFIED_COMPLETE") -> None:
    with _connect() as db:
        row = db.execute("SELECT correlation_id FROM london_tasks WHERE task_id=?", (task_id,)).fetchone()
        if not row:
            raise KeyError(task_id)
        correlation_id = str(row["correlation_id"])
    _event(task_id=task_id, correlation_id=correlation_id, actor=actor,
           event_type="AUDIT_RESULT", detail={"passed": bool(passed), **(detail or {})},
           evidence=evidence, success=bool(passed))
    if passed:
        transition(task_id, verified_state, actor=actor, evidence=evidence,
                   detail=detail or {}, verified_by_audit=(verified_state == "VERIFIED_COMPLETE"))
    else:
        transition(task_id, "REWORK_REQUIRED", actor=actor, evidence=evidence,
                   detail=detail or {})


def record_note(task_id: str, *, actor: str, event_type: str, detail: dict[str, Any]) -> None:
    with _connect() as db:
        row = db.execute("SELECT correlation_id FROM london_tasks WHERE task_id=?", (task_id,)).fetchone()
        if not row:
            raise KeyError(task_id)
        correlation_id = str(row["correlation_id"])
    _event(task_id=task_id, correlation_id=correlation_id, actor=actor,
           event_type=event_type, detail=detail)


def get_task(task_id: str) -> dict[str, Any]:
    with _connect() as db:
        task = db.execute("SELECT * FROM london_tasks WHERE task_id=?", (task_id,)).fetchone()
        events = db.execute("SELECT * FROM london_events WHERE task_id=? ORDER BY event_id", (task_id,)).fetchall()
    if not task:
        raise KeyError(task_id)
    return {"task": dict(task), "events": [dict(r) for r in events]}


def recent(limit: int = 100) -> dict[str, Any]:
    limit = max(1, min(int(limit), 1000))
    with _connect() as db:
        tasks = db.execute("SELECT * FROM london_tasks ORDER BY updated DESC LIMIT ?", (limit,)).fetchall()
        events = db.execute("SELECT * FROM london_events ORDER BY event_id DESC LIMIT ?", (limit,)).fetchall()
    return {"tasks": [dict(r) for r in tasks], "events": [dict(r) for r in events]}
