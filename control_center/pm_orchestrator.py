from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from .orchestrator import generate_text

PRIMARY_PM = "codex"
BACKUP_PM = "claude"
PLAN_C_PM = "gemini"
ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT_DOC = ROOT / "docs" / "PROJECT_A_BLUEPRINT.md"
BLUEPRINT_POLICY = ROOT / "config" / "project_a_blueprint.json"


def _blueprint_context() -> dict[str, Any]:
    policy: dict[str, Any] = {}
    document = ""
    try:
        policy = json.loads(BLUEPRINT_POLICY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        policy = {"error": "Project A machine policy unavailable"}
    try:
        document = BLUEPRINT_DOC.read_text(encoding="utf-8")[:30000]
    except OSError:
        document = "Project A blueprint document unavailable"
    return {"policy": policy, "document": document}


def _db_path() -> str:
    explicit = os.environ.get("ORCHESTRATOR_STATE_DB", "").strip()
    if explicit:
        return explicit
    control_db = os.environ.get("CONTROL_OPERATIONS_DB", "").strip()
    if control_db:
        return control_db
    return str(ROOT / "data" / "control-operations.sqlite3")


def _connect() -> sqlite3.Connection:
    path = _db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS pm_runtime (
            id INTEGER PRIMARY KEY CHECK (id=1),
            active_pm TEXT NOT NULL DEFAULT 'codex',
            lease_owner TEXT NOT NULL DEFAULT '',
            lease_expires REAL NOT NULL DEFAULT 0,
            epoch INTEGER NOT NULL DEFAULT 0,
            last_handoff TEXT NOT NULL DEFAULT '{}',
            updated REAL NOT NULL DEFAULT 0
        );
        INSERT OR IGNORE INTO pm_runtime(id,active_pm,updated) VALUES(1,'codex',0);

        CREATE TABLE IF NOT EXISTS pm_tasks (
            task_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            objective TEXT NOT NULL,
            acceptance_criteria TEXT NOT NULL DEFAULT '[]',
            payload TEXT NOT NULL DEFAULT '{}',
            state TEXT NOT NULL DEFAULT 'pending',
            active_pm TEXT NOT NULL DEFAULT '',
            decision TEXT NOT NULL DEFAULT '{}',
            error TEXT NOT NULL DEFAULT '',
            created REAL NOT NULL,
            updated REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pm_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL DEFAULT '',
            actor TEXT NOT NULL,
            event TEXT NOT NULL,
            detail TEXT NOT NULL DEFAULT '{}',
            created REAL NOT NULL
        );
        """
    )
    return db


def _lease_seconds() -> int:
    try:
        return max(30, int(os.environ.get("PM_LEASE_SECONDS", "180")))
    except ValueError:
        return 180


def _log(actor: str, event: str, detail: dict[str, Any] | None = None, task_id: str = "") -> None:
    with _connect() as db:
        db.execute(
            "INSERT INTO pm_events(task_id,actor,event,detail,created) VALUES(?,?,?,?,?)",
            (task_id, actor, event, json.dumps(detail or {}, ensure_ascii=False), time.time()),
        )


def submit_task(title: str, objective: str, *, acceptance_criteria: list[str] | None = None,
                payload: dict[str, Any] | None = None, task_id: str | None = None) -> str:
    task_id = task_id or str(uuid.uuid4())
    now = time.time()
    with _connect() as db:
        db.execute(
            "INSERT INTO pm_tasks(task_id,title,objective,acceptance_criteria,payload,created,updated) VALUES(?,?,?,?,?,?,?)",
            (task_id, title.strip(), objective.strip(), json.dumps(acceptance_criteria or [], ensure_ascii=False),
             json.dumps(payload or {}, ensure_ascii=False), now, now),
        )
    _log(PRIMARY_PM, "task_submitted", {"title": title}, task_id)
    return task_id


def handoff_packet() -> dict[str, Any]:
    with _connect() as db:
        runtime = db.execute("SELECT * FROM pm_runtime WHERE id=1").fetchone()
        tasks = db.execute(
            "SELECT task_id,title,objective,state,active_pm,decision,error,updated FROM pm_tasks "
            "WHERE state NOT IN ('verified_complete','cancelled') ORDER BY updated DESC LIMIT 30"
        ).fetchall()
        events = db.execute(
            "SELECT task_id,actor,event,detail,created FROM pm_events ORDER BY id DESC LIMIT 50"
        ).fetchall()
    return {
        "project": "Project A",
        "runtime": dict(runtime),
        "open_tasks": [dict(r) for r in tasks],
        "recent_events": [dict(r) for r in events],
        "blueprint": _blueprint_context(),
    }


def next_pending_task_id() -> str:
    with _connect() as db:
        row = db.execute("SELECT task_id FROM pm_tasks WHERE state='pending' ORDER BY created LIMIT 1").fetchone()
    return str(row[0]) if row else ""


def _acquire_lease(owner: str) -> bool:
    now = time.time()
    with _connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT lease_owner,lease_expires FROM pm_runtime WHERE id=1").fetchone()
        if row["lease_owner"] and row["lease_owner"] != owner and float(row["lease_expires"] or 0) > now:
            db.rollback()
            return False
        db.execute("UPDATE pm_runtime SET lease_owner=?,lease_expires=?,updated=? WHERE id=1",
                   (owner, now + _lease_seconds(), now))
        db.commit()
    return True


def heartbeat(owner: str) -> bool:
    now = time.time()
    with _connect() as db:
        cur = db.execute("UPDATE pm_runtime SET lease_expires=?,updated=? WHERE id=1 AND lease_owner=?",
                         (now + _lease_seconds(), now, owner))
        return cur.rowcount == 1


def release_lease(owner: str) -> None:
    with _connect() as db:
        db.execute("UPDATE pm_runtime SET lease_owner='',lease_expires=0,updated=? WHERE id=1 AND lease_owner=?",
                   (time.time(), owner))


def _set_active_pm(provider: str, reason: str, packet: dict[str, Any]) -> str:
    active = PRIMARY_PM if provider == "openai" else BACKUP_PM if provider == "anthropic" else PLAN_C_PM if provider == "gemini" else provider
    with _connect() as db:
        row = db.execute("SELECT active_pm,epoch FROM pm_runtime WHERE id=1").fetchone()
        old, epoch = str(row["active_pm"]), int(row["epoch"])
        db.execute("UPDATE pm_runtime SET active_pm=?,epoch=?,last_handoff=?,updated=? WHERE id=1",
                   (active, epoch + int(old != active), json.dumps(packet, ensure_ascii=False), time.time()))
    if old != active:
        event = "pm_restored" if active == PRIMARY_PM else "pm_failover"
        _log(active, event, {"from": old, "to": active, "reason": reason})
    return active


def _prompt(task: sqlite3.Row, packet: dict[str, Any]) -> str:
    blueprint = packet.get("blueprint", {})
    return f"""You are the active Project Manager for Project A, the Korea365 automation system.
The chairman/user is final decision maker. CODEX/OpenAI is primary PM. If CODEX is unavailable, quota-limited,
rate-limited, timed out or cannot continue, Claude automatically becomes Acting PM with continuity responsibility.
If both CODEX and Claude are unavailable, Gemini is Plan C continuity for pre-approved operational work.
The Acting PM must continue the same project state, not restart strategy from scratch.
Never claim completion without external evidence. A PM decision can only request verification; it cannot self-certify publication.
Do not invent credentials, paid approvals, URLs, test results or publication evidence.

Project A canonical blueprint and machine policy:
{json.dumps(blueprint, ensure_ascii=False)[:42000]}

Task title: {task['title']}
Objective: {task['objective']}
Acceptance criteria: {task['acceptance_criteria']}
Payload: {task['payload']}
Handoff state: {json.dumps({k: v for k, v in packet.items() if k != 'blueprint'}, ensure_ascii=False)[:24000]}

Return JSON only:
{{"status":"plan|delegate|review|rework|blocked|ready_for_audit","summary":"...","next_actions":[],
"assignments":[{{"role":"...","objective":"...","acceptance_criteria":[]}}],"risks":[],
"needs_human_approval":false,"completion_evidence_required":[]}}
"""


def run_task(task_id: str) -> dict[str, Any]:
    owner = f"pm-worker:{uuid.uuid4()}"
    if not _acquire_lease(owner):
        raise RuntimeError("PM lease is held by another worker")
    try:
        with _connect() as db:
            task = db.execute("SELECT * FROM pm_tasks WHERE task_id=?", (task_id,)).fetchone()
            if not task:
                raise KeyError(task_id)
            db.execute("UPDATE pm_tasks SET state='running',error='',updated=? WHERE task_id=?", (time.time(), task_id))
        packet = handoff_packet()
        raw, meta = generate_text(_prompt(task, packet), task_type="pm")
        provider = str(meta.get("provider", ""))
        active = _set_active_pm(provider, "provider selected by resilient orchestrator", packet)
        try:
            decision = json.loads(raw)
        except json.JSONDecodeError:
            decision = {"status": "review", "summary": raw[:4000], "next_actions": [], "assignments": [],
                        "risks": ["PM response was not valid JSON"], "needs_human_approval": False,
                        "completion_evidence_required": []}
        state = "ready_for_audit" if decision.get("status") == "ready_for_audit" else str(decision.get("status") or "review")
        with _connect() as db:
            db.execute("UPDATE pm_tasks SET state=?,active_pm=?,decision=?,updated=? WHERE task_id=?",
                       (state, active, json.dumps(decision, ensure_ascii=False), time.time(), task_id))
        _log(active, "pm_decision", {"provider": provider, "state": state, "meta": meta}, task_id)
        return {"task_id": task_id, "active_pm": active, "provider": provider, "decision": decision, "meta": meta}
    except Exception as exc:
        with _connect() as db:
            db.execute("UPDATE pm_tasks SET state='blocked',error=?,updated=? WHERE task_id=?",
                       (str(exc)[:1000], time.time(), task_id))
        _log(BACKUP_PM, "pm_worker_error", {"error": str(exc)[:1000]}, task_id)
        raise
    finally:
        release_lease(owner)


def status() -> dict[str, Any]:
    packet = handoff_packet()
    packet["policy"] = {
        "primary_pm": PRIMARY_PM,
        "plan_b_pm": BACKUP_PM,
        "plan_c_pm": PLAN_C_PM,
        "verified_complete_owner": "deterministic audit engine",
    }
    return packet
