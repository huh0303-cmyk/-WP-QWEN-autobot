from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

from . import london_activity
from .orchestrator import OrchestratorExhausted, generate_text, provider_health

ROOT = Path(__file__).resolve().parents[1]
PRIMARY_PM = "codex"
PLAN_B_PM = "claude"
PLAN_C_PM = "gemini"
SAFE_HOLD = "safe_hold"

CANONICAL_FILES = [
    ROOT / "docs" / "LONDON_PROJECT_BLUEPRINT.md",
    ROOT / "config" / "london_project_blueprint.json",
    ROOT / "docs" / "LONDON_PROJECT_CONTENT_PIPELINES.md",
    ROOT / "config" / "london_content_schedule.json",
    ROOT / "config" / "london_activity_policy.json",
]


def _db_path() -> str:
    return (
        os.environ.get("ORCHESTRATOR_STATE_DB", "").strip()
        or os.environ.get("CONTROL_OPERATIONS_DB", "").strip()
        or str(ROOT / "data" / "control-operations.sqlite3")
    )


def _connect() -> sqlite3.Connection:
    path = Path(_db_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS london_pm_runtime (
            id INTEGER PRIMARY KEY CHECK (id=1),
            active_pm TEXT NOT NULL DEFAULT 'codex',
            lease_owner TEXT NOT NULL DEFAULT '',
            lease_expires REAL NOT NULL DEFAULT 0,
            epoch INTEGER NOT NULL DEFAULT 0,
            last_handoff TEXT NOT NULL DEFAULT '{}',
            updated REAL NOT NULL DEFAULT 0
        );
        INSERT OR IGNORE INTO london_pm_runtime(id,active_pm,updated) VALUES(1,'codex',0);
        """
    )
    return db


def _lease_seconds() -> int:
    try:
        return max(30, int(os.environ.get("PM_LEASE_SECONDS", "180")))
    except ValueError:
        return 180


def _acquire_lease(owner: str) -> bool:
    now = time.time()
    with _connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT lease_owner,lease_expires FROM london_pm_runtime WHERE id=1").fetchone()
        if row["lease_owner"] and row["lease_owner"] != owner and float(row["lease_expires"] or 0) > now:
            db.rollback()
            return False
        db.execute("UPDATE london_pm_runtime SET lease_owner=?,lease_expires=?,updated=? WHERE id=1",
                   (owner, now + _lease_seconds(), now))
        db.commit()
    return True


def heartbeat(owner: str) -> bool:
    with _connect() as db:
        cur = db.execute("UPDATE london_pm_runtime SET lease_expires=?,updated=? WHERE id=1 AND lease_owner=?",
                         (time.time() + _lease_seconds(), time.time(), owner))
        return cur.rowcount == 1


def release_lease(owner: str) -> None:
    with _connect() as db:
        db.execute("UPDATE london_pm_runtime SET lease_owner='',lease_expires=0,updated=? WHERE id=1 AND lease_owner=?",
                   (time.time(), owner))


def _canonical_context() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for path in CANONICAL_FILES:
        key = str(path.relative_to(ROOT))
        try:
            text = path.read_text(encoding="utf-8")
            result[key] = json.loads(text) if path.suffix == ".json" else text[:30000]
        except (OSError, ValueError) as exc:
            result[key] = {"error": str(exc)[:300]}
    return result


def submit_task(title: str, objective: str, *, platform: str = "", target: str = "",
                acceptance_criteria: list[str] | None = None,
                payload: dict[str, Any] | None = None, parent_task_id: str = "") -> str:
    body = dict(payload or {})
    body["objective"] = objective
    body["pm_managed"] = True
    task_id = london_activity.create_task(
        title,
        platform=platform,
        target=target,
        requested_by="chairman",
        assigned_role=PRIMARY_PM,
        acceptance_criteria=acceptance_criteria or [],
        payload=body,
        parent_task_id=parent_task_id,
    )
    london_activity.transition(task_id, "PLANNED", actor=PRIMARY_PM,
                               detail={"objective": objective})
    return task_id


def _is_pm_managed(row: dict[str, Any]) -> bool:
    try:
        payload = json.loads(str(row.get("payload", "{}")) or "{}")
    except ValueError:
        return False
    return payload.get("pm_managed") is True


def _open_tasks(limit: int = 200, *, pm_only: bool = False) -> list[dict[str, Any]]:
    rows = london_activity.recent(limit)["tasks"]
    terminal = {"VERIFIED_COMPLETE", "FAILED", "CANCELLED"}
    result = [row for row in rows if str(row.get("state", "")).upper() not in terminal]
    return [row for row in result if _is_pm_managed(row)] if pm_only else result


def next_work_task_id() -> str:
    priorities = ["REQUESTED", "PLANNED", "ASSIGNED", "REWORK_REQUIRED"]
    rows = _open_tasks(1000, pm_only=True)
    for state in priorities:
        matches = [r for r in rows if str(r.get("state", "")).upper() == state]
        if matches:
            matches.sort(key=lambda r: float(r.get("created", 0)))
            return str(matches[0]["task_id"])
    return ""


def handoff_packet() -> dict[str, Any]:
    with _connect() as db:
        runtime = dict(db.execute("SELECT * FROM london_pm_runtime WHERE id=1").fetchone())
    return {
        "project": "london-project",
        "runtime": runtime,
        "open_tasks": _open_tasks(),
        "provider_health": provider_health(),
        "canonical_context": _canonical_context(),
        "generated_at": time.time(),
    }


def _map_provider(provider: str) -> str:
    return PRIMARY_PM if provider == "openai" else PLAN_B_PM if provider == "anthropic" else PLAN_C_PM if provider == "gemini" else SAFE_HOLD


def _set_active_pm(active: str, packet: dict[str, Any]) -> tuple[str, bool]:
    now = time.time()
    with _connect() as db:
        row = db.execute("SELECT active_pm,epoch FROM london_pm_runtime WHERE id=1").fetchone()
        old = str(row["active_pm"])
        epoch = int(row["epoch"])
        changed = old != active
        db.execute("UPDATE london_pm_runtime SET active_pm=?,epoch=?,last_handoff=?,updated=? WHERE id=1",
                   (active, epoch + int(changed), json.dumps(packet, ensure_ascii=False), now))
    return old, changed


def _prompt(task: dict[str, Any], packet: dict[str, Any]) -> str:
    return f"""You are the active PM for London Project.
Chairman is final business decision maker. CODEX is Plan A primary PM. Claude is Plan B Acting PM. Gemini is Plan C continuity.
Never self-certify VERIFIED_COMPLETE. Never publish review-gated YouTube content publicly without Chairman approval.
Every attempt, failure, retry, handoff and evidence must remain traceable under the existing task_id.
Continue existing policy and cadence; do not redesign strategy during failover.

Canonical context:
{json.dumps(packet['canonical_context'], ensure_ascii=False)[:50000]}

Task:
{json.dumps(task, ensure_ascii=False)[:20000]}

Current handoff state:
{json.dumps({k: v for k, v in packet.items() if k != 'canonical_context'}, ensure_ascii=False)[:30000]}

Return JSON only:
{{"status":"PLANNED|ASSIGNED|RUNNING|READY_FOR_AUDIT|REWORK_REQUIRED|BLOCKED",
"summary":"...","next_actions":[],"assignments":[],"risks":[],"needs_human_approval":false,
"completion_evidence_required":[]}}
"""


def run_task(task_id: str) -> dict[str, Any]:
    owner = f"london-pm-worker:{uuid.uuid4()}"
    if not _acquire_lease(owner):
        raise RuntimeError("London PM lease is held by another worker")
    try:
        snapshot = london_activity.get_task(task_id)
        task = snapshot["task"]
        if not _is_pm_managed(task):
            raise RuntimeError("Task is not PM-managed; publication mirror tasks are not sent to an LLM")
        packet = handoff_packet()
        london_activity.transition(task_id, "RUNNING", actor="orchestrator")
        try:
            raw, meta = generate_text(_prompt(task, packet), task_type="pm", task_id=task_id)
        except OrchestratorExhausted as exc:
            old, changed = _set_active_pm(SAFE_HOLD, packet)
            if changed:
                london_activity.record_failover(task_id, from_role=old, to_role=SAFE_HOLD,
                                                reason="all configured AI providers unavailable")
            london_activity.transition(task_id, "BLOCKED", actor="orchestrator",
                                       error=str(exc), detail={"mode": "SAFE_HOLD"})
            return {"task_id": task_id, "active_pm": SAFE_HOLD, "state": "BLOCKED", "error": str(exc)}

        provider = str(meta.get("provider", ""))
        active = _map_provider(provider)
        old, changed = _set_active_pm(active, packet)
        if changed:
            london_activity.record_failover(task_id, from_role=old, to_role=active,
                                            reason=f"resilient provider selected: {provider}")
        else:
            london_activity.assign(task_id, active, actor="orchestrator",
                                   detail={"provider": provider})

        try:
            decision = json.loads(raw)
        except json.JSONDecodeError:
            decision = {
                "status": "READY_FOR_AUDIT",
                "summary": raw[:4000],
                "next_actions": [],
                "assignments": [],
                "risks": ["PM response was not valid JSON"],
                "needs_human_approval": False,
                "completion_evidence_required": [],
            }
        requested_state = str(decision.get("status", "READY_FOR_AUDIT")).upper()
        if requested_state == "VERIFIED_COMPLETE":
            requested_state = "READY_FOR_AUDIT"
        allowed = {"PLANNED", "ASSIGNED", "RUNNING", "READY_FOR_AUDIT", "REWORK_REQUIRED", "BLOCKED"}
        state = requested_state if requested_state in allowed else "READY_FOR_AUDIT"
        london_activity.transition(task_id, state, actor=active,
                                   result={"decision": decision, "provider_meta": meta})
        return {"task_id": task_id, "active_pm": active, "provider": provider,
                "state": state, "decision": decision, "meta": meta}
    except Exception as exc:
        try:
            london_activity.transition(task_id, "BLOCKED", actor="orchestrator",
                                       error=str(exc), detail={"exception": type(exc).__name__})
        except Exception:
            pass
        raise
    finally:
        release_lease(owner)


def status() -> dict[str, Any]:
    return handoff_packet()
